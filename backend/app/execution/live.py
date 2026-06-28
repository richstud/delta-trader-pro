"""Live order placement against Delta Exchange using per-user encrypted API key."""
from __future__ import annotations

from typing import Any
from ..delta.rest import DeltaREST
from ..crypto import decrypt
from ..store.supabase import supabase_admin
from .paper import now_iso


async def get_user_delta_client(user_id: str) -> DeltaREST | None:
    sb = supabase_admin()
    row = sb.table("broker_credentials").select("*").eq("user_id", user_id).eq("broker", "delta").eq("is_active", True).maybe_single().execute()
    if not row.data:
        return None
    return DeltaREST(api_key=decrypt(row.data["api_key_enc"]), api_secret=decrypt(row.data["api_secret_enc"]))


async def open_live_position(user_id: str, symbol: str, side: str, qty: float, sl: float | None, tp: float | None, source: str, signal_id: str | None) -> dict[str, Any]:
    sb = supabase_admin()
    client = await get_user_delta_client(user_id)
    if client is None:
        raise RuntimeError("No active Delta credentials for user")
    try:
        resp = await client.place_order(product_symbol=symbol, side=side, size=qty)
    finally:
        await client.close()
    avg = float(((resp or {}).get("result") or {}).get("average_fill_price") or 0) or 0.0
    pos = {
        "user_id": user_id, "symbol": symbol, "side": side, "qty": qty,
        "entry_price": avg, "sl": sl, "tp": tp, "trailing_stop": None,
        "status": "open", "mode": "live", "opened_at": now_iso(),
    }
    p = sb.table("positions").insert(pos).execute().data[0]
    sb.table("trades").insert({
        "user_id": user_id, "symbol": symbol, "side": side, "qty": qty,
        "price": avg, "fee": 0, "pnl": 0, "mode": "live", "source": source,
        "signal_id": signal_id, "executed_at": now_iso(),
    }).execute()
    return p


async def close_live_position(user_id: str, position_id: str) -> None:
    sb = supabase_admin()
    pos = sb.table("positions").select("*").eq("id", position_id).eq("user_id", user_id).single().execute().data
    if not pos or pos["status"] != "open":
        return
    opp = "sell" if pos["side"] == "buy" else "buy"
    client = await get_user_delta_client(user_id)
    if client is None:
        raise RuntimeError("No active Delta credentials for user")
    try:
        resp = await client.place_order(product_symbol=pos["symbol"], side=opp, size=pos["qty"])
    finally:
        await client.close()
    fill = float(((resp or {}).get("result") or {}).get("average_fill_price") or 0) or 0.0
    direction = 1 if pos["side"] == "buy" else -1
    pnl = (fill - pos["entry_price"]) * direction * pos["qty"] if fill else 0
    sb.table("positions").update({"status": "closed", "closed_at": now_iso()}).eq("id", position_id).execute()
    sb.table("trades").insert({
        "user_id": user_id, "symbol": pos["symbol"], "side": opp,
        "qty": pos["qty"], "price": fill, "fee": 0, "pnl": pnl,
        "mode": "live", "source": "manual", "signal_id": None, "executed_at": now_iso(),
    }).execute()
