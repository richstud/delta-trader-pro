"""Strategy worker: every minute, reads latest closed 1m candle from Redis for each
configured symbol, runs EMA6/EMA50 crossover, writes signal, then fans out to
each active user (by user_settings.symbols), placing paper or live orders with
SL/TP/trailing per their settings."""
from __future__ import annotations

import asyncio
import json
import signal
import time
from datetime import datetime, timezone
from typing import Any

import structlog

from app.config import settings as cfg
from app.store.supabase import supabase_admin, redis_client
from app.store.redis_keys import candles_key, status_key, SIGNALS_CHANNEL, user_fills_channel
from app.strategy.ema_cross import EMACross
from app.execution.paper import open_paper_position, close_paper_position, ensure_account
from app.execution.live import open_live_position, close_live_position

log = structlog.get_logger("worker.strategy")
TICK_SECONDS = 15


async def load_user_universe() -> list[dict[str, Any]]:
    sb = supabase_admin()
    return sb.table("user_settings").select("*").execute().data or []


async def handle_signal(side: str, symbol: str, price: float, ema6: float, ema50: float) -> str:
    sb = supabase_admin()
    sig = {
        "symbol": symbol, "side": side, "price": price,
        "ema6": ema6, "ema50": ema50,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    row = sb.table("signals").insert(sig).execute().data[0]
    await redis_client().publish(SIGNALS_CHANNEL, json.dumps(row))
    return row["id"]


async def fanout_signal(signal_id: str, symbol: str, side: str, price: float) -> None:
    users = await load_user_universe()
    sb = supabase_admin()
    for u in users:
        uid = u["user_id"]
        if symbol not in (u.get("symbols") or []):
            continue
        qty = float(u.get("default_qty") or 1)
        sl_pct = float(u.get("sl_pct") or 0)
        tp_pct = float(u.get("tp_pct") or 0)
        mode = u.get("mode", "paper")
        sl = price * (1 - sl_pct / 100) if side == "buy" else price * (1 + sl_pct / 100)
        tp = price * (1 + tp_pct / 100) if side == "buy" else price * (1 - tp_pct / 100)
        # If user has an open opposite position, close it first.
        open_pos = sb.table("positions").select("*").eq("user_id", uid).eq("symbol", symbol).eq("status", "open").execute().data or []
        for p in open_pos:
            if p["side"] != side:
                try:
                    if p["mode"] == "live":
                        await close_live_position(uid, p["id"])
                    else:
                        await close_paper_position(uid, p["id"], price)
                except Exception as e:
                    log.warning("fanout.close.failed", uid=uid, err=str(e))
        try:
            if mode == "live":
                pos = await open_live_position(uid, symbol, side, qty, sl, tp, "algo", signal_id)
            else:
                await ensure_account(uid)
                pos = await open_paper_position(uid, symbol, side, qty, price, sl, tp, "algo", signal_id)
            await redis_client().publish(user_fills_channel(uid), json.dumps({"position_id": pos["id"], "symbol": symbol, "side": side, "price": price}))
        except Exception as e:
            log.warning("fanout.open.failed", uid=uid, err=str(e))


async def manage_sl_tp(latest_prices: dict[str, float]) -> None:
    """Walk every open position and close if SL/TP/trailing breached."""
    sb = supabase_admin()
    open_pos = sb.table("positions").select("*").eq("status", "open").execute().data or []
    for p in open_pos:
        price = latest_prices.get(p["symbol"])
        if not price:
            continue
        side = p["side"]
        sl, tp = p.get("sl"), p.get("tp")
        hit = False
        if sl is not None:
            if side == "buy" and price <= float(sl): hit = True
            if side == "sell" and price >= float(sl): hit = True
        if tp is not None and not hit:
            if side == "buy" and price >= float(tp): hit = True
            if side == "sell" and price <= float(tp): hit = True
        if hit:
            try:
                if p["mode"] == "live":
                    await close_live_position(p["user_id"], p["id"])
                else:
                    await close_paper_position(p["user_id"], p["id"], price)
                await redis_client().publish(user_fills_channel(p["user_id"]), json.dumps({"position_id": p["id"], "closed": True, "price": price}))
            except Exception as e:
                log.warning("sltp.close.failed", err=str(e))


async def main() -> None:
    r = redis_client()
    engines: dict[str, EMACross] = {s: EMACross(6, 50) for s in cfg.symbols}
    last_seen_t: dict[str, int] = {s: 0 for s in cfg.symbols}
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    log.info("worker.strategy.start", symbols=cfg.symbols)
    await r.set(status_key("algo"), "1")
    try:
        while not stop.is_set():
            latest_prices: dict[str, float] = {}
            for sym in cfg.symbols:
                key = candles_key(sym)
                items = await r.lrange(key, -2, -1)
                if not items:
                    continue
                last = json.loads(items[-1])
                latest_prices[sym] = float(last["c"])
                # process closed candles only
                if len(items) >= 2:
                    closed = json.loads(items[-2])
                    if closed["t"] > last_seen_t.get(sym, 0):
                        last_seen_t[sym] = closed["t"]
                        side, e6, e50 = engines[sym].feed(sym, float(closed["c"]))
                        if side:
                            sig_id = await handle_signal(side, sym, float(closed["c"]), e6, e50)
                            await fanout_signal(sig_id, sym, side, float(closed["c"]))
            await manage_sl_tp(latest_prices)
            try:
                await asyncio.wait_for(stop.wait(), timeout=TICK_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        await r.set(status_key("algo"), "0")
        log.info("worker.strategy.shutdown")


if __name__ == "__main__":
    asyncio.run(main())
