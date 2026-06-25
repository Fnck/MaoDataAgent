from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DebugEventMsg:
    """Lightweight debug event passed between producer (service) and consumer (SSE stream / DB).

    ``conversation_id`` is set automatically by ``DebugEventBus.emit()`` — callers
    should not supply it when constructing the event.
    """

    category: str  # "llm_call" | "tool_call" | "context" | "system"
    data: dict[str, Any]
    conversation_id: int = field(init=False, default=0)
    seq: str = field(init=False, default="0")
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    message_id: int | None = None
    step_id: int | None = None


async def persist_debug_event(
    session: AsyncSession, event: DebugEventMsg
) -> int:
    """Persist a debug event to the debug_events table. Returns the row ID."""
    from app.db.database import create_debug_event

    return await create_debug_event(
        session,
        conversation_id=event.conversation_id,
        category=event.category,
        data=json.dumps(event.data, ensure_ascii=False, cls=_DateTimeEncoder),
        timestamp=event.timestamp,
        message_id=event.message_id,
        step_id=event.step_id,
        seq=event.seq,
    )


def to_sse_debug_event(event: DebugEventMsg, event_id: int | None = None) -> dict:
    """Convert a DebugEventMsg to the SSE payload dict for the 'debug' event type."""
    payload: dict[str, Any] = {
        "type": "debug",
        "category": event.category,
        "data": event.data,
        "timestamp": event.timestamp,
        "seq": event.seq,
    }
    if event_id is not None:
        payload["event_id"] = event_id
    if event.message_id is not None:
        payload["message_id"] = event.message_id
    if event.step_id is not None:
        payload["step_id"] = event.step_id
    return payload


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that converts datetime objects to ISO 8601 strings."""
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _sse_event(data: dict) -> str:
    """Format a dict as a standard SSE event: 'data: <json>\\n\\n'."""
    return f"data: {json.dumps(data, cls=_DateTimeEncoder)}\n\n"


class DebugEventBus:
    """Per-request debug event bus using asyncio.Queue producer/consumer pattern.

    Producers (service functions) call emit() to persist and enqueue debug events.
    Consumers (SSE generators) call drain() to retrieve queued events as SSE strings.

    Usage::

        bus = DebugEventBus(session, conversation_id)
        # In producer:
        await bus.emit(DebugEventMsg(...))
        # In consumer (SSE generator):
        for sse_str in bus.drain():
            yield sse_str
    """

    def __init__(self, session: AsyncSession, conversation_id: int):
        self.session = session
        self.conversation_id = conversation_id
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._seq_counter: int = 0

    async def init_seq(self) -> None:
        """No-op: each question's events start from seq 1.

        Previous questions' events already have their message_id set, so the
        assignment query (message_id IS NULL) naturally scopes to the current run.
        """
        pass

    async def emit(self, event: DebugEventMsg) -> int:
        """Persist a debug event to DB and enqueue its SSE representation.

        Centralizes the three-step debug event workflow:
        1. Sets conversation_id and auto-incrementing seq (format: run_xxx#N)
        2. Persists to DB via persist_debug_event (flush, not commit)
        3. Formats as SSE string with the real DB event_id
        4. Enqueues for consumer via asyncio.Queue

        Returns the DB event_id.
        """
        self._seq_counter += 1
        event.seq = str(self._seq_counter)
        event.conversation_id = self.conversation_id
        event_id = await persist_debug_event(self.session, event)
        sse_str = _sse_event(to_sse_debug_event(event, event_id=event_id))
        await self._queue.put(sse_str)
        return event_id

    def drain(self) -> list[str]:
        """Non-blocking drain of all queued SSE debug event strings.

        Call this before yielding each service generator event to interleave
        debug events in the correct order relative to other SSE events.
        """
        result: list[str] = []
        while not self._queue.empty():
            result.append(self._queue.get_nowait())
        return result

    async def emit_and_flush(self, event: DebugEventMsg) -> list[str]:
        """Emit a debug event, commit to DB, and drain the SSE queue.

        Convenience wrapper for the common pattern::

            await bus.emit(event)
            await session.commit()
            for s in bus.drain():
                yield s

        Usage::

            for s in await bus.emit_and_flush(event):
                yield s

        Returns the list of drained SSE strings (includes the emitted event
        and any other pending events).
        """
        await self.emit(event)
        await self.session.commit()
        return self.drain()
