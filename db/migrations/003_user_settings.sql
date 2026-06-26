-- 003_user_settings.sql
create table if not exists public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  mode text not null default 'paper' check (mode in ('paper','live')),
  default_qty numeric not null default 1,
  sl_pct numeric not null default 1,
  tp_pct numeric not null default 2,
  trailing_pct numeric not null default 0,
  symbols text[] not null default array['BTCUSD']::text[],
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_user_settings_touch on public.user_settings;
create trigger trg_user_settings_touch before update on public.user_settings for each row execute function public.touch_updated_at();

grant select, insert, update on public.user_settings to authenticated;
grant all on public.user_settings to service_role;

alter table public.user_settings enable row level security;
create policy "settings_self_rw" on public.user_settings for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
