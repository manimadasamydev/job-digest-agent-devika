from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from job_agent.config import load_settings
from job_agent.db import JobStore
from job_agent.dedupe import dedupe_listings
from job_agent.httputil import client
from job_agent.llm.router import score_jobs
from job_agent.mailer import send_digest
from job_agent.models import Listing
from job_agent.profile import location_ok, title_prefilter
from job_agent.sources.boards import collect_board_listings
from job_agent.sources.careers import collect_career_listings
from job_agent.sources.search_fallback import collect_search_listings

log = logging.getLogger("job_agent")
IST = ZoneInfo("Asia/Kolkata")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    port = os.getenv("PORT")
    if port:
        return _serve(int(port))
    try:
        return asyncio.run(_run())
    except Exception:
        log.exception("job digest failed")
        return 1


def _serve(port: int) -> int:
    settings = load_settings()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            log.info("%s - " + fmt, self.address_string(), *args)

        def _ok(self, payload: dict, code: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization") or ""
            token = ""
            if header.lower().startswith("bearer "):
                token = header.split(" ", 1)[1].strip()
            if not token:
                query = parse_qs(urlparse(self.path).query)
                token = (query.get("token") or [""])[0]
            return bool(settings.job_agent_token) and token == settings.job_agent_token

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/health"):
                self._ok({"ok": True, "service": "job-digest-agent"})
                return
            if path == "/run":
                if not self._authorized():
                    self._ok({"ok": False, "error": "unauthorized"}, 401)
                    return
                code = asyncio.run(_run())
                self._ok({"ok": code == 0, "exit": code}, 200 if code == 0 else 500)
                return
            self._ok({"ok": False, "error": "not found"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            self.do_GET()

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    log.info("listening on %s (GET /health, POST /run)", port)
    server.serve_forever()
    return 0


async def _run() -> int:
    settings = load_settings()
    store = JobStore(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.job_agent_token,
    )
    run_id = store.start_run()
    scraped = 0
    new_count = 0
    emailed = 0
    try:
        async with client(settings.http_timeout) as http:
            boards, blocked = await collect_board_listings(http)
            careers = await collect_career_listings(http, settings.company_concurrency)
            search = await collect_search_listings(http, settings, blocked)
            merged = dedupe_listings(_filter(boards + careers + search))
            scraped = len(merged)
            log.info(
                "collected boards=%s careers=%s search=%s unique=%s blocked=%s",
                len(boards),
                len(careers),
                len(search),
                scraped,
                blocked,
            )
            pending, new_count = store.upsert_listings(merged)
            log.info("new fingerprints=%s pending unemailed=%s", new_count, len(pending))
            if not pending:
                store.finish_run(
                    run_id,
                    status="ok",
                    scraped_count=scraped,
                    new_count=0,
                    emailed_count=0,
                )
                log.info("no new jobs; skip mail")
                return 0
            scored = await score_jobs(http, settings, pending)
            keep = [job for job in scored if (job.relevance_score or 0) >= settings.llm_min_score]
            if not keep and pending:
                # LLM failed: still mail the raw new set so openings are not missed
                keep = pending
                for job in keep:
                    if job.relevance_score is None:
                        job.relevance_score = 60
                    if not job.summary:
                        job.summary = "New listing; sent without model score."
            score_map = {
                job.fingerprint: (job.relevance_score, job.summary)
                for job in pending
            }
            for job in keep:
                score_map[job.fingerprint] = (job.relevance_score, job.summary)
            if keep:
                send_digest(settings, keep, new_count=new_count)
                emailed = len(keep)
            store.mark_processed(list(score_map.keys()), score_map)
            store.finish_run(
                run_id,
                status="ok",
                scraped_count=scraped,
                new_count=new_count,
                emailed_count=emailed,
            )
            log.info("done emailed=%s at %s", emailed, datetime.now(IST).isoformat())
            return 0
    except Exception as exc:
        store.finish_run(
            run_id,
            status="error",
            scraped_count=scraped,
            new_count=new_count,
            emailed_count=emailed,
            error=str(exc)[:2000],
        )
        raise


def _filter(listings: list[Listing]) -> list[Listing]:
    out: list[Listing] = []
    for item in listings:
        blob = f"{item.title} {item.company} {item.location} {item.description}"
        if not title_prefilter(item.title, blob):
            continue
        # Remote-only India: require remote/WFH signal in location or description.
        if not location_ok(item.location or "", blob):
            continue
        out.append(item)
    return out


if __name__ == "__main__":
    sys.exit(main())
