from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.database import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    list_messages_by_conversation,
)
from app.db.session import get_async_session
from app.models import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[ConversationOut]:
    rows = await list_conversations(session, current_user["id"])
    return [ConversationOut.model_validate(r) for r in rows]


@router.post("", response_model=ConversationOut)
async def post_conversation(
    body: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ConversationOut:
    conv_id = await create_conversation(session, current_user["id"], body.title)
    await session.commit()
    row = await get_conversation(session, conv_id)
    return ConversationOut.model_validate(row)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ConversationDetail:
    conv = await get_conversation(session, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = await list_messages_by_conversation(session, conversation_id)
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    conv = await get_conversation(session, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    await delete_conversation(session, conversation_id)
    await session.commit()
    return {"detail": "Deleted"}
