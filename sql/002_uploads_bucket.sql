-- Jodi ager schema.sql already run kora thake, shudhu eta run koro:
insert into storage.buckets (id, name, public)
values ('uploads', 'uploads', false)
on conflict (id) do nothing;
