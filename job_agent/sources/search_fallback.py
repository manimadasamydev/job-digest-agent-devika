from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from job_agent.config import Settings
from job_agent.httputil import post_json
from job_agent.models import Listing
from job_agent.profile import location_ok, title_prefilter

log = logging.getLogger("job_agent.search")

SITE = {
    "linkedin": "site:linkedin.com/jobs",
    "naukri": "site:naukri.com",
    "foundit": "site:foundit.in",
}


class SearchBudget:
    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0

    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def take(self) -> bool:
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


async def collect_search_listings(
    http: httpx.AsyncClient,
    settings: Settings,
    blocked_boards: list[str],
) -> list[Listing]:
    budget = SearchBudget(settings.search_call_budget)
    listings: list[Listing] = []
    targets = [b for b in blocked_boards if b in SITE]
    for board in targets:
        if budget.remaining() < 1:
            break
        query = (
            f"Java Developer OR Java Backend OR Java Full Stack OR Spring Boot "
            f"Chennai OR Bengaluru OR Bangalore {SITE[board]} jobs posted"
        )
        got = await _search(http, settings, budget, query, source=board)
        listings.extend(got)
        log.info("search %s -> %s (budget used %s/%s)", board, len(got), budget.used, budget.limit)

    if budget.remaining() > 0:
        today = (
            "Java Developer OR Spring Boot jobs posted today Chennai OR Bengaluru OR Bangalore "
            "site:linkedin.com/jobs OR site:naukri.com OR site:foundit.in"
        )
        listings.extend(await _search(http, settings, budget, today, source="posted-today"))
    return listings


async def _search(
    http: httpx.AsyncClient,
    settings: Settings,
    budget: SearchBudget,
    query: str,
    source: str,
) -> list[Listing]:
    if settings.parallel_api_key and budget.take():
        rows = await _parallel(http, settings.parallel_api_key, query)
        if rows:
            return _to_listings(rows, source)
    if settings.tavily_api_key and budget.take():
        rows = await _tavily(http, settings.tavily_api_key, query)
        if rows:
            return _to_listings(rows, source)
    return []


async def _parallel(http: httpx.AsyncClient, key: str, query: str) -> list[dict[str, Any]]:
    data = await post_json(
        http,
        "https://api.parallel.ai/v1/search",
        {
            "objective": (
                "Find currently open Java Developer, Java Backend, Java Full Stack, or Spring Boot jobs "
                "in Chennai or Bengaluru/Bangalore. Return job posting URLs with title and company."
            ),
            "search_queries": [query],
            "mode": "fast",
        },
        headers={"x-api-key": key, "Content-Type": "application/json"},
    )
    if not isinstance(data, dict):
        return []
    results = data.get("results") or data.get("search_results") or []
    out: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        excerpts = row.get("excerpts") or []
        snippet = " ".join(excerpts) if isinstance(excerpts, list) else str(excerpts or "")
        out.append(
            {
                "url": row.get("url") or "",
                "title": row.get("title") or "",
                "snippet": snippet,
            }
        )
    return out


async def _tavily(http: httpx.AsyncClient, key: str, query: str) -> list[dict[str, Any]]:
    data = await post_json(
        http,
        "https://api.tavily.com/search",
        {
            "api_key": key,
            "query": query,
            "max_results": 8,
            "search_depth": "basic",
            "include_answer": False,
        },
    )
    if not isinstance(data, dict):
        return []
    out: list[dict[str, Any]] = []
    for row in data.get("results") or []:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "url": row.get("url") or "",
                "title": row.get("title") or "",
                "snippet": row.get("content") or "",
            }
        )
    return out


def _to_listings(rows: list[dict[str, Any]], source: str) -> list[Listing]:
    listings: list[Listing] = []
    for row in rows:
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        snippet = row.get("snippet") or ""
        if not url or not title:
            continue
        blob = f"{title} {snippet}"
        if not location_ok(blob, url) and source != "posted-today":
            # still keep if the site is a job URL in India search context
            if not any(x in url.lower() for x in ("naukri", "linkedin.com/jobs", "foundit")):
                continue
        if not title_prefilter(title, snippet):
            continue
        company = _company_from(title, snippet)
        listings.append(
            Listing(
                source=source,
                title=_clean_title(title),
                company=company,
                location=_location_from(blob),
                url=url,
                description=snippet[:1500],
            )
        )
    return listings


def _clean_title(title: str) -> str:
    return re.split(r"\s+[|\-–]\s+", title)[0][:200]


def _company_from(title: str, snippet: str) -> str:
    parts = re.split(r"\s+[|\-–]\s+", title)
    if len(parts) > 1:
        return parts[1][:80]
    match = re.search(r"at ([A-Z][\w&.\- ]{2,40})", snippet)
    return match.group(1).strip() if match else ""


def _location_from(blob: str) -> str:
    text = blob.lower()
    if "chennai" in text:
        return "Chennai"
    if "bengaluru" in text or "bangalore" in text:
        return "Bengaluru"
    return "Chennai/Bengaluru"
