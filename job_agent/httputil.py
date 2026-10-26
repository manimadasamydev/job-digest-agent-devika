from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

log = logging.getLogger("job_agent.http")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 JobDigest/1.0"
)


def client(timeout: float = 20.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
    )


async def get_text(http: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await http.get(url)
        if resp.status_code >= 400:
            log.info("GET %s -> %s", url, resp.status_code)
            return None
        return resp.text
    except Exception as exc:
        log.info("GET fail %s: %s", url, exc)
        return None


async def get_json(http: httpx.AsyncClient, url: str) -> Any | None:
    try:
        resp = await http.get(url)
        if resp.status_code >= 400:
            log.info("GET json %s -> %s", url, resp.status_code)
            return None
        return resp.json()
    except Exception as exc:
        log.info("GET json fail %s: %s", url, exc)
        return None


async def post_json(
    http: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any | None:
    try:
        resp = await http.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            log.info("POST %s -> %s %s", url, resp.status_code, resp.text[:300])
            return None
        return resp.json()
    except Exception as exc:
        log.info("POST fail %s: %s", url, exc)
        return None


async def bounded_gather(coros, limit: int = 8):
    sem = asyncio.Semaphore(limit)

    async def wrap(coro):
        async with sem:
            try:
                return await coro
            except Exception as exc:
                log.info("task failed: %s", exc)
                return []

    return await asyncio.gather(*(wrap(c) for c in coros))
