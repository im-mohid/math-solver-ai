create extension if not exists "pgcrypto";

create table if not exists jobs (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz default now(),
  status        text default 'pending',    -- pending | processing | done | error
  input_type    text default 'text',       -- text | image | pdf | txt
  question      text,
  file_url      text,                      -- Supabase Storage path (bucket: uploads)
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

alter table jobs enable row level security;
alter table worker_heartbeat enable row level security;

-- Upload er jonno private bucket (public = false)
insert into storage.buckets (id, name, public)
values ('uploads', 'uploads', false)
on conflict (id) do nothing;
