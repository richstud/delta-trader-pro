from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import get_current_user
from ..store.supabase import supabase_admin, redis_client
from ..store.redis_keys import price_key
from ..execution.paper import open_paper_position
from ..execution.live import open_live_position

router = APIRouter(prefix="/manual", tags=["manual"])


class OrderIn(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    qty: float
    sl: float | None = None
    tp: float | None = None


@router.post("/order")
async def place(body: OrderIn, user=Depends(get_current_user)):
    uid = user["user_id"]
    sb = supabase_admin()
    s = sb.table("user_settings").select("mode").eq("user_id", uid).maybe_single().execute().data
    mode = (s or {}).get("mode", "paper")
    if mode == "live":
        try:
            pos = await open_live_position(uid, body.symbol, body.side, body.qty, body.sl, body.tp, "manual", None)
        except Exception as e:
            raise HTTPException(400, str(e))
        return pos
    r = redis_client()
    last = await r.get(price_key(body.symbol))
    if not last:
        raise HTTPException(400, f"No live price yet for {body.symbol}")
    return await open_paper_position(uid, body.symbol, body.side, body.qty, float(last), body.sl, body.tp, "manual", None)
