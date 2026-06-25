from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.service.debug import get_debug_events_for_conversation
from app.db.session import get_async_session

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/conversation/{conversation_id}")
async def debug_events(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await get_debug_events_for_conversation(
            session, conversation_id, current_user["id"]
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
