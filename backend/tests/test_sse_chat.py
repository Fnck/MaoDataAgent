"""Tests for the SSE chat service layer and HTTP endpoint.

Covers:
- Simple streaming mode (_generate)
- Workflow classification (_classify_workflow_mode)
- Memory compaction (_generate_memory)
- Context building helpers
- HTTP-level SSE endpoint
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.chat import (
    SYSTEM_PROMPT,
    CLASSIFY_PROMPT,
    _build_user_prompt,
    _classify_workflow_mode,
    _generate,
    _generate_memory,
    stream_chat,
)
from app.service.debug_bus import DebugEventBus, _sse_event
from app.models import ChatRequest, ChatContext
from tests.conftest import collect_sse_events, make_llm_response, make_streaming_response


# ── _generate (simple streaming mode) ─────────────────────────

class TestGenerate:
    @pytest.mark.asyncio
    async def test_simple_chat_stream(self, db_session, test_config, bus):
        """Mock streaming LLM yields chunk + end events."""
        chunks = ["Hello", " world", "!"]
        mock_stream = make_streaming_response(chunks)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream

        body = ChatRequest(message="Hi", conversation_id=1)

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            events = await collect_sse_events(
                _generate(body, [{"role": "user", "content": "Hi"}], test_config, db_session, bus)
            )

        types = [e["type"] for e in events]
        assert "chunk" in types
        assert "end" in types
        # Verify content accumulation
        chunk_events = [e for e in events if e["type"] == "chunk"]
        combined = "".join(e["content"] for e in chunk_events)
        assert combined == "Hello world!"

    @pytest.mark.asyncio
    async def test_streaming_with_multiple_chunks(self, db_session, test_config, bus):
        """Three delta chunks produce three chunk events."""
        chunks = ["Part1 ", "Part2 ", "Part3"]
        mock_stream = make_streaming_response(chunks)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream

        body = ChatRequest(message="Test", conversation_id=1)

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            events = await collect_sse_events(
                _generate(body, [{"role": "user", "content": "Test"}], test_config, db_session, bus)
            )

        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert len(chunk_events) == 3

    @pytest.mark.asyncio
    async def test_streaming_llm_error(self, db_session, test_config, bus):
        """LLM raises exception → error event yielded."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("LLM unavailable")

        body = ChatRequest(message="Hi", conversation_id=1)

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            events = await collect_sse_events(
                _generate(body, [{"role": "user", "content": "Hi"}], test_config, db_session, bus)
            )

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "LLM unavailable" in events[0]["error"]

    @pytest.mark.asyncio
    async def test_streaming_saves_assistant_message(self, db_session, test_config, bus):
        """After streaming completes, assistant message is saved to DB."""
        chunks = ["Answer"]
        mock_stream = make_streaming_response(chunks)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream

        body = ChatRequest(message="Q", conversation_id=1)

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            events = await collect_sse_events(
                _generate(body, [{"role": "user", "content": "Q"}], test_config, db_session, bus)
            )

        end_events = [e for e in events if e["type"] == "end"]
        assert len(end_events) == 1
        assert "message_id" in end_events[0]


# ── _classify_workflow_mode ───────────────────────────────────

class TestClassifyWorkflowMode:
    @pytest.mark.asyncio
    async def test_classify_as_data_query(self, test_config, bus):
        """LLM returns 'yes' → mode='dynamic'."""
        mock_resp = make_llm_response("yes")
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            result = await _classify_workflow_mode("查询上月销售额", test_config, bus)

        assert result == "dynamic"

    @pytest.mark.asyncio
    async def test_classify_as_general_chat(self, test_config, bus):
        """LLM returns 'no' → mode=None."""
        mock_resp = make_llm_response("no")
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            result = await _classify_workflow_mode("什么是SQL?", test_config, bus)

        assert result is None

    @pytest.mark.asyncio
    async def test_classify_failure_defaults_to_none(self, test_config, bus):
        """LLM raises exception → returns None (graceful fallback)."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("timeout")

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            result = await _classify_workflow_mode("查询数据", test_config, bus)

        assert result is None


# ── _generate_memory ──────────────────────────────────────────

class TestGenerateMemory:
    @pytest.mark.asyncio
    async def test_memory_generation_success(self, test_config, bus):
        """LLM returns a summary → memory text returned."""
        mock_resp = make_llm_response("User queried sales data for Q1, total was 1.2M.")
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_resp

        older_messages = [
            {"role": "user", "content": "Show Q1 sales"},
            {"role": "assistant", "content": "Q1 sales total: 1.2M"},
        ]

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            memory = await _generate_memory(older_messages, "What about Q2?", test_config, bus)

        assert "1.2M" in memory or "sales" in memory.lower()

    @pytest.mark.asyncio
    async def test_memory_failure_falls_back_gracefully(self, test_config, bus):
        """LLM error → returns empty string, no crash."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("fail")

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            memory = await _generate_memory(
                [{"role": "user", "content": "hi"}], "next Q", test_config, bus
            )

        assert memory == ""


# ── Context building helpers ──────────────────────────────────

class TestContextBuilding:
    def test_build_user_prompt_with_context(self):
        result = _build_user_prompt("What is sales?", "Table: orders")
        assert result.startswith("[Context]")
        assert "[User Question]" in result
        assert "What is sales?" in result

    def test_build_user_prompt_without_context(self):
        result = _build_user_prompt("Hello", "")
        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_build_context_text_with_tables(self, test_config):
        """Context with selected tables includes table schema info."""
        from app.service.chat import _build_context_text

        body = ChatRequest(
            message="Q",
            conversation_id=1,
            context=ChatContext(selected_tables=["test_db.orders"]),
        )

        with patch("app.service.chat.get_columns") as mock_cols:
            mock_cols.return_value = [
                MagicMock(name="id", type="INTEGER", comment=None),
                MagicMock(name="amount", type="REAL", comment="order amount"),
            ]
            result = await _build_context_text(body)

        assert "### Selected Tables" in result
        assert "test_db.orders" in result
        assert "amount" in result

    @pytest.mark.asyncio
    async def test_build_context_text_with_files(self):
        """Context with selected files includes file content."""
        from app.service.chat import _build_context_text

        body = ChatRequest(
            message="Q",
            conversation_id=1,
            context=ChatContext(selected_files=["data/report.csv"]),
        )

        with patch("app.service.chat.read_file", return_value="col1,col2\n1,2"):
            result = await _build_context_text(body)

        assert "### Selected Files" in result
        assert "data/report.csv" in result

    @pytest.mark.asyncio
    async def test_build_context_text_none_context(self):
        """No context → empty string."""
        from app.service.chat import _build_context_text

        result = await _build_context_text(None)
        assert result == ""


# ── HTTP-level SSE endpoint ───────────────────────────────────

class TestSSEHTTPEndpoint:
    @pytest.mark.asyncio
    async def test_sse_endpoint_returns_event_stream(self, client, auth_token, db_session_from_app):
        """POST /api/chat/stream returns text/event-stream content type."""
        from app.db.database import create_conversation
        from tests.conftest import auth_headers

        conv_id = await create_conversation(db_session_from_app, user_id=1, title="test")
        await db_session_from_app.commit()

        # Mock the entire LLM call chain for simple mode
        mock_stream = make_streaming_response(["Hi there"])
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream

        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            resp = await client.post(
                "/api/chat/stream",
                json={
                    "message": "Hello",
                    "conversation_id": conv_id,
                    "workflow_mode": "none",
                },
                headers=auth_headers(auth_token),
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_sse_endpoint_auth_required(self, client, db_session_from_app):
        """No token → 401 or 403."""
        resp = await client.post(
            "/api/chat/stream",
            json={"message": "Hello", "conversation_id": 1},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_sse_endpoint_conversation_not_found(self, client, auth_token):
        """Invalid conversation_id → 404."""
        from tests.conftest import auth_headers

        mock_client = AsyncMock()
        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            resp = await client.post(
                "/api/chat/stream",
                json={"message": "Hello", "conversation_id": 99999, "workflow_mode": "none"},
                headers=auth_headers(auth_token),
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sse_endpoint_forbidden_conversation(self, client, auth_token, db_session_from_app):
        """Accessing another user's conversation → 403."""
        from app.auth import hash_password
        from app.db.database import create_user, create_conversation
        from tests.conftest import auth_headers

        # Create user B and their conversation
        user_b = await create_user(
            db_session_from_app, username="userB",
            password_hash=hash_password("passB"), role="user",
        )
        await db_session_from_app.commit()

        conv_id = await create_conversation(db_session_from_app, user_id=user_b, title="private")
        await db_session_from_app.commit()

        # auth_token is for testuser (user A), try to access user B's conversation
        mock_client = AsyncMock()
        with patch("app.service.chat._get_llm_client", return_value=mock_client):
            resp = await client.post(
                "/api/chat/stream",
                json={"message": "Hello", "conversation_id": conv_id, "workflow_mode": "none"},
                headers=auth_headers(auth_token),
            )
        assert resp.status_code == 403
