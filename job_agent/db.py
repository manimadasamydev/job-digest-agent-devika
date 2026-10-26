from __future__ import annotations

import logging
from typing import Any

from supabase import Client, create_client

from job_agent.models import Listing, listing_from_row

log = logging.getLogger("job_agent.db")


class JobStore:
    def __init__(self, url: str, key: str, token: str):
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
                "(GitHub: Settings -> Secrets and variables -> Actions)"
            )
        if not token:
            raise RuntimeError(
                "JOB_AGENT_TOKEN is required "
                "(GitHub: Settings -> Secrets and variables -> Actions)"
            )
        self.client: Client = create_client(url, key)
        self.token = token

    def start_run(self) -> str:
        data = self._rpc("ja_start_run", {"p_token": self.token})
        return str(data)

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        scraped_count: int,
        new_count: int,
        emailed_count: int,
        error: str | None = None,
    ) -> None:
        self._rpc(
            "ja_finish_run",
            {
                "p_token": self.token,
                "p_id": run_id,
                "p_status": status,
                "p_scraped": scraped_count,
                "p_new": new_count,
                "p_emailed": emailed_count,
                "p_error": error,
            },
        )

    def upsert_listings(self, listings: list[Listing]) -> tuple[list[Listing], int]:
        if not listings:
            return [], 0
        fps = [item.fingerprint for item in listings]
        existing = set(self._rpc("ja_existing", {"p_token": self.token, "p_fps": fps}) or [])
        new_items = [item for item in listings if item.fingerprint not in existing]
        seen_again = [item.fingerprint for item in listings if item.fingerprint in existing]
        if seen_again:
            self._rpc("ja_touch", {"p_token": self.token, "p_fps": seen_again})
        inserted_rows: list[dict[str, Any]] = []
        for chunk in _chunks(new_items, 40):
            payload = [item.to_row() for item in chunk]
            rows = self._rpc("ja_insert_jobs", {"p_token": self.token, "p_rows": payload}) or []
            if isinstance(rows, list):
                inserted_rows.extend(rows)
        inserted = []
        for row in inserted_rows:
            listing = listing_from_row(row)
            listing.is_new = True
            inserted.append(listing)
        pending_rows = self._rpc("ja_unemailed", {"p_token": self.token}) or []
        pending = [listing_from_row(row) for row in pending_rows]
        by_fp = {item.fingerprint: item for item in pending}
        for item in inserted:
            by_fp[item.fingerprint] = item
        return list(by_fp.values()), len(inserted)

    def mark_processed(self, fingerprints: list[str], score_map: dict[str, tuple[float | None, str]]) -> None:
        for fp in fingerprints:
            score, summary = score_map.get(fp, (None, ""))
            self._rpc(
                "ja_mark",
                {
                    "p_token": self.token,
                    "p_fp": fp,
                    "p_score": score,
                    "p_summary": summary,
                },
            )

    def _rpc(self, name: str, params: dict[str, Any]) -> Any:
        result = self.client.rpc(name, params).execute()
        return result.data


def _chunks(items: list[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
