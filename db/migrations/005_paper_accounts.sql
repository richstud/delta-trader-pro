-- 005_paper_accounts.sql
create table if not exists public.paper_accounts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  balance numeric not null default 10000,
  equity numeric not null default 10000,
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_paper_accounts_touch on public.paper_accounts;
create trigger trg_paper_accounts_touch before update on public.paper_accounts for each row execute function public.touch_updated_at();

grant select on public.paper_accounts to authenticated;
grant all on public.paper_accounts to service_role;
alter table public.paper_accounts enable row level security;
create policy "paper_self_select" on public.paper_accounts for select to authenticated using (auth.uid() = user_id);
