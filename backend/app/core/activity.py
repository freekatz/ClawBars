"""Activity log helper: write to DB and publish to in-memory SSE bus."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.models.activity import ActivityLog


async def log_activity(
    session: AsyncSession,
    event_type: str,
    actor_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ActivityLog:
    """Persist an activity log entry and broadcast it on the SSE bus."""
    entry = ActivityLog(
        event_type=event_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        payload=payload or {},
    )
    session.add(entry)
    await session.flush()  # populate entry.id for SSE event_id

    event_bus.publish(
        event_type=event_type,
        payload={
            "log_id": entry.id,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            **(payload or {}),
        },
    )

    return entry
