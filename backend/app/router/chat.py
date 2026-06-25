from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.models import ChatRequest
from app.service.chat import stream_chat
from app.db.session import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    t_start = datetime.now(timezone.utc)
    msg_preview = body.message[:100] + ("..." if len(body.message) > 100 else "")
    logger.info(
        "[/api/chat/stream] user=%s conv_id=%s workflow_mode=%s msg_len=%d msg=\"%s\"",
        current_user["username"],
        body.conversation_id,
        body.workflow_mode or "(auto)",
        len(body.message),
        msg_preview,
    )

    try:
        response = await stream_chat(body, current_user, session)
        elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        logger.info(
            "[/api/chat/stream] COMPLETE user=%s conv_id=%s elapsed_ms=%d",
            current_user["username"],
            body.conversation_id,
            elapsed_ms,
        )
        return response
    except ValueError as e:
        elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        logger.warning(
            "[/api/chat/stream] VALUE_ERROR user=%s conv_id=%s elapsed_ms=%d error=%s",
            current_user["username"],
            body.conversation_id,
            elapsed_ms,
            e,
        )
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError:
        logger.warning(
            "[/api/chat/stream] PERMISSION_DENIED user=%s conv_id=%s",
            current_user["username"],
            body.conversation_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        logger.error(
            "[/api/chat/stream] UNEXPECTED_ERROR user=%s conv_id=%s elapsed_ms=%d error=%s",
            current_user["username"],
            body.conversation_id,
            elapsed_ms,
            e,
        )
        raise
