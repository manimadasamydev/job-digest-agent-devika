from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from job_agent.httputil import get_text
from job_agent.models import Listing
from job_agent.profile import BOARD_QUERIES, CITIES, location_ok, title_prefilter

log = logging.getLogger("job_agent.boards")

SEARCH_URLS = {
    "linkedin": "https://www.linkedin.com/jobs/search/?keywords={q}&location={city}%2C%20India&f_TPR=r86400",
    "naukri": "https://www.naukri.com/{slug}-jobs-in-{city}",
    "foundit": "https://www.foundit.in/srp/results?query={q}&locations={city}",
    "instahyre": "https://www.instahyre.com/search-jobs/?q={q}&location={city}",
    "wellfound": "https://wellfound.com/role/l/{city_slug}/{role_slug}",
    "cutshort": "https://cutshort.io/profile/jobs?search={q}&location={city}",
    "tophire": "https://tophire.co/search?q={q}&location={city}",
}

BLOCK_PRONE = {"linkedin", "naukri", "foundit"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def collect_board_listings(http: httpx.AsyncClient) -> tuple[list[Listing], list[str]]:
    listings: list[Listing] = []
    failed: list[str] = []
    for board in SEARCH_URLS:
        got = 0
        for city in CITIES:
            for query in BOARD_QUERIES[:3]:
                url = _url(board, query, city)
                if not url:
                    continue
                html = await get_text(http, url)
                if not html:
                    continue
                found = _extract(board, html, url)
                got += len(found)
                listings.extend(found)
        if got == 0 and board in BLOCK_PRONE:
            failed.append(board)
            log.info("board %s returned 0, marked blocked", board)
        else:
            log.info("board %s extracted %s", board, got)
    return listings, failed


def _url(board: str, query: str, city: str) -> str:
    city_slug = "bangalore" if city.lower().startswith("beng") else city.lower()
    tmpl = SEARCH_URLS[board]
    if board == "naukri":
        return tmpl.format(slug=_slug(query), city=city_slug)
    if board == "wellfound":
        return tmpl.format(city_slug=city_slug, role_slug=_slug(query))
    return tmpl.format(q=query.replace(" ", "+"), city=city, city_slug=city_slug)


def _extract(board: str, html: str, page_url: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Listing] = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        if "JobPosting" not in text:
            continue
        out.extend(_from_ldjson(board, text))
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        title = " ".join(a.get_text(" ", strip=True).split())
        if len(title) < 8 or not _jobish(href, title):
            continue
        loc_guess = _nearby_location(a)
        blob = f"{title} {loc_guess}"
        if not location_ok(blob, page_url) and board not in {"linkedin", "naukri", "foundit", "instahyre", "wellfound", "cutshort", "tophire"}:
            continue
        location = loc_guess or ("Remote India" if board in BLOCK_PRONE else "")
        if not title_prefilter(title, location):
            continue
        host = urlparse(href).netloc
        if host in {"", "javascript:"}:
            continue
        out.append(
            Listing(
                source=board,
                title=title[:200],
                company=_guess_company(a, board),
                location=location,
                url=href.split("?")[0] if board != "linkedin" else href,
                description=title,
            )
        )
        if len(out) > 80:
            break
    return out


def _jobish(href: str, title: str) -> bool:
    h = href.lower()
    t = title.lower()
    if any(x in h for x in ("/job", "/jobs", "/opening", "/position", "jid=", "jobid")):
        return True
    if any(x in t for x in ("engineer", "developer", "python", "ai ", "genai", "llm", "ml ")):
        return "http" in h
    return False


def _nearby_location(tag) -> str:
    parent = tag.parent
    for _ in range(4):
        if parent is None:
            break
        text = " ".join(parent.get_text(" ", strip=True).split())[:240]
        if any(c in text.lower() for c in ("chennai", "bengaluru", "bangalore", "india", "remote")):
            return text
        parent = parent.parent
    return ""


def _guess_company(tag, board: str) -> str:
    for attr in ("data-company", "data-company-name"):
        if tag.get(attr):
            return tag.get(attr)
    sib = tag.find_next(class_=re.compile(r"company", re.I))
    if sib:
        return sib.get_text(" ", strip=True)[:80]
    return board


def _from_ldjson(board: str, text: str) -> list[Listing]:
    import json

    out: list[Listing] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return out
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        graph = item.get("@graph")
        if isinstance(graph, list):
            items.extend(graph)
            continue
        types = item.get("@type")
        if types != "JobPosting" and "JobPosting" not in str(types):
            continue
        title = item.get("title") or ""
        company = ""
        org = item.get("hiringOrganization") or {}
        if isinstance(org, dict):
            company = org.get("name") or ""
        loc = item.get("jobLocation") or {}
        loc_text = ""
        if isinstance(loc, dict):
            addr = loc.get("address") or {}
            if isinstance(addr, dict):
                loc_text = " ".join(
                    str(addr.get(k) or "") for k in ("addressLocality", "addressRegion", "addressCountry")
                )
        elif isinstance(loc, list) and loc:
            addr = (loc[0] or {}).get("address") or {}
            if isinstance(addr, dict):
                loc_text = str(addr.get("addressLocality") or "")
        url = item.get("url") or ""
        desc = item.get("description") or ""
        if not title_prefilter(title, f"{desc} {loc_text}"):
            continue
        if loc_text and not location_ok(loc_text, desc):
            continue
        out.append(
            Listing(
                source=board,
                title=str(title)[:200],
                company=str(company)[:120],
                location=str(loc_text)[:160],
                url=str(url),
                description=str(desc)[:2000],
                posted_at=item.get("datePosted"),
            )
        )
    return out
