from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.agent import run_agent_loop, REACT_SYSTEM_PROMPT
from tests.conftest import collect_sse_events, make_llm_response


# ── Tests ───────────────────────────────────────────────────

class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_simple_text_response(self, db_session, test_config, bus):
        """Agent returns a Final Answer on the second iteration (after step 0 breakdown)."""
        # Step 0: problem breakdown
        step0_resp = make_llm_response('```json\n{"query_subject": "greeting"}\n```')
        # Step 1: final answer
        step1_resp = make_llm_response("Final Answer: Here is your answer.")

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [step0_resp, step1_resp]

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Hello",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        types = [e["type"] for e in events]
        assert "chunk" in types
        assert "end" in types
        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert "Here is your answer." in chunk_events[0]["content"]

    @pytest.mark.asyncio
    async def test_single_tool_call(self, db_session, test_config, mocker, bus):
        """Agent calls one tool via ReAct text format, gets result, then produces final answer."""
        step0_resp = make_llm_response('```json\n{"query_subject": "tables"}\n```')
        step1_resp = make_llm_response(
            'Tool Name: `list_tables` Tool Input: `{"datasource_name": "test_db"}`'
        )
        step2_resp = make_llm_response("Final Answer: Found 3 tables.")

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [step0_resp, step1_resp, step2_resp]

        mocker.patch("app.service.agent.execute_tool", return_value={"tables": ["t1", "t2", "t3"]})

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="List tables",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        types = [e["type"] for e in events]
        assert "step_start" in types
        assert "step_end" in types
        assert "chunk" in types
        assert "end" in types

    @pytest.mark.asyncio
    async def test_tool_call_error(self, db_session, test_config, mocker, bus):
        """Agent calls a tool that fails, then still gets a final answer."""
        step0_resp = make_llm_response('```json\n{"query_subject": "data"}\n```')
        step1_resp = make_llm_response(
            'Tool Name: `sql_executor` Tool Input: `{"datasource_name": "x", "sql": "SELECT 1"}`'
        )
        step2_resp = make_llm_response("Final Answer: Sorry, the query failed.")

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [step0_resp, step1_resp, step2_resp]

        mocker.patch("app.service.agent.execute_tool", return_value={"error": "Connection refused"})

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Query data",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        types = [e["type"] for e in events]
        assert "step_start" in types
        assert "step_error" in types
        assert "chunk" in types
        assert "end" in types

    @pytest.mark.asyncio
    async def test_max_iterations_exhausted(self, db_session, test_config, mocker, bus):
        """Agent keeps calling tools and never produces text; max iterations reached."""
        # Step 0: valid breakdown, then keep calling tools
        step0_resp = make_llm_response('```json\n{"query_subject": "go"}\n```')
        tool_resp = make_llm_response(
            'Tool Name: `list_tables` Tool Input: `{"datasource_name": "test_db"}`'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [step0_resp, tool_resp, tool_resp]

        mocker.patch("app.service.agent.execute_tool", return_value={"tables": []})

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Go",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        last_event = events[-1]
        assert last_event["type"] == "error"
        assert "maximum iterations" in last_event["error"]

    @pytest.mark.asyncio
    async def test_llm_api_error(self, db_session, test_config, bus):
        """LLM raises an exception; agent should yield error event and return."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Hello",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        assert events[0]["type"] == "error"
        assert "API down" in events[0]["error"]

    @pytest.mark.asyncio
    async def test_system_prompt_included(self, db_session, test_config, bus):
        """Verify the system prompt is passed to the LLM."""
        step0_resp = make_llm_response('```json\n{"query_subject": "test"}\n```')
        step1_resp = make_llm_response("Final Answer: Done.")

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [step0_resp, step1_resp]

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Test",
                    messages=[{"role": "system", "content": "Old prompt"}],
                    conversation_id=1,
                    session=db_session,
                    config=test_config,
                    bus=bus,
                )
            )

        call_args = mock_client.chat.completions.create.call_args
        messages_sent = call_args.kwargs["messages"]
        system_msgs = [m for m in messages_sent if m["role"] == "system"]
        assert len(system_msgs) == 1
        # The system prompt includes the REACT_SYSTEM_PROMPT plus initialization context
        assert REACT_SYSTEM_PROMPT in system_msgs[0]["content"]
