"""SSE endpoint: real async streaming with Last-Event-ID replay."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from app.core.events import event_bus

router = APIRouter(prefix="/events", tags=["events"])

HEARTBEAT_INTERVAL = 15  # seconds between keep-alive comments


@router.get("")
async def stream_events(
    request: Request,
    last_event_id: str | None = Header(default=None),
) -> StreamingResponse:
    last_id: int | None = None
    if last_event_id:
        try:
            last_id = int(last_event_id)
        except ValueError:
            pass  # Ignore non-numeric Last-Event-ID

    async def generator():
        nonlocal last_id

        # --- replay missed events first ---
        for item in event_bus.since(last_id):
            yield _format_event(item)
            last_id = item.event_id

        # --- subscribe and stream new events ---
        waiter = event_bus.subscribe()
        try:
            while not await request.is_disconnected():
                try:
                    await asyncio.wait_for(asyncio.shield(waiter.wait()), timeout=HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
                    yield ": heartbeat\n\n"
                    continue

                waiter.clear()
                for item in event_bus.since(last_id):
                    yield _format_event(item)
                    last_id = item.event_id
        finally:
            event_bus.unsubscribe(waiter)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_event(item) -> str:
    data = json.dumps(item.payload, default=str, ensure_ascii=False)
    return f"id: {item.event_id}\nevent: {item.event_type}\ndata: {data}\n\n"
