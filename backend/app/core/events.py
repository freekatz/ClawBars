"""In-memory SSE event bus with Last-Event-ID replay support."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventItem:
    event_id: int
    event_type: str
    payload: dict[str, Any]


class InMemoryEventBus:
    def __init__(self, maxlen: int = 2048):
        self._buffer: deque[EventItem] = deque(maxlen=maxlen)
        self._next_id = 1
        self._waiters: set[asyncio.Event] = set()

    def publish(self, event_type: str, payload: dict[str, Any]) -> EventItem:
        item = EventItem(event_id=self._next_id, event_type=event_type, payload=payload)
        self._next_id += 1
        self._buffer.append(item)
        # Wake up all SSE consumers
        for ev in list(self._waiters):
            ev.set()
        return item

    def since(self, last_event_id: int | None = None) -> list[EventItem]:
        if last_event_id is None:
            return list(self._buffer)
        return [item for item in self._buffer if item.event_id > last_event_id]

    def subscribe(self) -> asyncio.Event:
        """Return an asyncio.Event that fires whenever new events arrive."""
        ev = asyncio.Event()
        self._waiters.add(ev)
        return ev

    def unsubscribe(self, ev: asyncio.Event) -> None:
        self._waiters.discard(ev)


event_bus = InMemoryEventBus()
