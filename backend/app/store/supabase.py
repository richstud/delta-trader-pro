"""Shared Supabase service-role client + Redis pool."""
from __future__ import annotations

import redis.asyncio as aioredis
from supabase import create_client, Client
from ..config import settings

_supabase: Client | None = None
_redis: aioredis.Redis | None = None


def supabase_admin() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase


def redis_client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
