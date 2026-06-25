from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_conversation, list_debug_events_by_conversation


def _to_iso(value) -> str | None:
    """Convert a datetime or string to ISO format string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def get_debug_events_for_conversation(
    session: AsyncSession, conversation_id: int, user_id: int
) -> list[dict]:
    """Fetch all debug events for a conversation with ownership check."""
    conv = await get_conversation(session, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise PermissionError("Forbidden")

    rows = await list_debug_events_by_conversation(session, conversation_id)
    result = []
    for row in rows:
        entry = {
            "event_id": row.id,
            "conversation_id": row.conversation_id,
            "message_id": row.message_id,
            "step_id": row.step_id,
            "category": row.category,
            "seq": row.seq,
            "data": json.loads(row.data) if row.data else {},
            "timestamp": _to_iso(row.timestamp),
        }
        result.append(entry)
    return result
