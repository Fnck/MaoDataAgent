from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from app.service.engine import (
    _load_workflows,
    _match_workflow,
    _resolve_template,
    _sse_event,
)


# ── _sse_event ──────────────────────────────────────────────

class TestSSEEvent:
    def test_format(self):
        event = _sse_event({"type": "chunk", "content": "hello"})
        assert event == 'data: {"type": "chunk", "content": "hello"}\n\n'

    def test_roundtrip(self):
        data = {"type": "step_start", "step_id": 1, "step_name": "test"}
        raw = _sse_event(data)
        assert raw.startswith("data: ")
        assert raw.endswith("\n\n")
        # Parse back
        body = raw[len("data: "):-2]
        parsed = json.loads(body)
        assert parsed == data


# ── _load_workflows ─────────────────────────────────────────

class TestLoadWorkflows:
    def test_non_existent_dir(self):
        result = _load_workflows("tests/nonexistent_dir_12345")
        assert result == []

    def test_loads_valid_yaml_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wf1 = tmp / "workflow_a.yaml"
            wf2 = tmp / "workflow_b.yaml"

            wf1.write_text(yaml.dump({
                "name": "Workflow A",
                "trigger_keywords": ["table", "schema"],
                "steps": [],
            }), encoding="utf-8")

            wf2.write_text(yaml.dump({
                "name": "Workflow B",
                "trigger_keywords": ["file", "read"],
                "steps": [],
            }), encoding="utf-8")

            result = _load_workflows(str(tmp))
            assert len(result) == 2
            assert result[0]["name"] == "Workflow A"
            assert result[1]["name"] == "Workflow B"
            assert result[0]["_file"] == str(wf1)
            assert result[1]["_file"] == str(wf2)

    def test_skips_invalid_yaml(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = tmp / "bad.yaml"
            bad.write_text("[[[ invalid yaml : }}}", encoding="utf-8")

            result = _load_workflows(str(tmp))
            assert result == []

    def test_skips_empty_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            empty = tmp / "empty.yaml"
            empty.write_text("", encoding="utf-8")
            result = _load_workflows(str(tmp))
            assert result == []

    def test_sorts_files_alphabetically(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for name in ["c.yaml", "a.yaml", "b.yaml"]:
                f = tmp / name
                f.write_text(yaml.dump({"name": name}), encoding="utf-8")

            result = _load_workflows(str(tmp))
            names = [w["name"] for w in result]
            assert names == ["a.yaml", "b.yaml", "c.yaml"]


# ── _match_workflow ─────────────────────────────────────────

class TestMatchWorkflow:
    SAMPLE_WORKFLOWS = [
        {
            "name": "explore_table",
            "trigger_keywords": ["table", "schema", "columns"],
            "steps": [],
        },
        {
            "name": "read_file",
            "trigger_keywords": ["file", "read"],
            "steps": [],
        },
    ]

    def test_exact_keyword_match(self):
        result = _match_workflow("show me the table schema", self.SAMPLE_WORKFLOWS)
        assert result is not None
        assert result["name"] == "explore_table"

    def test_case_insensitive_match(self):
        result = _match_workflow("READ the FILE", self.SAMPLE_WORKFLOWS)
        assert result is not None
        assert result["name"] == "read_file"

    def test_partial_match(self):
        result = _match_workflow("what columns are in this TABLE?", self.SAMPLE_WORKFLOWS)
        assert result is not None
        assert result["name"] == "explore_table"

    def test_first_match_wins(self):
        wf = _match_workflow("explore the file table schema", self.SAMPLE_WORKFLOWS)
        assert wf is not None
        # "table" appears first in explore_table keywords
        assert wf["name"] == "explore_table"

    def test_no_match(self):
        result = _match_workflow("what is the weather?", self.SAMPLE_WORKFLOWS)
        assert result is None

    def test_empty_workflows(self):
        result = _match_workflow("show table", [])
        assert result is None

    def test_no_keywords(self):
        wf = {"name": "no_keywords"}
        result = _match_workflow("hello", [wf])
        assert result is None


# ── _resolve_template ───────────────────────────────────────

class TestResolveTemplate:
    def test_simple_variable(self):
        ctx = {"name": "DataAgent"}
        result = _resolve_template("Hello, {{ name }}!", ctx)
        assert result == "Hello, DataAgent!"

    def test_nested_access(self):
        ctx = {"context": {"selected_files": ["report.csv"]}}
        result = _resolve_template("File: {{ context['selected_files'][0] }}", ctx)
        assert result == "File: report.csv"

    def test_dict_to_json(self):
        ctx = {"data": {"key": "value"}}
        result = _resolve_template("{{ data }}", ctx)
        assert result == json.dumps({"key": "value"}, ensure_ascii=False)

    def test_list_to_json(self):
        ctx = {"items": [1, 2, 3]}
        result = _resolve_template("{{ items }}", ctx)
        assert result == json.dumps([1, 2, 3], ensure_ascii=False)

    def test_multiple_placeholders(self):
        ctx = {"a": "foo", "b": "bar"}
        result = _resolve_template("{{ a }} and {{ b }}", ctx)
        assert result == "foo and bar"

    def test_no_placeholders(self):
        result = _resolve_template("plain text", {})
        assert result == "plain text"

    def test_failed_resolution_keeps_placeholder(self, caplog):
        # The regex captures content without outer spaces, so the result
        # will be something containing the original expression text
        result = _resolve_template("{{ undefined_var }}", {})
        # The regex \{\{(.+?)\}\} captures "undefined_var" (without spaces)
        # and on failure returns "{{undefined_var}}"
        assert "undefined_var" in result

    def test_user_message(self):
        ctx = {"user_message": "How many users?"}
        result = _resolve_template("Q: {{ user_message }}", ctx)
        assert result == "Q: How many users?"

    def test_steps_output_access(self):
        ctx = {
            "steps": {
                "get_schema": {"columns": [{"name": "id"}, {"name": "name"}]},
            },
        }
        result = _resolve_template(
            "First column: {{ steps['get_schema']['columns'][0]['name'] }}",
            ctx,
        )
        assert result == "First column: id"