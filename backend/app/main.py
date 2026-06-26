from __future__ import annotations

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import account, credentials, settings as settings_router, positions, trades, signals, manual, status, ws


def _setup_logging() -> None:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO), format="%(message)s")
    structlog.configure(processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ])


@asynccontextmanager
async def lifespan(_: FastAPI):
    _setup_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Delta Algo API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(status.router)
    app.include_router(account.router)
    app.include_router(credentials.router)
    app.include_router(settings_router.router)
    app.include_router(positions.router)
    app.include_router(trades.router)
    app.include_router(signals.router)
    app.include_router(manual.router)
    app.include_router(ws.router)
    return app


app = create_app()
