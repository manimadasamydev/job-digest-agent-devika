-- Applied remotely via Supabase MCP. Kept here for the repo record.
create extension if not exists pgcrypto;

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  fingerprint text not null unique,
  source text not null,
  title text not null,
  company text not null default '',
  location text not null default '',
  url text not null,
  description text not null default '',
  posted_at timestamptz,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  emailed_at timestamptz,
  relevance_score double precision,
  summary text,
  raw jsonb not null default '{}'::jsonb
);

create table if not exists public.job_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  scraped_count integer not null default 0,
  new_count integer not null default 0,
  emailed_count integer not null default 0,
  error text
);

alter table public.jobs enable row level security;
alter table public.job_runs enable row level security;
revoke all on public.jobs from anon, authenticated;
revoke all on public.job_runs from anon, authenticated;
grant all on public.jobs to service_role;
grant all on public.job_runs to service_role;
