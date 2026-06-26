"""Supabase JWT verification.

Supports two modes:
- HS256 (legacy): set SUPABASE_JWT_SECRET in env.
- RS256/ES256 via JWKS: fetched from <SUPABASE_URL>/auth/v1/.well-known/jwks.json.
"""
from __future__ import annotations

import time
from typing import Any
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, status
from .config import settings


_jwks_client: PyJWKClient | None = None
_jwks_cache_until = 0.0


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client, _jwks_cache_until
    now = time.time()
    if _jwks_client is None or now > _jwks_cache_until:
        url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url, cache_keys=True)
        _jwks_cache_until = now + 3600
    return _jwks_client


def verify_token(token: str) -> dict[str, Any]:
    options = {"verify_aud": True}
    audience = settings.SUPABASE_JWT_AUDIENCE
    try:
        if settings.SUPABASE_JWT_SECRET:
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=audience,
                options=options,
            )
        # JWKS path
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            options=options,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e


async def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_token(token)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub")
    return {"user_id": user_id, "claims": claims, "token": token}


async def verify_ws_token(token: str) -> str:
    """Used by /ws/live where the token comes as a query param."""
    claims = verify_token(token)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub")
    return user_id
