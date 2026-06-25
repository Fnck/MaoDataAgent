from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_async_session
from app.db.workflow_db import (
    get_workflow_execution,
    list_workflow_executions_by_conversation,
    list_workflow_steps_by_execution,
)
from app.models.schemas import WorkflowExecutionOut, WorkflowStepOut

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionOut)
async def get_execution(
    execution_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    execution = await get_workflow_execution(session, execution_id)
    if execution is None:
        return {"error": "Not found"}
    steps = await list_workflow_steps_by_execution(session, execution_id)
    step_outs = [WorkflowStepOut.model_validate(s) for s in steps]
    out = WorkflowExecutionOut.model_validate(execution)
    out.steps = step_outs
    return out


@router.get("/conversations/{conversation_id}/executions", response_model=list[WorkflowExecutionOut])
async def get_conversation_executions(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    executions = await list_workflow_executions_by_conversation(session, conversation_id)
    return [WorkflowExecutionOut.model_validate(e) for e in executions]
