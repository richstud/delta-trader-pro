from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import get_current_user
from ..store.supabase import supabase_admin
from ..crypto import encrypt

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredIn(BaseModel):
    api_key: str
    api_secret: str
    is_active: bool = True


@router.get("")
async def get_cred(user=Depends(get_current_user)):
    sb = supabase_admin()
    row = sb.table("broker_credentials").select("broker,is_active,updated_at").eq("user_id", user["user_id"]).eq("broker", "delta").maybe_single().execute().data
    return {
        "broker": "delta",
        "has_credentials": bool(row),
        "is_active": bool(row and row.get("is_active")),
        "updated_at": (row or {}).get("updated_at"),
    }


@router.put("")
async def put_cred(body: CredIn, user=Depends(get_current_user)):
    if not body.api_key or not body.api_secret:
        raise HTTPException(400, "api_key and api_secret required")
    sb = supabase_admin()
    row = {
        "user_id": user["user_id"],
        "broker": "delta",
        "api_key_enc": encrypt(body.api_key),
        "api_secret_enc": encrypt(body.api_secret),
        "is_active": body.is_active,
    }
    sb.table("broker_credentials").upsert(row, on_conflict="user_id,broker").execute()
    return {"ok": True}


@router.delete("")
async def del_cred(user=Depends(get_current_user)):
    sb = supabase_admin()
    sb.table("broker_credentials").delete().eq("user_id", user["user_id"]).eq("broker", "delta").execute()
    return {"ok": True}
