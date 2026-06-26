"""/ws/live — pushes ticks, signals, and user's own fills."""
from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..auth import verify_ws_token
from ..store.supabase import redis_client
from ..store.redis_keys import TICKS_CHANNEL, SIGNALS_CHANNEL, user_fills_channel

router = APIRouter()


@router.websocket("/ws/live")
async def ws_live(ws: WebSocket, token: str = Query(...)):
    try:
        user_id = await verify_ws_token(token)
    except Exception:
        await ws.close(code=4401)
        return
    await ws.accept()
    r = redis_client()
    pubsub = r.pubsub()
    await pubsub.subscribe(TICKS_CHANNEL, SIGNALS_CHANNEL, user_fills_channel(user_id))
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            await ws.send_text(json.dumps({"channel": msg["channel"], "data": json.loads(msg["data"])}))
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
