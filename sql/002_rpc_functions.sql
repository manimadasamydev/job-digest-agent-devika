-- Run after 001_init.sql in Supabase SQL Editor.
-- Set token to the same value as GitHub secret JOB_AGENT_TOKEN.

create table if not exists public.job_agent_config (
  id int primary key default 1 check (id = 1),
  token text not null
);

insert into public.job_agent_config (id, token)
values (1, 'devika-job-2026')
on conflict (id) do update set token = excluded.token;

create or replace function public.ja_assert_token(p_token text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_token is null or p_token = '' then
    raise exception 'missing token';
  end if;
  if not exists (
    select 1 from public.job_agent_config c where c.id = 1 and c.token = p_token
  ) then
    raise exception 'invalid token';
  end if;
end;
$$;

create or replace function public.ja_start_run(p_token text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  rid uuid;
begin
  perform public.ja_assert_token(p_token);
  insert into public.job_runs (status) values ('running') returning id into rid;
  return rid;
end;
$$;

create or replace function public.ja_finish_run(
  p_token text,
  p_id uuid,
  p_status text,
  p_scraped int,
  p_new int,
  p_emailed int,
  p_error text default null
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ja_assert_token(p_token);
  update public.job_runs
  set finished_at = now(),
      status = p_status,
      scraped_count = coalesce(p_scraped, 0),
      new_count = coalesce(p_new, 0),
      emailed_count = coalesce(p_emailed, 0),
      error = p_error
  where id = p_id;
end;
$$;

create or replace function public.ja_existing(p_token text, p_fps text[])
returns text[]
language plpgsql
security definer
set search_path = public
as $$
declare
  out_fps text[];
begin
  perform public.ja_assert_token(p_token);
  select coalesce(array_agg(j.fingerprint), '{}') into out_fps
  from public.jobs j
  where j.fingerprint = any(p_fps);
  return out_fps;
end;
$$;

create or replace function public.ja_touch(p_token text, p_fps text[])
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ja_assert_token(p_token);
  update public.jobs
  set last_seen_at = now()
  where fingerprint = any(p_fps);
end;
$$;

create or replace function public.ja_insert_jobs(p_token text, p_rows jsonb)
returns setof public.jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ja_assert_token(p_token);
  return query
  insert into public.jobs (
    fingerprint, source, title, company, location, url,
    description, posted_at, relevance_score, summary, raw
  )
  select
    x.fingerprint,
    x.source,
    x.title,
    coalesce(x.company, ''),
    coalesce(x.location, ''),
    x.url,
    coalesce(x.description, ''),
    nullif(x.posted_at, '')::timestamptz,
    x.relevance_score,
    x.summary,
    coalesce(x.raw, '{}'::jsonb)
  from jsonb_to_recordset(p_rows) as x(
    fingerprint text,
    source text,
    title text,
    company text,
    location text,
    url text,
    description text,
    posted_at text,
    relevance_score double precision,
    summary text,
    raw jsonb
  )
  on conflict (fingerprint) do nothing
  returning *;
end;
$$;

create or replace function public.ja_unemailed(p_token text)
returns setof public.jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ja_assert_token(p_token);
  return query
  select * from public.jobs
  where emailed_at is null
  order by first_seen_at desc;
end;
$$;

create or replace function public.ja_mark(
  p_token text,
  p_fp text,
  p_score double precision,
  p_summary text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.ja_assert_token(p_token);
  update public.jobs
  set emailed_at = now(),
      relevance_score = p_score,
      summary = coalesce(p_summary, '')
  where fingerprint = p_fp;
end;
$$;

grant execute on function public.ja_start_run(text) to service_role;
grant execute on function public.ja_finish_run(text, uuid, text, int, int, int, text) to service_role;
grant execute on function public.ja_existing(text, text[]) to service_role;
grant execute on function public.ja_touch(text, text[]) to service_role;
grant execute on function public.ja_insert_jobs(text, jsonb) to service_role;
grant execute on function public.ja_unemailed(text) to service_role;
grant execute on function public.ja_mark(text, text, double precision, text) to service_role;
