from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, urlunparse

from job_agent.models import Listing


def canonical_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    if netloc.endswith("linkedin.com"):
        netloc = "www.linkedin.com"
    path = re.sub(r"/+", "/", parsed.path).rstrip("/")
    linkedin_id = re.search(r"/jobs/view/(?:[^/]*-)?(\d{8,})", path)
    if linkedin_id:
        path = f"/jobs/view/{linkedin_id.group(1)}"
    naukri_id = re.search(r"-(\d{8,})$", path)
    if "naukri.com" in netloc and naukri_id:
        path = f"/job-listings-{naukri_id.group(1)}"
    return urlunparse((scheme, netloc, path, "", "", ""))


def fingerprint_for(listing: Listing) -> str:
    url = canonical_url(listing.url)
    if url:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()
    key = "|".join(
        [
            (listing.title or "").strip().lower(),
            (listing.company or "").strip().lower(),
            (listing.location or "").strip().lower(),
            (listing.source or "").strip().lower(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def dedupe_listings(listings: list[Listing]) -> list[Listing]:
    seen: set[str] = set()
    out: list[Listing] = []
    for item in listings:
        item.url = canonical_url(item.url) or item.url
        item.fingerprint = fingerprint_for(item)
        if not item.fingerprint or item.fingerprint in seen:
            continue
        if not item.title or not item.url:
            continue
        seen.add(item.fingerprint)
        out.append(item)
    return out
