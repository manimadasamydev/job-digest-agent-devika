from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

from job_agent.config import Settings
from job_agent.models import Listing

log = logging.getLogger("job_agent.mail")
IST = ZoneInfo("Asia/Kolkata")


def send_digest(settings: Settings, jobs: list[Listing], *, new_count: int) -> None:
    if not jobs:
        return
    if not settings.gmail_user or not settings.gmail_password:
        raise RuntimeError("GMAIL_USER and GMAIL_APP_PASSWORD are required to send mail")

    now = datetime.now(IST)
    period = "AM" if now.hour < 12 else "PM"
    subject = f"Job digest — {now:%Y-%m-%d} {period} — {len(jobs)} new roles"
    html = _html(jobs, now, new_count)
    text = _text(jobs, now)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_user
    msg["To"] = settings.mail_to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.gmail_user, settings.gmail_password)
        smtp.sendmail(settings.gmail_user, [settings.mail_to], msg.as_string())
    log.info("sent digest with %s jobs to %s", len(jobs), settings.mail_to)


def _text(jobs: list[Listing], now: datetime) -> str:
    lines = [f"New roles first seen {now:%Y-%m-%d %H:%M IST}", ""]
    for job in jobs:
        score = f"{job.relevance_score:.0f}" if job.relevance_score is not None else "-"
        lines.extend(
            [
                f"{job.title} — {job.company}",
                f"  {job.location} | {job.source} | fit {score}",
                f"  {job.url}",
                f"  {job.summary}",
                "",
            ]
        )
    return "\n".join(lines)


def _html(jobs: list[Listing], now: datetime, new_count: int) -> str:
    rows = []
    for job in jobs:
        score = f"{job.relevance_score:.0f}" if job.relevance_score is not None else "-"
        rows.append(
            "<tr>"
            f"<td>{_esc(job.title)}</td>"
            f"<td>{_esc(job.company)}</td>"
            f"<td>{_esc(job.location)}</td>"
            f"<td>{_esc(job.source)}</td>"
            f"<td>{score}</td>"
            f"<td><a href='{_esc(job.url)}'>open</a></td>"
            f"<td>{_esc(job.summary)}</td>"
            "</tr>"
        )
    body = "\n".join(rows)
    return f"""
    <html><body>
    <p>New today (first seen this run / unemailed): {new_count} kept after scoring.</p>
    <p>{now:%Y-%m-%d %H:%M IST}</p>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr>
        <th>Title</th><th>Company</th><th>Location</th>
        <th>Source</th><th>Fit</th><th>Link</th><th>Why it fits</th>
      </tr>
      {body}
    </table>
    </body></html>
    """


def _esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
