from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


@dataclass
class Listing:
    source: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    posted_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    relevance_score: float | None = None
    summary: str = ""
    fingerprint: str = ""
    is_new: bool = False

    def to_row(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "description": (self.description or "")[:8000],
            "posted_at": _iso_or_none(self.posted_at),
            "relevance_score": self.relevance_score,
            "summary": self.summary,
            "raw": self.raw or {},
        }


def listing_from_row(row: dict[str, Any]) -> Listing:
    return Listing(
        source=row.get("source") or "",
        title=row.get("title") or "",
        company=row.get("company") or "",
        location=row.get("location") or "",
        url=row.get("url") or "",
        description=row.get("description") or "",
        posted_at=row.get("posted_at"),
        raw=row.get("raw") or {},
        relevance_score=row.get("relevance_score"),
        summary=row.get("summary") or "",
        fingerprint=row.get("fingerprint") or "",
        is_new=True,
    )


def _iso_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) and value > 10_000:
        from datetime import datetime, timezone

        ms = value if value > 10_000_000_000 else value * 1000
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    text = str(value)
    if re.match(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return None
