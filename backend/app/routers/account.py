from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..store.supabase import supabase_admin

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/summary")
async def summary(user=Depends(get_current_user)):
    sb = supabase_admin()
    uid = user["user_id"]
    settings_row = sb.table("user_settings").select("mode").eq("user_id", uid).maybe_single().execute().data
    mode = (settings_row or {}).get("mode", "paper")
    open_pos = sb.table("positions").select("id", count="exact").eq("user_id", uid).eq("status", "open").execute()
    trades = sb.table("trades").select("pnl,executed_at,mode").eq("user_id", uid).execute().data or []
    pnl_total = sum(float(t["pnl"] or 0) for t in trades)
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    pnl_today = sum(float(t["pnl"] or 0) for t in trades if (t.get("executed_at") or "").startswith(today))
    if mode == "paper":
        acc = sb.table("paper_accounts").select("*").eq("user_id", uid).maybe_single().execute().data
        balance = float((acc or {}).get("balance") or 10000.0)
        equity = float((acc or {}).get("equity") or balance)
    else:
        balance = 0.0
        equity = 0.0
    return {
        "mode": mode,
        "balance": balance,
        "equity": equity,
        "open_positions": open_pos.count or 0,
        "pnl_today": pnl_today,
        "pnl_total": pnl_total,
    }
