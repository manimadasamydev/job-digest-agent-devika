from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from job_agent.config import Settings
from job_agent.httputil import post_json
from job_agent.models import Listing
from job_agent.profile import RESUME_SUMMARY

log = logging.getLogger("job_agent.llm")

FREE_MODELS = (
    "z-ai/glm-5.2:free",
    "minimax/minimax-m3:free",
    "minimax/minimax-m2.7:free",
    "thinkingmachines/inkling:free",
)

SYSTEM = (
    "You rank job listings for Devika Madasamy. Return JSON only: "
    '{"jobs":[{"i":0,"score":0,"keep":false,"why":"..."}]} '
    "score 0-100. keep true only if score >= 55. "
    "Prefer Java Backend / Spring Boot / Microservices, Remote India only, 6+ years. "
    "Reject onsite-only, intern/fresher/junior, frontend/full-stack UI, "
    "Python/AI-only, .NET-only, principal/staff 12+ only."
)


async def score_jobs(http: httpx.AsyncClient, settings: Settings, jobs: list[Listing]) -> list[Listing]:
    if not jobs:
        return []
    model_ok = False
    for start in range(0, len(jobs), 12):
        batch = jobs[start : start + 12]
        payload = [
            {
                "i": i,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "url": job.url,
                "description": (job.description or "")[:900],
            }
            for i, job in enumerate(batch)
        ]
        prompt = (
            f"Candidate:\n{RESUME_SUMMARY}\n\nJobs JSON:\n{json.dumps(payload, ensure_ascii=False)}\n"
            "Score each job. JSON only."
        )
        text = await _complete(http, settings, prompt)
        parsed = _parse(text, len(batch))
        if text:
            model_ok = True
        for i, job in enumerate(batch):
            if i in parsed:
                job.relevance_score = float(parsed[i]["score"])
                job.summary = str(parsed[i]["why"])[:400]
            elif not text:
                job.relevance_score = 60.0
                job.summary = "New listing; model unavailable."
            else:
                job.relevance_score = 0.0
                job.summary = "No score returned."
    if not model_ok:
        return jobs
    keep = [job for job in jobs if (job.relevance_score or 0) >= settings.llm_min_score]
    keep.sort(key=lambda j: j.relevance_score or 0, reverse=True)
    return keep


async def _complete(http: httpx.AsyncClient, settings: Settings, prompt: str) -> str | None:
    attempts: list[tuple[str, str, str]] = []
    if settings.ollama_api_key:
        attempts.append(("ollama", "gemma4:31b-cloud", settings.ollama_api_key))
    if settings.openrouter_api_key:
        for model in FREE_MODELS:
            attempts.append(("openrouter", model, settings.openrouter_api_key))
    if settings.openrouter_api_key_pam:
        attempts.append(("openrouter", "z-ai/glm-5.3-flash", settings.openrouter_api_key_pam))
    if settings.openrouter_api_key_pam_test:
        attempts.append(("openrouter", "z-ai/glm-5.3-flash", settings.openrouter_api_key_pam_test))
    if settings.mistral_api_key:
        attempts.append(("mistral", "magistral-medium-latest", settings.mistral_api_key))

    for kind, model, key in attempts:
        text = await _call(http, kind, model, key, prompt)
        if text:
            log.info("llm ok via %s %s", kind, model)
            return text
        log.info("llm miss %s %s", kind, model)
    return None


async def _call(http: httpx.AsyncClient, kind: str, model: str, key: str, prompt: str) -> str | None:
    if kind == "ollama":
        data = await post_json(
            http,
            "https://ollama.com/api/chat",
            {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        if isinstance(data, dict):
            return ((data.get("message") or {}).get("content")) or None
        return None
    if kind == "openrouter":
        data = await post_json(
            http,
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "model": model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/devika120898/job-digest-agent",
                "X-Title": "job-digest-agent-devika",
            },
        )
        return _openai_content(data)
    if kind == "mistral":
        data = await post_json(
            http,
            "https://api.mistral.ai/v1/chat/completions",
            {
                "model": model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        return _openai_content(data)
    return None


def _openai_content(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    return ((choices[0].get("message") or {}).get("content")) or None


def _parse(text: str | None, n: int) -> dict[int, dict[str, Any]]:
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        blob = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    rows = blob.get("jobs") if isinstance(blob, dict) else blob
    out: dict[int, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("i", row.get("index", -1)))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= n:
            continue
        try:
            score = float(row.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        keep = bool(row.get("keep", score >= 55))
        why = str(row.get("why") or row.get("reason") or "")[:400]
        out[idx] = {"score": score, "keep": keep or score >= 55, "why": why}
    return out
