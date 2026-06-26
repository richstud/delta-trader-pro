"""Delta Exchange REST client with HMAC signing.
Docs: https://docs.delta.exchange/
"""
from __future__ import annotations

import hashlib
import hmac
import time
import httpx
from typing import Any
from ..config import settings


class DeltaREST:
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = (base_url or settings.DELTA_BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(timeout=15.0)

    def _sign(self, method: str, path: str, query: str, body: str, ts: str) -> str:
        if not self.api_secret:
            raise RuntimeError("api_secret missing")
        msg = f"{method}{ts}{path}{query}{body}"
        return hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

    async def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None, signed: bool = False) -> Any:
        import orjson
        url = self.base_url + path
        body = orjson.dumps(json).decode() if json is not None else ""
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if signed:
            ts = str(int(time.time()))
            sig = self._sign(method, path, query, body, ts)
            headers.update({
                "api-key": self.api_key or "",
                "signature": sig,
                "timestamp": ts,
            })
        for attempt in range(3):
            try:
                r = await self._client.request(method, url + query, content=body if body else None, headers=headers)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError("server", request=r.request, response=r)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPStatusError, httpx.TransportError):
                if attempt == 2:
                    raise
                await _backoff(attempt)

    # --- public ---
    async def get_ticker(self, symbol: str) -> Any:
        return await self._request("GET", f"/v2/tickers/{symbol}")

    # --- private ---
    async def place_order(self, *, product_symbol: str, side: str, size: float, order_type: str = "market_order") -> Any:
        body = {
            "product_symbol": product_symbol,
            "side": side,
            "size": size,
            "order_type": order_type,
        }
        return await self._request("POST", "/v2/orders", json=body, signed=True)

    async def positions(self) -> Any:
        return await self._request("GET", "/v2/positions/margined", signed=True)

    async def wallet_balances(self) -> Any:
        return await self._request("GET", "/v2/wallet/balances", signed=True)

    async def close(self) -> None:
        await self._client.aclose()


async def _backoff(attempt: int) -> None:
    import asyncio
    await asyncio.sleep(min(2 ** attempt, 8))
