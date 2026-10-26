from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    ollama_api_key: str
    openrouter_api_key: str
    openrouter_api_key_pam: str
    openrouter_api_key_pam_test: str
    mistral_api_key: str
    parallel_api_key: str
    tavily_api_key: str
    gmail_user: str
    gmail_app_password: str
    mail_to: str
    job_agent_token: str
    search_call_budget: int = 10
    llm_min_score: int = 55
    http_timeout: float = 20.0
    company_concurrency: int = 8

    @property
    def gmail_password(self) -> str:
        return self.gmail_app_password.replace(" ", "")


def load_settings() -> Settings:
    return Settings(
        supabase_url=_env("SUPABASE_URL"),
        supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        ollama_api_key=_env("OLLAMA_API_KEY"),
        openrouter_api_key=_env("OPENROUTER_API_KEY"),
        openrouter_api_key_pam=_env("OPENROUTER_API_KEY_PAM"),
        openrouter_api_key_pam_test=_env("OPENROUTER_API_KEY_PAM_TEST"),
        mistral_api_key=_env("MISTRAL_API_KEY"),
        parallel_api_key=_env("PARALLEL_API_KEY"),
        tavily_api_key=_env("TAVILY_API_KEY"),
        gmail_user=_env("GMAIL_USER", "manimadasamy.dev@gmail.com"),
        gmail_app_password=_env("GMAIL_APP_PASSWORD"),
        mail_to=_env("MAIL_TO", "manimadasamy.dev@gmail.com"),
        job_agent_token=_env("JOB_AGENT_TOKEN"),
    )
