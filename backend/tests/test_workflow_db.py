from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.workflow_db import (
    create_workflow_execution,
    create_workflow_step,
    update_workflow_execution_status,
    update_workflow_step,
    get_workflow_execution,
    list_workflow_executions_by_conversation,
    list_workflow_executions_by_message,
    list_workflow_steps_by_execution,
)


# ── Workflow Executions ─────────────────────────────────────

class TestWorkflowExecutionCRUD:
    @pytest.mark.asyncio
    async def test_create_execution(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()
        assert exec_id > 0

        record = await get_workflow_execution(db_session, exec_id)
        assert record is not None
        assert record.mode == "dynamic"
        assert record.status == "running"
        assert record.conversation_id == 1
        assert record.started_at is not None

    @pytest.mark.asyncio
    async def test_create_execution_with_optional_fields(self, db_session):
        exec_id = await create_workflow_execution(
            db_session,
            conversation_id=1,
            mode="yaml",
            workflow_name="explore_table",
            message_id=42,
        )
        await db_session.commit()

        record = await get_workflow_execution(db_session, exec_id)
        assert record.mode == "yaml"
        assert record.workflow_name == "explore_table"
        assert record.message_id == 42

    @pytest.mark.asyncio
    async def test_update_execution_status_completed(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )

        finished = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        await update_workflow_execution_status(
            db_session, exec_id, "completed",
            finished_at=finished,
            final_answer="All done.",
        )
        await db_session.commit()

        record = await get_workflow_execution(db_session, exec_id)
        assert record.status == "completed"
        assert record.finished_at is not None
        assert record.final_answer == "All done."

    @pytest.mark.asyncio
    async def test_update_execution_status_failed(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )

        finished = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        await update_workflow_execution_status(
            db_session, exec_id, "failed", finished_at=finished
        )
        await db_session.commit()

        record = await get_workflow_execution(db_session, exec_id)
        assert record.status == "failed"

    @pytest.mark.asyncio
    async def test_get_nonexistent_execution(self, db_session):
        record = await get_workflow_execution(db_session, 99999)
        assert record is None

    @pytest.mark.asyncio
    async def test_list_by_conversation(self, db_session):
        await create_workflow_execution(db_session, conversation_id=1, mode="dynamic")
        await create_workflow_execution(db_session, conversation_id=1, mode="yaml")
        await create_workflow_execution(db_session, conversation_id=2, mode="dynamic")
        await db_session.commit()

        results = await list_workflow_executions_by_conversation(db_session, 1)
        assert len(results) == 2

        results2 = await list_workflow_executions_by_conversation(db_session, 2)
        assert len(results2) == 1

        empty = await list_workflow_executions_by_conversation(db_session, 999)
        assert empty == []

    @pytest.mark.asyncio
    async def test_list_by_message(self, db_session):
        await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic", message_id=10
        )
        await create_workflow_execution(
            db_session, conversation_id=1, mode="yaml", message_id=10
        )
        await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic", message_id=20
        )
        await db_session.commit()

        results = await list_workflow_executions_by_message(db_session, 10)
        assert len(results) == 2

        empty = await list_workflow_executions_by_message(db_session, 999)
        assert empty == []


# ── Workflow Steps ──────────────────────────────────────────

class TestWorkflowStepCRUD:
    @pytest.mark.asyncio
    async def test_create_step(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()

        step_id = await create_workflow_step(
            db_session,
            exec_id,
            step_index=0,
            step_type="tool_call",
            step_name="list_tables",
            input='{"key": "value"}',
        )
        await db_session.commit()

        assert step_id > 0

    @pytest.mark.asyncio
    async def test_update_step_completed(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()

        step_id = await create_workflow_step(
            db_session, exec_id, 0, "tool_call", "list_tables"
        )
        await db_session.commit()

        finished = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        await update_workflow_step(
            db_session, step_id, "completed",
            output='{"tables": ["a", "b"]}',
            finished_at=finished,
        )
        await db_session.commit()

        steps = await list_workflow_steps_by_execution(db_session, exec_id)
        assert len(steps) == 1
        step = steps[0]
        assert step.status == "completed"
        assert step.output == '{"tables": ["a", "b"]}'
        assert step.finished_at is not None

    @pytest.mark.asyncio
    async def test_update_step_failed(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()

        step_id = await create_workflow_step(
            db_session, exec_id, 0, "tool_call", "bad_tool"
        )
        await db_session.commit()

        await update_workflow_step(
            db_session, step_id, "failed",
            error="Tool not found",
        )
        await db_session.commit()

        steps = await list_workflow_steps_by_execution(db_session, exec_id)
        assert steps[0].status == "failed"
        assert steps[0].error == "Tool not found"

    @pytest.mark.asyncio
    async def test_list_steps_ordered_by_index(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()

        for i, name in enumerate(["step_c", "step_a", "step_b"]):
            await create_workflow_step(
                db_session, exec_id, i, "tool_call", name
            )
        await db_session.commit()

        steps = await list_workflow_steps_by_execution(db_session, exec_id)
        assert len(steps) == 3
        # Must be ordered by step_index
        assert [s.step_name for s in steps] == ["step_c", "step_a", "step_b"]

    @pytest.mark.asyncio
    async def test_list_steps_empty_execution(self, db_session):
        exec_id = await create_workflow_execution(
            db_session, conversation_id=1, mode="dynamic"
        )
        await db_session.commit()

        steps = await list_workflow_steps_by_execution(db_session, exec_id)
        assert steps == []
