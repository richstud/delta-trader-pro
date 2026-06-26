from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_current_user
from ..store.supabase import supabase_admin, redis_client
from ..store.redis_keys import price_key
from ..execution.paper import close_paper_position
from ..execution.live import close_live_position

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
async def list_positions(user=Depends(get_current_user)):
    sb = supabase_admin()
    rows = sb.table("positions").select("*").eq("user_id", user["user_id"]).eq("status", "open").order("opened_at", desc=True).execute().data or []
    return rows


@router.post("/{position_id}/close")
async def close_position(position_id: str, user=Depends(get_current_user)):
    sb = supabase_admin()
    pos = sb.table("positions").select("*").eq("id", position_id).eq("user_id", user["user_id"]).maybe_single().execute().data
    if not pos:
        raise HTTPException(404, "Position not found")
    if pos["mode"] == "live":
        await close_live_position(user["user_id"], position_id)
    else:
        r = redis_client()
        last = await r.get(price_key(pos["symbol"]))
        price = float(last) if last else float(pos["entry_price"])
        await close_paper_position(user["user_id"], position_id, price)
    return {"ok": True}
