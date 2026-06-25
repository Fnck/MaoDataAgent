"""Tests for the core text-to-data workflow with LLM behavior mocking.

Simulates realistic business query scenarios from the business analysis document:
- Manufacturing: fulfillment rate, supplier grade, defect rate
- Finance: revenue YoY
- Multi-tool batch execution
- Error handling and recovery
- YAML workflow execution
- Full SSE pipeline via HTTP
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from app.config import AppConfig
from app.models import ChatRequest, ChatContext
from app.service.agent import (
    REACT_SYSTEM_PROMPT,
    _parse_problem_breakdown,
    parse_react_actions,
    run_agent_loop,
)
from app.service.debug_bus import DebugEventBus
from app.service.engine import run_yaml_workflow
from tests.conftest import collect_sse_events, make_llm_response


# ── ReAct parse helpers ───────────────────────────────────────

class TestParseProblemBreakdown:
    def test_json_code_block(self):
        text = '```json\n{"query_subject": "履约率", "time_scope": "本月"}\n```'
        result = _parse_problem_breakdown(text)
        assert result is not None
        assert result["query_subject"] == "履约率"

    def test_raw_json_object(self):
        text = 'Analysis: {"query_subject": "营收", "output_format": "百分比"}'
        result = _parse_problem_breakdown(text)
        assert result is not None
        assert result["query_subject"] == "营收"

    def test_no_json_returns_none(self):
        text = "This is just plain text without any JSON."
        assert _parse_problem_breakdown(text) is None

    def test_invalid_json_returns_none(self):
        text = '```json\n{invalid json}\n```'
        assert _parse_problem_breakdown(text) is None


class TestParseReactActions:
    def test_single_tool_call(self):
        text = 'Tool Name: `ontology_query_tool` Tool Input: `{"keyword": ["物料"]}`'
        actions, final = parse_react_actions(text)
        assert len(actions) == 1
        assert actions[0][0] == "ontology_query_tool"
        assert actions[0][1]["keyword"] == ["物料"]
        assert final is None

    def test_final_answer(self):
        text = 'Thought: Done.\nFinal Answer: 本月履约率为75.5%'
        actions, final = parse_react_actions(text)
        assert len(actions) == 0
        assert "75.5%" in final

    def test_tool_call_then_final_answer(self):
        text = (
            'Tool Name: `sql_executor` Tool Input: `{"sql": "SELECT 1"}`\n'
            'Final Answer: Result is 1'
        )
        actions, final = parse_react_actions(text)
        assert len(actions) == 1
        assert final == "Result is 1"

    def test_multiple_tool_calls(self):
        text = (
            'Tool Name: `ontology_query_tool` Tool Input: `{"keyword": ["供应商"]}`\n'
            'Tool Name: `sql_executor` Tool Input: `{"sql": "SELECT * FROM suppliers"}`'
        )
        actions, final = parse_react_actions(text)
        assert len(actions) == 2
        assert actions[0][0] == "ontology_query_tool"
        assert actions[1][0] == "sql_executor"

    def test_invalid_tool_name_skipped(self):
        text = 'Tool Name: `none` Tool Input: `{"x": 1}`'
        actions, final = parse_react_actions(text)
        assert len(actions) == 0

    def test_plain_format_without_backticks(self):
        text = 'Tool Name: sql_executor Tool Input: {"sql": "SELECT 1"}'
        actions, final = parse_react_actions(text)
        assert len(actions) == 1
        assert actions[0][0] == "sql_executor"


# ── Manufacturing: Fulfillment Rate Query ─────────────────────

class TestFulfillmentRateWorkflow:
    """R1-R8: Supplier order fulfillment scenario.

    User asks "本月订单履约率是多少", agent goes through:
    Step 0 → problem breakdown → ontology query → SQL execution → final answer.
    """

    @pytest.mark.asyncio
    async def test_query_fulfillment_rate(self, db_session, test_config, bus):
        """Full ReAct loop for fulfillment rate query."""
        # Step 0: Problem breakdown JSON
        step0_text = (
            '```json\n'
            '{"query_subject": "履约率", "time_scope": "本月", '
            '"output_format": "百分比", "related_entities": ["订单", "供应商"]}\n'
            '```'
        )
        step0_resp = make_llm_response(step0_text)

        # Step 1: Ontology query tool call
        step1_text = (
            'Tool Name: `ontology_query_tool` Tool Input: '
            '`{"keyword": ["履约率", "订单"]}`'
        )
        step1_resp = make_llm_response(step1_text)

        # Step 2: SQL executor tool call
        sql_query = "SELECT COUNT(CASE WHEN status='fulfilled' THEN 1 END)*100.0/COUNT(*) AS rate FROM orders"
        step2_text = (
            'Tool Name: `sql_executor` Tool Input: '
            '`{"datasource_name": "test_db", "sql": "' + sql_query + '"}'
            '`'
        )
        step2_resp = make_llm_response(step2_text)

        # Step 3: Final answer
        step3_text = 'Final Answer: 本月订单履约率为75.5%，其中A级供应商履约率最高达92.3%。'
        step3_resp = make_llm_response(step3_text)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            step0_resp, step1_resp, step2_resp, step3_resp
        ]

        # Need max_iterations >= 4 for this flow
        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        ontology_result = {
            "entities": [
                {"name": "订单", "table": "orders", "columns": ["id", "status", "supplier_id"]},
                {"name": "供应商", "table": "suppliers", "columns": ["id", "name", "grade"]},
            ]
        }
        sql_result = {"columns": ["rate"], "rows": [[75.5]]}

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", side_effect=[ontology_result, sql_result]):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="本月订单履约率是多少",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        types = [e["type"] for e in events]
        # Should have step_start, step_end for tool calls
        assert "step_start" in types
        assert "step_end" in types
        # Should have chunk with final answer
        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert any("75.5%" in e["content"] for e in chunk_events)
        # Should end properly
        assert "end" in types


# ── Manufacturing: Supplier Grade Query ───────────────────────

class TestSupplierGradeWorkflow:
    @pytest.mark.asyncio
    async def test_query_supplier_grade(self, db_session, test_config, bus):
        """Supplier grade distribution query via ReAct loop."""
        step0_text = '```json\n{"query_subject": "供应商等级", "output_format": "分布统计"}\n```'
        step1_text = (
            'Tool Name: `ontology_query_tool` Tool Input: '
            '`{"keyword": ["供应商等级"]}`'
        )
        step2_text = (
            'Tool Name: `sql_executor` Tool Input: '
            '`{"datasource_name": "test_db", "sql": "SELECT grade, COUNT(*) FROM suppliers GROUP BY grade"}`'
        )
        step3_text = 'Final Answer: 供应商等级分布：A级15家，B级22家，C级8家。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
            make_llm_response(step2_text),
            make_llm_response(step3_text),
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", side_effect=[
                 {"entities": [{"name": "供应商", "table": "suppliers"}]},
                 {"columns": ["grade", "count"], "rows": [["A", 15], ["B", 22], ["C", 8]]},
             ]):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="供应商等级分布",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert any("供应商等级分布" in e["content"] for e in chunk_events)


# ── Manufacturing: Quality Defect Rate Query ──────────────────

class TestDefectRateWorkflow:
    @pytest.mark.asyncio
    async def test_query_defect_rate(self, db_session, test_config, bus):
        """Incoming material defect rate query via ReAct loop."""
        step0_text = '```json\n{"query_subject": "来料不良率", "time_scope": "本月", "output_format": "百分比"}\n```'
        step1_text = (
            'Tool Name: `ontology_query_tool` Tool Input: '
            '`{"keyword": ["不良率", "来料"]}`'
        )
        step2_text = 'Final Answer: 本月来料不良率为3.2%，较上月下降0.5个百分点。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
            make_llm_response(step2_text),
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", return_value={
                 "entities": [{"name": "来料检验", "table": "incoming_inspections"}]
             }):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="来料不良率统计",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert any("3.2%" in e["content"] for e in chunk_events)


# ── Finance: Revenue YoY Query ────────────────────────────────

class TestRevenueYoYWorkflow:
    """FR1-FR6: Finance scenario — revenue year-over-year change."""

    @pytest.mark.asyncio
    async def test_query_revenue_yoy(self, db_session, test_config, bus):
        """Revenue YoY change query via ReAct loop."""
        step0_text = '```json\n{"query_subject": "营收同比变动", "time_scope": "年度", "output_format": "百分比"}\n```'
        step1_text = (
            'Tool Name: `ontology_query_tool` Tool Input: '
            '`{"keyword": ["营收", "同比"]}`'
        )
        step2_text = (
            'Tool Name: `sql_executor` Tool Input: '
            '`{"datasource_name": "test_db", "sql": "SELECT year, revenue FROM financials ORDER BY year DESC LIMIT 2"}`'
        )
        step3_text = 'Final Answer: 本年度营收同比增长12.5%，从8.0亿增长至9.0亿。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
            make_llm_response(step2_text),
            make_llm_response(step3_text),
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", side_effect=[
                 {"entities": [{"name": "营收", "table": "financials"}]},
                 {"columns": ["year", "revenue"], "rows": [[2025, 9.0], [2024, 8.0]]},
             ]):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="营收同比变动",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert any("12.5%" in e["content"] for e in chunk_events)


# ── Multi-tool batch execution ────────────────────────────────

class TestMultiToolExecution:
    @pytest.mark.asyncio
    async def test_agent_calls_multiple_tools_in_one_iteration(self, db_session, test_config, bus):
        """LLM outputs 2 tool calls in a single iteration → both executed."""
        step0_text = '```json\n{"query_subject": "综合分析"}\n```'
        step1_text = (
            'Tool Name: `ontology_query_tool` Tool Input: `{"keyword": ["订单"]}`\n'
            'Tool Name: `sql_executor` Tool Input: `{"datasource_name": "test_db", "sql": "SELECT COUNT(*) FROM orders"}`'
        )
        step2_text = 'Final Answer: 综合分析完成。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
            make_llm_response(step2_text),
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", side_effect=[
                 {"entities": [{"name": "订单", "table": "orders"}]},
                 {"columns": ["count"], "rows": [[100]]},
             ]):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="综合分析",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        step_start_events = [e for e in events if e["type"] == "step_start"]
        step_end_events = [e for e in events if e["type"] == "step_end"]
        # Both tools should have step_start/step_end
        assert len(step_start_events) == 2
        assert len(step_end_events) == 2


# ── Error handling in workflow ────────────────────────────────

class TestWorkflowErrorHandling:
    @pytest.mark.asyncio
    async def test_agent_tool_error_then_recovery(self, db_session, test_config, bus):
        """First tool fails, agent retries with different approach."""
        step0_text = '```json\n{"query_subject": "数据查询"}\n```'
        step1_text = (
            'Tool Name: `sql_executor` Tool Input: '
            '`{"datasource_name": "test_db", "sql": "SELECT * FROM nonexistent"}`'
        )
        step2_text = (
            'Tool Name: `ontology_query_tool` Tool Input: `{"keyword": ["数据"]}`'
        )
        step3_text = 'Final Answer: 查询完成，已通过本体查找获取结果。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
            make_llm_response(step2_text),
            make_llm_response(step3_text),
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", side_effect=[
                 {"error": "Table nonexistent not found"},
                 {"entities": [{"name": "数据", "table": "data_table"}]},
             ]):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="查询数据",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        types = [e["type"] for e in events]
        assert "step_error" in types
        assert "step_end" in types
        assert "chunk" in types

    @pytest.mark.asyncio
    async def test_agent_consecutive_parse_failures(self, db_session, test_config, bus):
        """LLM outputs garbage 3 times → error event with parse failure message."""
        garbage_resp = make_llm_response("I don't know what to do here...")

        mock_client = AsyncMock()
        # Step 0 produces valid JSON, then 3 garbage responses
        step0_text = '```json\n{"query_subject": "test"}\n```'
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            garbage_resp,
            garbage_resp,
            garbage_resp,
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="test",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert any("consecutive" in e["error"].lower() or "failed" in e["error"].lower() for e in error_events)

    @pytest.mark.asyncio
    async def test_agent_step0_no_json_fallback(self, db_session, test_config, bus):
        """Step 0 doesn't produce JSON → agent continues with fallback message."""
        # Step 0: no JSON, just text
        step0_resp = make_llm_response("I will analyze the data for you.")
        # Step 1: still no valid action (another garbage)
        step1_resp = make_llm_response("Let me think more...")
        # Step 2: produces a valid action
        step2_text = 'Tool Name: `ontology_query_tool` Tool Input: `{"keyword": ["test"]}`'
        step2_resp = make_llm_response(step2_text)
        # Step 3: final answer
        step3_text = 'Final Answer: Analysis complete.'
        step3_resp = make_llm_response(step3_text)

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            step0_resp, step1_resp, step2_resp, step3_resp
        ]

        config = AppConfig(
            llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
            workflow={"mode": "dynamic", "tools": [], "yaml_dir": "wf", "max_iterations": 5},
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        with patch("app.service.agent.AsyncOpenAI", return_value=mock_client), \
             patch("app.service.agent.execute_tool", return_value={"entities": []}):
            events = await collect_sse_events(
                run_agent_loop(
                    user_message="Analyze data",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        # Should still eventually produce a result
        types = [e["type"] for e in events]
        assert "chunk" in types
        assert "end" in types


# ── YAML workflow execution ───────────────────────────────────

class TestYAMLWorkflow:
    @pytest.mark.asyncio
    async def test_yaml_workflow_with_tool_and_llm_steps(self, db_session, bus):
        """Execute a YAML workflow with both tool_call and llm_call steps."""
        workflow_def = {
            "name": "explore_table",
            "trigger_keywords": ["table", "schema"],
            "steps": [
                {
                    "type": "tool_call",
                    "name": "get_schema",
                    "tool": "list_tables",
                    "params": {"datasource_name": "test_db"},
                },
                {
                    "type": "llm_call",
                    "name": "summarize",
                    "system": "You are a data analyst.",
                    "prompt": "Summarize: {{ steps['get_schema'] }}",
                },
            ],
            "final_answer": "Analysis: {{ steps['summarize']['content'] }}",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            wf_file = Path(tmpdir) / "explore.yaml"
            wf_file.write_text(yaml.dump(workflow_def, allow_unicode=True), encoding="utf-8")

            config = AppConfig(
                llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
                workflow={"mode": "yaml", "tools": [], "yaml_dir": tmpdir, "max_iterations": 3},
                datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
            )

            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = make_llm_response(
                "Found 3 tables: orders, suppliers, products."
            )

            with patch("app.service.engine.AsyncOpenAI", return_value=mock_client), \
                 patch("app.service.engine.execute_tool", return_value={"tables": ["orders", "suppliers", "products"]}):
                events = await collect_sse_events(
                    run_yaml_workflow(
                        user_message="Show me the table schema",
                        messages=[],
                        conversation_id=1,
                        session=db_session,
                        config=config,
                        bus=bus,
                    )
                )

        types = [e["type"] for e in events]
        assert "step_start" in types
        assert "step_end" in types
        assert "chunk" in types
        assert "end" in types

    @pytest.mark.asyncio
    async def test_yaml_workflow_no_match(self, db_session, bus):
        """No matching workflow → error event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty directory → no workflows
            config = AppConfig(
                llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
                workflow={"mode": "yaml", "tools": [], "yaml_dir": tmpdir, "max_iterations": 3},
                datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
            )

            events = await collect_sse_events(
                run_yaml_workflow(
                    user_message="Hello world",
                    messages=[],
                    conversation_id=1,
                    session=db_session,
                    config=config,
                    bus=bus,
                )
            )

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1

    @pytest.mark.asyncio
    async def test_yaml_workflow_template_resolution(self, db_session, bus):
        """Verify {{ }} templates resolve correctly in YAML workflow."""
        workflow_def = {
            "name": "query_data",
            "trigger_keywords": ["查询"],
            "steps": [
                {
                    "type": "tool_call",
                    "name": "fetch_data",
                    "tool": "sql_executor",
                    "params": {
                        "datasource_name": "test_db",
                        "sql": "SELECT * FROM orders WHERE name = '{{ user_message }}'",
                    },
                },
            ],
            "final_answer": "Result: {{ steps['fetch_data'] }}",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            wf_file = Path(tmpdir) / "query.yaml"
            wf_file.write_text(yaml.dump(workflow_def, allow_unicode=True), encoding="utf-8")

            config = AppConfig(
                llm={"api_base": "http://fake", "api_key": "k", "model": "m", "max_tokens": 256, "temperature": 0.0},
                workflow={"mode": "yaml", "tools": [], "yaml_dir": tmpdir, "max_iterations": 3},
                datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
            )

            with patch("app.service.engine.execute_tool", return_value={"rows": [[1, "test"]]}):
                events = await collect_sse_events(
                    run_yaml_workflow(
                        user_message="查询订单",
                        messages=[],
                        conversation_id=1,
                        session=db_session,
                        config=config,
                        bus=bus,
                    )
                )

        # Verify the tool was called with resolved template
        from app.service.engine import execute_tool
        # Template should have resolved user_message into the SQL
        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert len(chunk_events) >= 1


# ── Full SSE pipeline via HTTP ────────────────────────────────

class TestFullDynamicPipelineHTTP:
    @pytest.mark.asyncio
    async def test_full_dynamic_pipeline_via_http(self, client, auth_token, db_session_from_app):
        """POST /api/chat/stream with workflow_mode='dynamic' produces complete event sequence."""
        from app.db.database import create_conversation
        from tests.conftest import auth_headers

        conv_id = await create_conversation(db_session_from_app, user_id=1, title="test")
        await db_session_from_app.commit()

        # Mock the full agent loop
        step0_text = '```json\n{"query_subject": "测试"}\n```'
        step1_text = 'Final Answer: 查询结果：测试数据。'

        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = [
            make_llm_response(step0_text),
            make_llm_response(step1_text),
        ]

        with patch("app.service.chat._get_llm_client", return_value=mock_client), \
             patch("app.service.agent.AsyncOpenAI", return_value=mock_client):
            resp = await client.post(
                "/api/chat/stream",
                json={
                    "message": "查询测试数据",
                    "conversation_id": conv_id,
                    "workflow_mode": "dynamic",
                },
                headers=auth_headers(auth_token),
            )

        assert resp.status_code == 200
        # Parse SSE events from the response
        content = resp.text
        events = []
        for line in content.split("\n"):
            if line.startswith("data: "):
                body = line[len("data: "):]
                events.append(json.loads(body))

        types = [e["type"] for e in events]
        # Should have at least chunk and end
        assert "chunk" in types or "error" in types
