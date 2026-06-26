"""Delta Exchange WebSocket subscriber.
- maintains one connection, subscribes to v2 ticker channel for configured symbols
- writes latest price to Redis (delta:price:{symbol})
- builds 1m OHLCV candles in-memory then pushes to Redis list
- publishes ticks to delta:ticks
- auto-reconnect with exponential backoff
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
import structlog
import websockets
from ..config import settings
from ..store.supabase import redis_client
from ..store.redis_keys import price_key, candles_key, TICKS_CHANNEL, status_key

log = structlog.get_logger("delta.ws")

CANDLE_INTERVAL = 60  # seconds


class DeltaWS:
    def __init__(self, symbols: list[str]) -> None:
        self.symbols = symbols
        self._candles: dict[str, dict[str, Any]] = {}  # symbol -> in-progress candle

    async def run_forever(self) -> None:
        backoff = 1
        r = redis_client()
        while True:
            try:
                await r.set(status_key("ws"), "0")
                async with websockets.connect(settings.DELTA_WS_URL, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "payload": {
                            "channels": [{"name": "v2/ticker", "symbols": self.symbols}],
                        },
                    }))
                    await r.set(status_key("ws"), "1")
                    log.info("ws.connected", symbols=self.symbols)
                    backoff = 1
                    async for raw in ws:
                        try:
                            await self._handle(json.loads(raw))
                        except Exception:
                            log.exception("ws.handle.failed")
            except Exception as e:
                log.warning("ws.disconnected", err=str(e))
                await r.set(status_key("ws"), "0")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _handle(self, msg: dict[str, Any]) -> None:
        if msg.get("type") != "v2/ticker":
            return
        sym = msg.get("symbol")
        price = float(msg.get("mark_price") or msg.get("close") or msg.get("price") or 0)
        if not sym or not price:
            return
        ts = int(time.time())
        r = redis_client()
        await r.set(price_key(sym), price)
        await r.publish(TICKS_CHANNEL, json.dumps({"symbol": sym, "price": price, "ts": ts}))
        await self._update_candle(sym, price, ts)

    async def _update_candle(self, symbol: str, price: float, ts: int) -> None:
        bucket = (ts // CANDLE_INTERVAL) * CANDLE_INTERVAL
        c = self._candles.get(symbol)
        if c is None or c["t"] != bucket:
            if c is not None:
                # close out previous candle
                await self._persist_candle(symbol, c)
            c = {"t": bucket, "o": price, "h": price, "l": price, "c": price}
            self._candles[symbol] = c
        else:
            c["h"] = max(c["h"], price)
            c["l"] = min(c["l"], price)
            c["c"] = price

    async def _persist_candle(self, symbol: str, c: dict[str, Any]) -> None:
        r = redis_client()
        key = candles_key(symbol)
        await r.rpush(key, json.dumps(c))
        await r.ltrim(key, -500, -1)  # keep last 500 candles
