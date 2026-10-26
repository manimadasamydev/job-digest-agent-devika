from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from job_agent.companies import ASHBY_BOARDS, GREENHOUSE_BOARDS, LEVER_BOARDS, unique_companies
from job_agent.httputil import bounded_gather, get_json, get_text
from job_agent.models import Listing
from job_agent.profile import location_ok, title_prefilter

log = logging.getLogger("job_agent.careers")

GH_JOBS = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
LEVER_JOBS = "https://api.lever.co/v0/postings/{token}?mode=json"
ASHBY_JOBS = "https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"


async def collect_career_listings(http: httpx.AsyncClient, concurrency: int = 8) -> list[Listing]:
    companies = unique_companies()
    coros = [_company(http, c["name"], c["url"]) for c in companies]
    chunks = await bounded_gather(coros, limit=concurrency)
    out: list[Listing] = []
    for chunk in chunks:
        if chunk:
            out.extend(chunk)
    log.info("career pages yielded %s listings", len(out))
    return out


async def _company(http: httpx.AsyncClient, name: str, url: str) -> list[Listing]:
    listings: list[Listing] = []
    special = await _special_apis(http, name)
    listings.extend(special)
    token = GREENHOUSE_BOARDS.get(name)
    if token:
        listings.extend(await _greenhouse(http, name, token))
    token = LEVER_BOARDS.get(name)
    if token:
        listings.extend(await _lever(http, name, token))
    token = ASHBY_BOARDS.get(name)
    if token:
        listings.extend(await _ashby(http, name, token))
    html = await get_text(http, url)
    if html:
        listings.extend(await _from_html(http, name, url, html))
    return [item for item in listings if title_prefilter(item.title, f"{item.description} {item.location}")]


async def _special_apis(http: httpx.AsyncClient, name: str) -> list[Listing]:
    if name == "Amazon":
        return await _amazon(http)
    if name == "Google":
        return await _google(http)
    if name == "Microsoft":
        return await _microsoft(http)
    return []


async def _amazon(http: httpx.AsyncClient) -> list[Listing]:
    out: list[Listing] = []
    for city in ("Bengaluru", "Chennai"):
        url = (
            "https://www.amazon.jobs/en/search.json"
            f"?base_query=Java+Developer+OR+Spring+Boot&loc_query={city}&normalized_country_code=IND&result_limit=40"
        )
        data = await get_json(http, url)
        jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
        if not jobs:
            continue
        for job in jobs:
            loc = job.get("normalized_location") or job.get("location") or city
            out.append(
                Listing(
                    source="careers:Amazon",
                    title=job.get("title") or "",
                    company="Amazon",
                    location=str(loc),
                    url="https://www.amazon.jobs" + (job.get("job_path") or job.get("url_next_step") or ""),
                    description=job.get("description_short") or job.get("description") or "",
                    posted_at=job.get("posted_date"),
                    raw={"id": job.get("id_icims") or job.get("id")},
                )
            )
    return out


async def _google(http: httpx.AsyncClient) -> list[Listing]:
    out: list[Listing] = []
    for loc in ("Bangalore, India", "Chennai, India"):
        url = (
            "https://careers.google.com/api/v3/search/"
            f"?q=Java%20Developer%20OR%20Spring%20Boot&location={loc.replace(' ', '%20')}"
        )
        data = await get_json(http, url)
        jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
        if not jobs:
            continue
        for job in jobs:
            locs = job.get("locations") or []
            loc_text = ", ".join(
                (x.get("display") or x.get("city") or "") if isinstance(x, dict) else str(x) for x in locs
            )
            out.append(
                Listing(
                    source="careers:Google",
                    title=job.get("title") or "",
                    company="Google",
                    location=loc_text or loc,
                    url=job.get("apply_url") or job.get("canonical_url") or "",
                    description=job.get("summary") or job.get("description") or "",
                )
            )
    return out


async def _microsoft(http: httpx.AsyncClient) -> list[Listing]:
    url = (
        "https://gcsservices.careers.microsoft.com/search/api/v1/search"
        "?q=Java%20Developer%20Spring%20Boot&lc=en_us&pg=1&pgSz=40&o=Relevance&flt=true&l=India"
    )
    data = await get_json(http, url)
    jobs = ((data or {}).get("operationResult") or {}).get("result") if isinstance(data, dict) else None
    jobs = (jobs or {}).get("jobs") if isinstance(jobs, dict) else jobs
    out: list[Listing] = []
    if not jobs:
        return out
    for job in jobs:
        props = job.get("properties") or job
        loc = props.get("primaryLocation") or props.get("location") or ""
        if isinstance(loc, dict):
            loc = loc.get("displayName") or loc.get("city") or ""
        title = job.get("title") or props.get("title") or ""
        job_id = job.get("jobId") or props.get("jobId") or ""
        href = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}" if job_id else ""
        if loc and not location_ok(str(loc), title):
            continue
        out.append(
            Listing(
                source="careers:Microsoft",
                title=str(title),
                company="Microsoft",
                location=str(loc),
                url=href,
                description=str(props.get("description") or "")[:2000],
            )
        )
    return out


async def _greenhouse(http: httpx.AsyncClient, name: str, token: str) -> list[Listing]:
    data = await get_json(http, GH_JOBS.format(token=token))
    jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
    if not jobs:
        return []
    out: list[Listing] = []
    for job in jobs:
        loc = job.get("location") or {}
        loc_text = loc.get("name") if isinstance(loc, dict) else str(loc or "")
        offices = job.get("offices") or []
        extra = " ".join((o.get("name") or o.get("location") or "") for o in offices if isinstance(o, dict))
        if not location_ok(f"{loc_text} {extra}"):
            continue
        out.append(
            Listing(
                source=f"careers:{name}",
                title=job.get("title") or "",
                company=name,
                location=loc_text or extra,
                url=job.get("absolute_url") or "",
                description=re.sub("<[^>]+>", " ", job.get("content") or "")[:2000],
                posted_at=job.get("updated_at") or job.get("created_at"),
            )
        )
    return out


async def _lever(http: httpx.AsyncClient, name: str, token: str) -> list[Listing]:
    jobs = await get_json(http, LEVER_JOBS.format(token=token))
    if not isinstance(jobs, list):
        return []
    out: list[Listing] = []
    for job in jobs:
        cats = job.get("categories") or {}
        loc = cats.get("location") or job.get("country") or ""
        if not location_ok(str(loc), str(job.get("descriptionPlain") or job.get("text") or "")):
            continue
        out.append(
            Listing(
                source=f"careers:{name}",
                title=job.get("text") or job.get("title") or "",
                company=name,
                location=str(loc),
                url=job.get("hostedUrl") or job.get("applyUrl") or "",
                description=(job.get("descriptionPlain") or "")[:2000],
                posted_at=job.get("createdAt"),
            )
        )
    return out


async def _ashby(http: httpx.AsyncClient, name: str, token: str) -> list[Listing]:
    data = await get_json(http, ASHBY_JOBS.format(token=token))
    jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
    if not jobs:
        return []
    out: list[Listing] = []
    for job in jobs:
        loc = job.get("location") or ""
        if isinstance(loc, dict):
            loc = loc.get("name") or loc.get("location") or ""
        blob = f"{loc} {job.get('descriptionHtml') or job.get('descriptionPlain') or ''}"
        if not location_ok(blob):
            continue
        out.append(
            Listing(
                source=f"careers:{name}",
                title=job.get("title") or "",
                company=name,
                location=str(loc),
                url=job.get("jobUrl") or job.get("applyUrl") or "",
                description=re.sub("<[^>]+>", " ", job.get("descriptionHtml") or "")[:2000],
            )
        )
    return out


async def _from_html(http: httpx.AsyncClient, name: str, page_url: str, html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    host_html = html.lower()
    extra: list[Listing] = []
    gh = re.search(r"boards\.greenhouse\.io/([a-z0-9\-]+)", host_html)
    if gh and name not in GREENHOUSE_BOARDS:
        extra.extend(await _greenhouse(http, name, gh.group(1)))
    lever = re.search(r"jobs\.lever\.co/([a-z0-9\-]+)", host_html)
    if lever and name not in LEVER_BOARDS:
        extra.extend(await _lever(http, name, lever.group(1)))
    ash = re.search(r"jobs\.ashbyhq\.com/([a-z0-9\-]+)", host_html)
    if ash and name not in ASHBY_BOARDS:
        extra.extend(await _ashby(http, name, ash.group(1)))
    wd = re.search(r"https?://[a-z0-9.\-]+\.myworkdayjobs\.com/[a-z0-9\-/_]+", host_html)
    if wd:
        extra.extend(await _workday(http, name, wd.group(0)))

    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        title = " ".join(a.get_text(" ", strip=True).split())
        if len(title) < 10:
            continue
        if not any(x in href.lower() for x in ("/job", "/jobs", "/opening", "/careers/")):
            continue
        if not title_prefilter(title):
            continue
        loc = ""
        parent_text = " ".join((a.parent.get_text(" ", strip=True) if a.parent else "").split())[:240]
        if location_ok(parent_text, title):
            loc = parent_text
        elif not location_ok(title, parent_text):
            continue
        extra.append(
            Listing(
                source=f"careers:{name}",
                title=title[:200],
                company=name,
                location=loc[:160],
                url=href,
                description=parent_text,
            )
        )
    return extra


async def _workday(http: httpx.AsyncClient, name: str, board_url: str) -> list[Listing]:
    cxs = re.match(r"(https://[a-z0-9.\-]+\.myworkdayjobs\.com)/([^/]+)", board_url)
    if not cxs:
        return []
    post_url = f"{cxs.group(1)}/wday/cxs/{cxs.group(2)}/jobs"
    try:
        resp = await http.post(
            post_url,
            json={"appliedFacets": {}, "limit": 40, "offset": 0, "searchText": "Java Developer Spring Boot"},
        )
        if resp.status_code >= 400:
            return []
        payload = resp.json()
    except Exception:
        return []
    postings = payload.get("jobPostings") or []
    out: list[Listing] = []
    for job in postings:
        loc = job.get("locationsText") or job.get("bulletFields") or ""
        if isinstance(loc, list):
            loc = " ".join(str(x) for x in loc)
        title = job.get("title") or ""
        if loc and not location_ok(str(loc), title):
            continue
        if not title_prefilter(title, str(loc)):
            continue
        ext = job.get("externalPath") or ""
        href = urljoin(board_url, ext) if ext else board_url
        out.append(
            Listing(
                source=f"careers:{name}",
                title=title,
                company=name,
                location=str(loc),
                url=href,
            )
        )
    return out
