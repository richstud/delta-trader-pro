"""Paper trading executor: maintains paper_accounts ledger in Supabase."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from ..store.supabase import supabase_admin


async def ensure_account(user_id: str, starting_balance: float = 10000.0) -> dict[str, Any]:
    sb = supabase_admin()
    res = sb.table("paper_accounts").select("*").eq("user_id", user_id).maybe_single().execute()
    if res.data:
        return res.data
    row = {"user_id": user_id, "balance": starting_balance, "equity": starting_balance}
    sb.table("paper_accounts").insert(row).execute()
    return row


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def open_paper_position(user_id: str, symbol: str, side: str, qty: float, price: float, sl: float | None, tp: float | None, source: str, signal_id: str | None) -> dict[str, Any]:
    sb = supabase_admin()
    pos = {
        "user_id": user_id, "symbol": symbol, "side": side, "qty": qty,
        "entry_price": price, "sl": sl, "tp": tp, "trailing_stop": None,
        "status": "open", "mode": "paper", "opened_at": now_iso(),
    }
    p = sb.table("positions").insert(pos).execute().data[0]
    sb.table("trades").insert({
        "user_id": user_id, "symbol": symbol, "side": side, "qty": qty,
        "price": price, "fee": 0, "pnl": 0, "mode": "paper", "source": source,
        "signal_id": signal_id, "executed_at": now_iso(),
    }).execute()
    return p


async def close_paper_position(user_id: str, position_id: str, exit_price: float) -> None:
    sb = supabase_admin()
    pos = sb.table("positions").select("*").eq("id", position_id).eq("user_id", user_id).single().execute().data
    if not pos or pos["status"] != "open":
        return
    direction = 1 if pos["side"] == "buy" else -1
    pnl = (exit_price - pos["entry_price"]) * direction * pos["qty"]
    sb.table("positions").update({"status": "closed", "closed_at": now_iso()}).eq("id", position_id).execute()
    sb.table("trades").insert({
        "user_id": user_id, "symbol": pos["symbol"],
        "side": "sell" if pos["side"] == "buy" else "buy",
        "qty": pos["qty"], "price": exit_price, "fee": 0, "pnl": pnl,
        "mode": "paper", "source": "algo", "signal_id": None, "executed_at": now_iso(),
    }).execute()
    acc = sb.table("paper_accounts").select("*").eq("user_id", user_id).single().execute().data
    new_bal = float(acc["balance"]) + pnl
    sb.table("paper_accounts").update({"balance": new_bal, "equity": new_bal, "updated_at": now_iso()}).eq("user_id", user_id).execute()
