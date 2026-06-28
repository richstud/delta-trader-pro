-- 004_positions_trades_signals.sql
create table if not exists public.signals (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  symbol text not null,
  side text not null check (side in ('buy','sell')),
  ema6 numeric not null,
  ema50 numeric not null,
  price numeric not null
);
create index if not exists signals_ts_idx on public.signals(ts desc);

grant select on public.signals to authenticated;
grant all on public.signals to service_role;
alter table public.signals enable row level security;
create policy "signals_read_all" on public.signals for select to authenticated using (true);

create table if not exists public.positions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  side text not null check (side in ('buy','sell')),
  qty numeric not null,
  entry_price numeric not null,
  sl numeric,
  tp numeric,
  trailing_stop numeric,
  status text not null default 'open' check (status in ('open','closed')),
  mode text not null check (mode in ('paper','live')),
  opened_at timestamptz not null default now(),
  closed_at timestamptz
);
create index if not exists positions_user_status_idx on public.positions(user_id, status);

grant select on public.positions to authenticated;
grant all on public.positions to service_role;
alter table public.positions enable row level security;
create policy "positions_self_select" on public.positions for select to authenticated using (auth.uid() = user_id);

create table if not exists public.trades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null,
  side text not null check (side in ('buy','sell')),
  qty numeric not null,
  price numeric not null,
  fee numeric not null default 0,
  pnl numeric not null default 0,
  mode text not null check (mode in ('paper','live')),
  source text not null check (source in ('algo','manual')),
  signal_id uuid references public.signals(id) on delete set null,
  executed_at timestamptz not null default now()
);
create index if not exists trades_user_time_idx on public.trades(user_id, executed_at desc);

grant select on public.trades to authenticated;
grant all on public.trades to service_role;
alter table public.trades enable row level security;
create policy "trades_self_select" on public.trades for select to authenticated using (auth.uid() = user_id);
