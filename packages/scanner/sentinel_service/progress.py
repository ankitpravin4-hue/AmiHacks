"""In-memory fan-out of engine progress events to WebSocket subscribers."""

from __future__ import annotations

import asyncio
from typing import Any


class ProgressHub:
    """Replay-capable event bus keyed by scan_id."""

    def __init__(self) -> None:
        self._events: dict[int, list[dict[str, Any]]] = {}
        self._queues: dict[int, list[asyncio.Queue[dict[str, Any] | None]]] = {}
        self._done: set[int] = set()

    def emit(self, scan_id: int, percent: int, step: str, status: str | None = None) -> None:
        """Record an event and push it to every live subscriber."""
        event: dict[str, Any] = {"percent": percent, "step": step}
        if status is not None:
            event["status"] = status
        self._events.setdefault(scan_id, []).append(event)
        if percent >= 100 or status in {"completed", "failed"}:
            self._done.add(scan_id)
        for queue in list(self._queues.get(scan_id, [])):
            queue.put_nowait(event)
            if scan_id in self._done:
                queue.put_nowait(None)

    def history(self, scan_id: int) -> list[dict[str, Any]]:
        """Events already emitted for a scan (late joiners)."""
        return list(self._events.get(scan_id, []))

    def is_done(self, scan_id: int) -> bool:
        """True after the engine finished or failed."""
        return scan_id in self._done

    def subscribe(self, scan_id: int) -> asyncio.Queue[dict[str, Any] | None]:
        """Queue that receives future events. ``None`` means the stream ended."""
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._queues.setdefault(scan_id, []).append(queue)
        return queue

    def unsubscribe(self, scan_id: int, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        """Drop a finished WebSocket subscriber."""
        listeners = self._queues.get(scan_id, [])
        if queue in listeners:
            listeners.remove(queue)
