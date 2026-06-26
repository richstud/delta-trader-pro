from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..store.supabase import supabase_admin

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
async def list_signals(user=Depends(get_current_user), limit: int = 100):
    sb = supabase_admin()
    rows = sb.table("signals").select("*").order("ts", desc=True).limit(limit).execute().data or []
    return rows
