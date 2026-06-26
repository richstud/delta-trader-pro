# Delta Algo Platform

Multi-user algorithmic trading platform for Delta Exchange. Two deployables in one repo:

- **`src/`** — React + TanStack Start dashboard (build with `bun run build`, serve `dist/`)
- **`backend/`** — Python FastAPI + workers (deploy to your VPS at `/opt/delta-algo/backend`)

Storage: **your external Supabase project** (Postgres + Auth). No Lovable Cloud.

---

## 1. Supabase setup (one time)

1. Create a project at https://supabase.com (or reuse one).
2. In SQL Editor, run the files in `supabase/migrations/` **in order**: 001 → 005.
3. Authentication → Providers → enable **Email** (password). Optional: disable email confirmation for testing.
4. From Project Settings → API, copy:
   - `Project URL`              → `SUPABASE_URL` and `VITE_SUPABASE_URL`
   - `anon public` key          → `VITE_SUPABASE_PUBLISHABLE_KEY` (and `SUPABASE_ANON_KEY`)
   - `service_role` key (SECRET)→ `SUPABASE_SERVICE_ROLE_KEY`  (server only, never ship to browser)
   - `JWT Secret` (Settings → API → JWT Settings) → `SUPABASE_JWT_SECRET` *(only if your project uses legacy HS256 JWTs; otherwise leave blank — JWKS will be used automatically)*

---

## 2. VPS deploy (backend)

The backend is **completely isolated** from your existing Groww bot:
- Path: `/opt/delta-algo` (separate dir)
- Port: `8010` (no conflict)
- Systemd units: `delta-api`, `delta-websocket`, `delta-strategy` (separate units)
- Nginx vhost: `algo.yourdomain.com` (separate server block)
- Redis DB index: `3` (separate logical DB on same redis-server)

```bash
# As root or sudo user
sudo mkdir -p /opt/delta-algo && sudo chown $USER /opt/delta-algo
git clone <your-repo-url> /opt/delta-algo
cd /opt/delta-algo/backend

python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill SUPABASE_*, REDIS_URL, ENCRYPTION_KEY (see below), DELTA_*, CORS_ORIGINS.

# Generate a 32-byte AES-GCM key:
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# Paste into ENCRYPTION_KEY=
```

Install Redis if not already present (your Groww bot likely already runs one — this app uses
DB index `3` so it cannot collide with your other app's keys):

```bash
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
```

Install the three systemd services:

```bash
sudo chown -R www-data:www-data /opt/delta-algo
sudo cp backend/deploy/systemd/delta-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now delta-api delta-websocket delta-strategy
sudo systemctl status delta-api delta-websocket delta-strategy
```

Logs:
```bash
journalctl -u delta-api -f
journalctl -u delta-websocket -f
journalctl -u delta-strategy -f
```

Nginx + TLS:

```bash
sudo cp backend/deploy/nginx/delta-algo.conf /etc/nginx/sites-available/delta-algo
sudo ln -s /etc/nginx/sites-available/delta-algo /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d algo.yourdomain.com
```

Health check: `curl https://algo.yourdomain.com/health` → `{"ok": true}`.

---

## 3. Frontend deploy

The dashboard ships as static files. Set env at build time:

```
VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<anon key>
VITE_BACKEND_URL=https://algo.yourdomain.com
```

Then:

```bash
bun install
bun run build
# dist/ now contains the static site; host it on Lovable, Vercel, or another nginx vhost.
```

---

## 4. How it works

- **websocket_worker** keeps a single Delta Exchange WebSocket connection (`v2/ticker`),
  writes live prices to Redis `delta:price:{symbol}` and builds 1m OHLCV candles in
  `delta:candles:1m:{symbol}` (last 500). Publishes ticks to `delta:ticks` channel.
  Auto-reconnects with exponential backoff.

- **strategy_worker** polls every 15s. For each closed 1m candle, runs EMA(6)/EMA(50)
  crossover. On a crossover, writes a row to `public.signals` and fans out to every
  user in `public.user_settings` who has that symbol enabled: opens a position in
  paper or live mode per the user's settings, computes SL/TP from their `sl_pct`/`tp_pct`,
  and writes rows to `positions` + `trades`. Also walks all open positions every tick
  and closes those that breach SL/TP using the latest tick price.

- **api** (FastAPI on `:8010`) serves the dashboard: account summary, positions/trades/
  signals list, settings, encrypted credentials CRUD, manual orders, system status, and
  `/ws/live` (pushes ticks + signals + per-user fills via Redis pub/sub).

- **Auth**: every API request carries the Supabase access token as `Bearer`. The backend
  verifies it (HS256 with the JWT secret, or JWKS for RS256 projects) and uses `sub`
  as the user_id. Workers use the service role key and bypass RLS for cross-user fanout.

- **Credentials**: `broker_credentials.api_key_enc` and `api_secret_enc` are AES-GCM-
  encrypted server-side with `ENCRYPTION_KEY`. They are never readable by the client
  (the table has zero `authenticated` policies). The API only accepts writes and
  decrypts on demand when placing live orders.

---

## 5. Reliability

- WS auto-reconnect (exponential backoff capped at 60s).
- REST retries (3x with backoff) on 5xx / transport errors.
- Structured JSON logs (stdout → journald).
- `/health` for liveness; `/status` for per-component (WS / Redis / Supabase / Algo).
- Graceful shutdown on SIGTERM in both workers.
- Stateless API process — scale horizontally by adding more uvicorn workers behind nginx.

---

## 6. Scaling

- 50+ users: workers fan out to all users on each signal; the cost is per-user inserts
  into Supabase + (for live mode) per-user Delta REST calls. Run multiple API processes
  behind nginx upstream if needed.
- Add symbols: append to `DELTA_SYMBOLS` and restart `delta-websocket` and
  `delta-strategy`. Users opt in per-symbol via their `user_settings.symbols`.
- Add strategies: drop a new module under `backend/app/strategy/` and wire it into
  `workers/strategy_worker.py` alongside `EMACross`.
- Multiple brokers: replicate `backend/app/delta/` as `backend/app/<broker>/` and key
  `broker_credentials.broker` to select. `execution/live.py` already routes by broker
  via the credentials row.

---

## 7. Isolation from your existing Groww app

| Resource              | This app                     | Your existing app   |
| --------------------- | ---------------------------- | ------------------- |
| Filesystem            | `/opt/delta-algo`            | (unchanged)         |
| Python venv           | `/opt/delta-algo/backend/.venv` | (unchanged)      |
| FastAPI port          | `8010`                       | (different port)    |
| Systemd units         | `delta-*`                    | (different names)   |
| Nginx vhost           | `algo.yourdomain.com`        | (different host)    |
| Redis DB              | DB index `3` (`REDIS_URL`)   | DB index `0/1/…`    |
| Redis keys            | `delta:*` prefix             | (different prefix)  |
| Supabase project      | This one (separate)          | (separate)          |

Zero shared state → zero possibility of interference.
