from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..store.supabase import supabase_admin

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
async def list_trades(user=Depends(get_current_user), limit: int = 200):
    sb = supabase_admin()
    rows = sb.table("trades").select("*").eq("user_id", user["user_id"]).order("executed_at", desc=True).limit(limit).execute().data or []
    return rows
