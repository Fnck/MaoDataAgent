from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.tools import (
    execute_tool,
    get_tool_schemas,
    register_tool,
    register_builtin_tools,
    _TOOL_REGISTRY,
)
from app.config import AppConfig, _config


# ── Fixture to reset registry before each test ──────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """Clear tool registry before each test."""
    _TOOL_REGISTRY.clear()
    yield
    _TOOL_REGISTRY.clear()


# ── Tool registration tests ─────────────────────────────────

class TestToolRegistration:
    def test_register_tool_adds_to_registry(self):
        async def dummy(_params):
            return {"ok": True}

        register_tool("dummy", {"description": "Test tool", "parameters": {}}, dummy)
        assert "dummy" in _TOOL_REGISTRY
        assert _TOOL_REGISTRY["dummy"]["fn"] is dummy

    def test_register_builtin_tools_populates_registry(self):
        register_builtin_tools()
        names = set(_TOOL_REGISTRY.keys())
        assert names == {"execute_sql", "list_tables", "get_table_schema", "read_file", "list_files"}

    def test_register_builtin_tools_idempotent(self):
        register_builtin_tools()
        count = len(_TOOL_REGISTRY)
        register_builtin_tools()
        assert len(_TOOL_REGISTRY) == count


# ── get_tool_schemas tests ──────────────────────────────────

class TestGetToolSchemas:
    def test_returns_openai_compatible_schemas(self):
        async def dummy(_params):
            return {"ok": True}

        register_tool("execute_sql", {
            "description": "Execute a read-only SQL query",
            "parameters": {
                "datasource_name": {"type": "string", "description": "Name of datasource"},
                "query": {"type": "string", "description": "SQL query"},
            },
        }, dummy)

        schemas = get_tool_schemas()
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "execute_sql"
        assert "parameters" in schema["function"]
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "datasource_name" in params["properties"]
        assert "query" in params["properties"]

    def test_required_params_are_listed(self):
        async def dummy(_params):
            return {"ok": True}

        register_tool("test", {
            "description": "Test",
            "parameters": {
                "required_param": {"type": "string"},
                "optional_param": {"type": "string", "required": False},
            },
        }, dummy)

        schemas = get_tool_schemas()
        required = schemas[0]["function"]["parameters"]["required"]
        assert "required_param" in required
        assert "optional_param" not in required

    def test_empty_registry(self):
        schemas = get_tool_schemas()
        assert schemas == []


# ── execute_tool tests ──────────────────────────────────────

class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        result = await execute_tool("nonexistent", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_registered_tool(self):
        async def echo(params):
            return {"echo": params.get("message", "")}

        register_tool("echo", {"description": "Echo", "parameters": {}}, echo)
        result = await execute_tool("echo", {"message": "hello"})
        assert result == {"echo": "hello"}

    @pytest.mark.asyncio
    async def test_tool_exception_is_caught(self):
        async def broken(_params):
            raise RuntimeError("boom")

        register_tool("broken", {"description": "Broken", "parameters": {}}, broken)
        result = await execute_tool("broken", {})
        assert "error" in result
        assert "boom" in result["error"]


# ── execute_sql tool tests ──────────────────────────────────

class TestExecuteSql:
    def setup_method(self):
        register_builtin_tools()

    @pytest.mark.asyncio
    async def test_non_select_blocked(self):
        result = await execute_tool("execute_sql", {
            "datasource_name": "test_db",
            "query": "DROP TABLE users",
        })
        assert "error" in result
        assert "Only SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_insert_blocked(self):
        result = await execute_tool("execute_sql", {
            "datasource_name": "test_db",
            "query": "INSERT INTO users VALUES (1)",
        })
        assert "error" in result
        assert "Only SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_datasource(self):
        result = await execute_tool("execute_sql", {
            "datasource_name": "nonexistent",
            "query": "SELECT 1",
        })
        assert "error" in result
        assert "Datasource not found" in result["error"]

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=True)
    async def test_select_query_success(self, mock_exists, mocker):
        mock_aiosqlite = mocker.patch("app.service.tools.aiosqlite")

        class MockRow(dict):
            pass

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall = AsyncMock(return_value=[
            MockRow(id=1, name="Alice"),
            MockRow(id=2, name="Bob"),
        ])
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=None)

        mock_conn = MagicMock()
        mock_conn.execute = MagicMock(return_value=mock_cursor)
        mock_conn.row_factory = None
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        # aiosqlite.connect must return an async context manager
        mock_aiosqlite.connect = MagicMock(return_value=mock_conn)

        import app.config as config_module

        # Inject test config with a valid datasource
        saved = config_module._config
        config_module._config = AppConfig(
            datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
        )

        try:
            result = await execute_tool("execute_sql", {
                "datasource_name": "test_db",
                "query": "SELECT id, name FROM users",
            })
            assert "columns" in result
            assert result["columns"] == ["id", "name"]
            assert result["row_count"] == 2
            assert len(result["rows"]) == 2
        finally:
            config_module._config = saved


# ── list_tables tool test ───────────────────────────────────

class TestListTables:
    def setup_method(self):
        register_builtin_tools()

    @pytest.mark.asyncio
    async def test_list_tables_delegates_to_datasource(self):
        with patch("app.service.datasource.list_tables") as mock_list:
            from app.models import TableInfo

            mock_list.return_value = [
                TableInfo(datasource_name="ds1", table_name="table_a"),
                TableInfo(datasource_name="ds1", table_name="table_b"),
            ]
            result = await execute_tool("list_tables", {})
            assert "tables" in result
            assert "ds1.table_a" in result["tables"]
            assert "ds1.table_b" in result["tables"]


class TestGetTableSchema:
    def setup_method(self):
        register_builtin_tools()

    @pytest.mark.asyncio
    async def test_invalid_table_ref_format(self):
        result = await execute_tool("get_table_schema", {"table_ref": "no_dot_format"})
        assert "error" in result
        assert "format" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_delegates_to_datacolumn_service(self):
        with patch("app.service.datasource.get_columns") as mock_cols:
            from app.models import ColumnInfo

            mock_cols.return_value = [
                ColumnInfo(name="id", type="INTEGER", comment="PK"),
                ColumnInfo(name="name", type="TEXT", comment=None),
            ]
            result = await execute_tool("get_table_schema", {"table_ref": "ds.table"})
            mock_cols.assert_called_once_with("ds", "table")
            assert "columns" in result
            assert len(result["columns"]) == 2
            assert result["columns"][0]["name"] == "id"
            assert result["columns"][0]["type"] == "INTEGER"


class TestFileTools:
    def setup_method(self):
        register_builtin_tools()

    @pytest.mark.asyncio
    async def test_read_file_delegates_to_storage(self):
        with patch("app.service.storage.read_file") as mock_read:
            mock_read.return_value = "file contents here"
            result = await execute_tool("read_file", {"key": "folder/file.txt"})
            mock_read.assert_called_once_with("folder/file.txt")
            assert result == {"key": "folder/file.txt", "content": "file contents here"}

    @pytest.mark.asyncio
    async def test_list_files_delegates_to_storage(self):
        with patch("app.service.storage.list_files") as mock_list:
            from app.models import StorageItem

            mock_list.return_value = [
                StorageItem(key="a.txt", size=100, is_dir=False),
                StorageItem(key="sub/", is_dir=True),
            ]
            result = await execute_tool("list_files", {"prefix": ""})

            assert "items" in result
            assert len(result["items"]) == 2
            assert result["items"][0]["key"] == "a.txt"
            assert not result["items"][0]["is_dir"]
            assert result["items"][1]["is_dir"]