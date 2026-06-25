from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.service.tools import execute_tool

router = APIRouter(prefix="/api/tools/test", tags=["tools-test"])

TOOL_DESCRIPTIONS = {
    "ontology_query_tool": {
        "params": {"keyword": "(required) keyword to search across business objects, activities, rules, metrics, etc."},
        "example": {"keyword": "采购清单"},
    },
    "sql_executor": {
        "params": {
            "sql": "(required) SELECT / WITH / EXPLAIN SQL query",
            "datasource_name": "(optional) datasource name, uses default SQLite if omitted",
        },
        "example": {"sql": "SELECT * FROM material LIMIT 5"},
    },
    "query_metadata": {
        "params": {
            "table_names": "(optional) list of table names for batch query",
            "table_name": "(optional) single table name or datasource.table",
            "keyword": "(optional) search keyword; empty string returns all tables",
        },
        "example": {"table_names": ["material", "qc_order", "receipt_record"]},
    },
    "read_file": {
        "params": {"key": "(required) file path/key in object storage"},
        "example": {"key": ""},
    },
    "list_files": {
        "params": {"prefix": "(optional) directory prefix to list"},
        "example": {"prefix": ""},
    },
}


@router.get("")
async def list_tools():
    """List all testable tools and their parameter schemas."""
    return {
        "tools": list(TOOL_DESCRIPTIONS.keys()),
        "descriptions": TOOL_DESCRIPTIONS,
        "usage": "POST /api/tools/test/{tool_name} with JSON body containing the tool params",
    }


@router.post("/{tool_name}")
async def test_tool(tool_name: str, request: Request):
    """Execute a tool with the given params and return the result."""
    if tool_name not in TOOL_DESCRIPTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown tool: {tool_name}. Available: {list(TOOL_DESCRIPTIONS.keys())}",
        )
    params: dict = await request.json()
    result = await execute_tool(tool_name, params)
    return {"tool": tool_name, "params": params, "result": result}
