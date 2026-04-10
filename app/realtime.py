from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class _Subscriber:
    queue: asyncio.Queue[str]
    loop: asyncio.AbstractEventLoop


class AttendanceEventBroker:
    def __init__(self) -> None:
        self._subscribers: list[_Subscriber] = []
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        subscriber = _Subscriber(queue=queue, loop=asyncio.get_running_loop())
        async with self._lock:
            self._subscribers.append(subscriber)
        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers = [item for item in self._subscribers if item is not subscriber]

    def publish(self, event: str = "refresh") -> None:
        for subscriber in list(self._subscribers):
            subscriber.loop.call_soon_threadsafe(subscriber.queue.put_nowait, event)


attendance_event_broker = AttendanceEventBroker()
