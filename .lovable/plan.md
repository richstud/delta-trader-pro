# Fix: `trailing` reserved-word error in migration 004

## Root cause
`trailing` is a reserved keyword in Postgres. `trailing numeric,` is parsed as the start of a `TRIM(TRAILING ...)` expression, producing `syntax error at or near "trailing"`.

## Fix
Rename the column to `trailing_stop` in three places so we don't have to quote `"trailing"` everywhere in Python code.

### 1. `db/migrations/004_positions_trades_signals.sql`
Change the `positions` table definition:
```sql
trailing numeric,
```
→
```sql
trailing_stop numeric,
```

### 2. `backend/app/execution/paper.py`
In `open_paper_position`, change:
```python
"sl": sl, "tp": tp, "trailing": None,
```
→
```python
"sl": sl, "tp": tp, "trailing_stop": None,
```

### 3. `backend/app/execution/live.py`
In `open_live_position`, same change:
```python
"sl": sl, "tp": tp, "trailing": None,
```
→
```python
"sl": sl, "tp": tp, "trailing_stop": None,
```

(Any future strategy-worker code that updates the trailing value must also use `trailing_stop`.)

## What you do after I apply this
1. In Supabase SQL Editor, **delete the previous failed query text** and paste the updated `004_positions_trades_signals.sql` from the repo.
2. Run it — should succeed.
3. Continue with migration `005_paper_accounts.sql`.
4. On the VPS, `git pull` so `backend/app/execution/*.py` picks up the rename, then `systemctl restart delta-api delta-strategy`.

No other files reference the old name.
