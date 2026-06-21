from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .engine import MarketEngine


engine = MarketEngine()
feed_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global feed_task
    feed_task = asyncio.create_task(engine.run_demo_feed(), name="demo-market-feed")
    yield
    engine.stop()
    if feed_task is not None:
        feed_task.cancel()
        with suppress(asyncio.CancelledError):
            await feed_task


app = FastAPI(
    title="QFT Taiwan Trading Workstation API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "feed_connected": engine.connected,
        "mode": engine.mode.value,
        "live_trading_enabled": False,
    }


@app.get("/api/snapshot")
async def snapshot() -> dict[str, object]:
    return engine.snapshot()


@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    last_revision = -1
    try:
        while True:
            if engine.revision != last_revision:
                await websocket.send_json(engine.snapshot())
                last_revision = engine.revision
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        return
