
# Delta Exchange Multi-User Algo Platform — Build Plan

One Lovable repo with two deployables:
- `src/` — React/TS dashboard (runs in Lovable preview, deployed to Lovable hosting or your VPS via static build)
- `backend/` — Python FastAPI + workers (source only; you deploy to `/opt/delta-algo` on your VPS)

Database = your **external Supabase project**. Lovable Cloud stays disabled. You will paste the Supabase URL + anon key + service-role key as secrets; SQL migrations are provided as files for you to run against your Supabase project (Lovable cannot run migrations against an external project from here).

---

## 1. Repo layout

```text
/
├── src/                              ← React + TanStack Start dashboard
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── index.tsx                 ← redirect to /dashboard or /auth
│   │   ├── auth.tsx                  ← login / signup (Supabase email+password)
│   │   ├── reset-password.tsx
│   │   └── _authenticated/
│   │       ├── route.tsx             ← managed auth gate
│   │       ├── dashboard.tsx         ← account summary, P&L, system status
│   │       ├── trades.tsx            ← live + historical trades, manual exit
│   │       ├── signals.tsx           ← EMA6/50 signal feed
│   │       ├── positions.tsx        ← open positions, manual entry/exit
│   │       ├── settings.tsx          ← qty, SL, TP, trailing-stop, paper/live toggle
│   │       └── credentials.tsx       ← add/edit Delta API key + secret
│   ├── lib/
│   │   ├── api.ts                    ← typed client for FastAPI backend (REST + WS)
│   │   └── supabase.ts
│   └── integrations/supabase/client.ts
│
├── backend/                          ← deploy to VPS at /opt/delta-algo
│   ├── app/
│   │   ├── main.py                   ← FastAPI app, port 8010
│   │   ├── config.py                 ← env loader
│   │   ├── auth.py                   ← Supabase JWT verification (JWKS)
│   │   ├── deps.py                   ← get_current_user, get_redis, get_supabase
│   │   ├── routers/
│   │   │   ├── account.py            ← /account/summary
│   │   │   ├── credentials.py        ← CRUD broker_credentials (encrypted)
│   │   │   ├── settings.py           ← user_settings
│   │   │   ├── positions.py          ← list/close
│   │   │   ├── trades.py             ← history
│   │   │   ├── signals.py            ← live + history
│   │   │   ├── manual.py             ← place order (paper/live)
│   │   │   ├── status.py             ← health + WS/Redis/Supabase status
│   │   │   └── ws.py                 ← /ws/live (prices, signals, fills)
│   │   ├── delta/
│   │   │   ├── rest.py               ← Delta REST client (HMAC signing)
│   │   │   ├── ws_client.py          ← Delta WS subscriber (BTCUSD, ETHUSD, etc.)
│   │   │   └── symbols.py
│   │   ├── strategy/
│   │   │   └── ema_cross.py          ← EMA6/EMA50 crossover, 1m candles
│   │   ├── execution/
│   │   │   ├── paper.py              ← paper_accounts ledger
│   │   │   └── live.py               ← live order placement, SL/TP/trailing
│   │   ├── store/
│   │   │   ├── redis_keys.py         ← delta:* keys (prices, candles, signals)
│   │   │   └── supabase.py           ← service-role client
│   │   └── crypto.py                 ← AES-GCM for api_key/api_secret at rest
│   ├── workers/
│   │   ├── websocket_worker.py       ← maintains Delta WS, writes Redis + Supabase
│   │   └── strategy_worker.py        ← consumes candles, runs EMA, emits signals, executes per-user
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── deploy/
│       ├── systemd/
│       │   ├── delta-api.service     ← uvicorn :8010
│       │   ├── delta-websocket.service
│       │   └── delta-strategy.service
│       └── nginx/delta-algo.conf     ← TLS reverse proxy → :8010, /ws upgrade
│
├── supabase/migrations/              ← you run these against YOUR Supabase
│   ├── 001_profiles.sql
│   ├── 002_broker_credentials.sql
│   ├── 003_user_settings.sql
│   ├── 004_positions_trades_signals.sql
│   ├── 005_paper_accounts.sql
│   └── 006_rls_policies.sql
│
└── README.md                         ← VPS deploy steps, systemd, nginx, .env
```

---

## 2. Data model (Supabase Postgres)

- `profiles` (id = auth.users.id, display_name, created_at)
- `broker_credentials` (user_id, broker='delta', api_key_enc, api_secret_enc, is_active) — values encrypted server-side with `ENCRYPTION_KEY` env (AES-GCM), never returned in plaintext to client
- `user_settings` (user_id, mode='paper'|'live', default_qty, sl_pct, tp_pct, trailing_pct, symbols[])
- `signals` (id, symbol, ts, side, ema6, ema50, price)
- `positions` (id, user_id, symbol, side, qty, entry_price, sl, tp, trailing, status, opened_at, closed_at)
- `trades` (id, user_id, symbol, side, qty, price, fee, pnl, mode, source='algo'|'manual', signal_id, executed_at)
- `paper_accounts` (user_id, balance, equity, updated_at)

RLS: every table scoped to `auth.uid()`. Service-role (backend) bypasses RLS for cross-user workers.

---

## 3. Auth flow

- Frontend: Supabase email/password (+ reset password page).
- Frontend attaches `Authorization: Bearer <supabase access_token>` to every FastAPI call (REST + WS query param).
- FastAPI verifies JWT via Supabase JWKS (`SUPABASE_URL/auth/v1/.well-known/jwks.json`), extracts `sub` = user_id.
- Backend uses service-role key for cross-user worker writes; user-scoped endpoints filter by verified `user_id`.

---

## 4. Algo engine (backend)

- **websocket_worker**: one process, single Delta WS connection, subscribes to configured symbols, builds 1m candles in Redis (`delta:candles:{symbol}`), publishes ticks to Redis pub/sub.
- **strategy_worker**: on each closed 1m candle, computes EMA6 + EMA50, detects crossover, writes `signals` row, then fans out to each active user: reads their `user_settings` + `broker_credentials`, places paper or live order with SL/TP/trailing, writes `positions` + `trades`.
- **api**: serves dashboard reads + manual order endpoints + `/ws/live` (pushes prices, signals, user's fills via Redis pub/sub).
- Reliability: auto-reconnect WS with exponential backoff, retry on Delta REST 5xx, structured logging (JSON to stdout → journald), `/health` + `/health/deep` endpoints, graceful shutdown on SIGTERM.
- Scalability: stateless API (horizontal scale behind nginx), single websocket_worker, strategy_worker shardable by symbol later.

---

## 5. Frontend (dashboard)

Pages: Auth, Dashboard (account summary + system status pills: WS/Redis/Supabase/Algo), Positions (live, manual exit), Trades (history + filters), Signals (live feed), Manual order entry, Settings (qty/SL/TP/trailing, paper⇄live), Credentials (add/edit Delta API key+secret — write-only, never displayed back).

Live updates via WS to `wss://<your-domain>/ws/live?token=<jwt>`.

---

## 6. Secrets to add in Lovable

Backend reads these from `.env` on your VPS — Lovable doesn't run the Python backend. The frontend in Lovable only needs:
- `VITE_SUPABASE_URL` (your external project)
- `VITE_SUPABASE_PUBLISHABLE_KEY` (anon key)
- `VITE_BACKEND_URL` (e.g. `https://algo.yourdomain.com`)

On the VPS `.env` you'll set: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_AUDIENCE`, `REDIS_URL`, `ENCRYPTION_KEY` (32-byte base64), `DELTA_BASE_URL`, `LOG_LEVEL`.

---

## 7. Deployment (your VPS, you run these)

1. `git clone` repo into `/opt/delta-algo`
2. `python -m venv .venv && pip install -r backend/requirements.txt`
3. Fill `backend/.env` from `.env.example`
4. Run SQL migrations in Supabase SQL editor (in order)
5. `cp backend/deploy/systemd/*.service /etc/systemd/system/ && systemctl enable --now delta-api delta-websocket delta-strategy`
6. `cp backend/deploy/nginx/delta-algo.conf /etc/nginx/sites-enabled/ && certbot --nginx -d algo.yourdomain.com`
7. Frontend: `bun run build` → host `dist/` on Lovable or same nginx (separate vhost) — point `VITE_BACKEND_URL` at the FastAPI vhost.

Completely isolated from your existing Groww app: different port (8010), different systemd units, different nginx vhost, different repo path.

---

## What I will build in Lovable now (after you approve)

- Full `src/` frontend (all pages, Supabase auth, typed backend client, WS hookup)
- Full `backend/` Python source tree (FastAPI, workers, Delta clients, EMA strategy, paper+live execution, encryption, systemd + nginx + Dockerfile)
- `supabase/migrations/*.sql` for you to run
- `README.md` with exact VPS deploy commands

What I will NOT do (Lovable cannot):
- Run uvicorn / Redis / workers inside the Lovable preview
- Run migrations against your external Supabase project
- SSH into your VPS

Ready to switch to build mode?
