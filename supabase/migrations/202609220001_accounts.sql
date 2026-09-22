-- Run once in your Supabase SQL editor before enabling the new application.
begin;
create table public.nova_records (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  collection text not null check (collection in ('chat', 'messages', 'notes', 'memories')),
  payload jsonb not null check (jsonb_typeof(payload) = 'object' and octet_length(payload::text) <= 100000),
  created_at timestamptz not null default now()
);
create index nova_records_owner_collection on public.nova_records(user_id, collection, id desc);
alter table public.nova_records enable row level security;
revoke all on public.nova_records from anon, authenticated;
grant select, insert, delete on public.nova_records to authenticated;
grant usage on sequence public.nova_records_id_seq to authenticated;
create policy owner_read on public.nova_records for select to authenticated using ((select auth.uid()) = user_id);
create policy owner_insert on public.nova_records for insert to authenticated with check ((select auth.uid()) = user_id);
create policy owner_delete on public.nova_records for delete to authenticated using ((select auth.uid()) = user_id);

-- Keep storage bounded per account, including writes made directly through the REST API.
create function public.nova_trim_records() returns trigger language plpgsql security invoker set search_path = '' as $$
begin
  perform pg_advisory_xact_lock(hashtextextended(new.user_id::text || new.collection, 0));
  delete from public.nova_records where user_id = new.user_id and collection = new.collection
    and id in (select id from public.nova_records where user_id = new.user_id
      and collection = new.collection order by id desc offset 100);
  return new;
end;
$$;
create trigger nova_records_retention after insert on public.nova_records
for each row execute function public.nova_trim_records();
commit;
