-- 002_broker_credentials.sql
create table if not exists public.broker_credentials (
  user_id uuid not null references auth.users(id) on delete cascade,
  broker text not null default 'delta',
  api_key_enc text not null,
  api_secret_enc text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, broker)
);

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

drop trigger if exists trg_broker_creds_touch on public.broker_credentials;
create trigger trg_broker_creds_touch before update on public.broker_credentials for each row execute function public.touch_updated_at();

-- Backend (service_role) owns this table. Clients NEVER read raw ciphertext directly;
-- the FastAPI API mediates all access. So no `authenticated` grants.
grant all on public.broker_credentials to service_role;

alter table public.broker_credentials enable row level security;
