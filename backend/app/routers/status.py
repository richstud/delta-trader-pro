from fastapi import APIRouter
from ..store.supabase import redis_client, supabase_admin
from ..store.redis_keys import status_key

router = APIRouter(tags=["status"])


@router.get("/health")
async def health():
    return {"ok": True}


@router.get("/status")
async def status():
    out = {"websocket": False, "redis": False, "supabase": False, "algo": False}
    try:
        r = redis_client()
        pong = await r.ping()
        out["redis"] = bool(pong)
        out["websocket"] = (await r.get(status_key("ws"))) == "1"
        out["algo"] = (await r.get(status_key("algo"))) == "1"
    except Exception:
        pass
    try:
        sb = supabase_admin()
        sb.table("user_settings").select("user_id").limit(1).execute()
        out["supabase"] = True
    except Exception:
        pass
    return out
