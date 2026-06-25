from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WorkflowExecution, WorkflowStep


# ── Workflow Executions ──────────────────────────────────────

async def create_workflow_execution(
    session: AsyncSession,
    conversation_id: int,
    mode: str,
    workflow_name: str | None = None,
    message_id: int | None = None,
) -> int:
    execution = WorkflowExecution(
        conversation_id=conversation_id,
        message_id=message_id,
        mode=mode,
        workflow_name=workflow_name,
        status="running",
    )
    session.add(execution)
    await session.flush()
    return execution.id


async def update_workflow_execution_status(
    session: AsyncSession,
    execution_id: int,
    status: str,
    finished_at: datetime | None = None,
    final_answer: str | None = None,
) -> None:
    execution = await session.get(WorkflowExecution, execution_id)
    if execution:
        execution.status = status
        if finished_at:
            execution.finished_at = finished_at
        if final_answer is not None:
            execution.final_answer = final_answer
        await session.flush()


async def get_workflow_execution(
    session: AsyncSession,
    execution_id: int,
) -> WorkflowExecution | None:
    return await session.get(WorkflowExecution, execution_id)


async def list_workflow_executions_by_conversation(
    session: AsyncSession,
    conversation_id: int,
) -> list[WorkflowExecution]:
    result = await session.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.conversation_id == conversation_id)
        .order_by(WorkflowExecution.started_at.desc())
    )
    return list(result.scalars().all())


async def list_workflow_executions_by_message(
    session: AsyncSession,
    message_id: int,
) -> list[WorkflowExecution]:
    result = await session.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.message_id == message_id)
        .order_by(WorkflowExecution.started_at)
    )
    return list(result.scalars().all())


# ── Workflow Steps ───────────────────────────────────────────

async def create_workflow_step(
    session: AsyncSession,
    execution_id: int,
    step_index: int,
    step_type: str,
    step_name: str,
    input: str | None = None,
) -> int:
    step = WorkflowStep(
        execution_id=execution_id,
        step_index=step_index,
        step_type=step_type,
        step_name=step_name,
        input=input,
        status="running",
    )
    session.add(step)
    await session.flush()
    return step.id


async def update_workflow_step(
    session: AsyncSession,
    step_id: int,
    status: str,
    output: str | None = None,
    error: str | None = None,
    finished_at: datetime | None = None,
) -> None:
    step = await session.get(WorkflowStep, step_id)
    if step:
        step.status = status
        if output is not None:
            step.output = output
        if error is not None:
            step.error = error
        if finished_at:
            step.finished_at = finished_at
        await session.flush()


async def list_workflow_steps_by_execution(
    session: AsyncSession,
    execution_id: int,
) -> list[WorkflowStep]:
    result = await session.execute(
        select(WorkflowStep)
        .where(WorkflowStep.execution_id == execution_id)
        .order_by(WorkflowStep.step_index)
    )
    return list(result.scalars().all())
