# Job Digest Agent

Twice-daily digest of **Java Developer / Java Backend / Java Full Stack** roles in **Chennai** and **Bengaluru**, ranked against Manikandan Madasamy's profile.

Runs on a schedule at **8:00 AM and 6:00 PM IST** (`30 2,12 * * *` UTC), stores listings in Supabase, and emails **only new** matches to `manimadasamy.dev@gmail.com`.

## What it searches

- Boards: TopHire, Cutshort, LinkedIn, Naukri, Foundit, Instahyre, Wellfound
- Official company career pages
- Parallel, then Tavily, only when LinkedIn / Naukri / Foundit are blocked (budgeted)

Duplicates are keyed by URL fingerprint. A job is emailed at most once.

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# fill .env — never commit it
python -m job_agent
```

## Free hosting (recommended)

Use **GitHub Actions** (`.github/workflows/digest.yml`) with the same secrets as `.env`. Free Render web cannot send Gmail SMTP reliably.

## LLM order

1. Ollama Cloud `gemma4:31b-cloud`
2. Your OpenRouter key, free models only
3. `z-ai/glm-5.3-flash` on fallback OpenRouter keys
4. Mistral Magistral Medium

If every model fails, the digest still sends a raw new-job list.
