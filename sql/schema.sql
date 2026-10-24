create extension if not exists "pgcrypto";

create table if not exists jobs (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz default now(),
  status        text default 'pending',    -- pending | processing | done | error
  input_type    text default 'text',       -- text | image | pdf | txt
  question      text,
  file_url      text,
  options       jsonb default '{}'::jsonb,
  answer        jsonb,
  error         text,
  worker_id     text,
  started_at    timestamptz,
  finished_at   timestamptz
);

create index if not exists jobs_status_idx on jobs (status, created_at);

create table if not exists worker_heartbeat (
  worker_id  text primary key,
  last_seen  timestamptz default now(),
  info       jsonb default '{}'::jsonb
);

-- Atomic claim: duita worker ek-i job nite parbe na
create or replace function claim_job(p_worker text)
returns setof jobs
language plpgsql
as $$
begin
  return query
  update jobs
     set status = 'processing', worker_id = p_worker, started_at = now()
   where id = (
     select id from jobs
      where status = 'pending'
      order by created_at
      limit 1
      for update skip locked
   )
  returning *;
end;
$$;

-- Server-side only: RLS on, kono policy nai. service_role key RLS bypass kore,
-- tai browser/anon key diye kichu access kora jabe na.
alter table jobs enable row level security;
alter table worker_heartbeat enable row level security;
