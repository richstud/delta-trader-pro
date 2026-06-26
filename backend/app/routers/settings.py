from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..auth import get_current_user
from ..store.supabase import supabase_admin

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULTS = {
    "mode": "paper",
    "default_qty": 1,
    "sl_pct": 1.0,
    "tp_pct": 2.0,
    "trailing_pct": 0.0,
    "symbols": ["BTCUSD"],
}


class SettingsIn(BaseModel):
    mode: str = Field(pattern="^(paper|live)$")
    default_qty: float
    sl_pct: float
    tp_pct: float
    trailing_pct: float
    symbols: list[str]


@router.get("")
async def get_settings(user=Depends(get_current_user)):
    sb = supabase_admin()
    row = sb.table("user_settings").select("*").eq("user_id", user["user_id"]).maybe_single().execute().data
    if not row:
        return DEFAULTS
    return {k: row.get(k, v) for k, v in DEFAULTS.items()}


@router.put("")
async def put_settings(body: SettingsIn, user=Depends(get_current_user)):
    sb = supabase_admin()
    row = {"user_id": user["user_id"], **body.model_dump()}
    sb.table("user_settings").upsert(row, on_conflict="user_id").execute()
    return {"ok": True}
