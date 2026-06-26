"""Standalone WebSocket worker: runs Delta WS subscriber forever."""
from __future__ import annotations

import asyncio
import signal
import structlog
from app.config import settings
from app.delta.ws_client import DeltaWS

log = structlog.get_logger("worker.ws")


async def main() -> None:
    ws = DeltaWS(settings.symbols)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    task = asyncio.create_task(ws.run_forever())
    await stop.wait()
    log.info("worker.ws.shutdown")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
