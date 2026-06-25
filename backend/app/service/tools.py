from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Coroutine

from sqlalchemy import text

from app.db.session import async_session_factory
from app.service.datasource_resolver import get_current_tenant_id, resolve_active_datasource

logger = logging.getLogger(__name__)

# ── Tool type & registry ────────────────────────────────────

ToolFn = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]

_TOOL_REGISTRY: dict[str, dict] = {}  # name -> {"fn": ToolFn, "schema": dict}


def register_tool(name: str, schema: dict, fn: ToolFn) -> None:
    _TOOL_REGISTRY[name] = {"fn": fn, "schema": schema}


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for all registered tools."""
    schemas = []
    for name, info in _TOOL_REGISTRY.items():
        s = info["schema"]
        required = [k for k, v in s.get("parameters", {}).items() if v.get("required", True)]
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": s["description"],
                "parameters": {
                    "type": "object",
                    "properties": {k: {"type": v["type"], "description": v.get("description", "")} for k, v in s.get("parameters", {}).items()},
                    "required": required,
                },
            },
        })
    return schemas


async def execute_tool(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool by name and return the result dict."""
    if name not in _TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    fn = _TOOL_REGISTRY[name]["fn"]
    logger.debug("Tool call: %s, params: %s", name, {k: v for k, v in params.items()})
    try:
        t0 = datetime.now(timezone.utc)
        result = await fn(params)
        elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
        logger.debug("Tool finished: %s, elapsed_ms=%d, result keys: %s", name, elapsed_ms, list(result.keys()) if isinstance(result, dict) else "non-dict")
        return result
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {e}"
        logger.error("Tool failed: %s, error: %s\n%s", name, error_detail, traceback.format_exc())
        return {"error": f"[{name}] {error_detail}"}


# ── Tool implementations ────────────────────────────────────

async def _tool_execute_sql(params: dict) -> dict:
    """Execute a read-only SQL query against the user's active datasource."""
    query = params.get("query") or params.get("sql", "")
    query = str(query).strip()
    if not query:
        return {"error": "No SQL query provided"}

    query_upper = query.upper()
    starts_read = (
        query_upper.startswith("SELECT")
        or query_upper.startswith("WITH")
        or query_upper.startswith("EXPLAIN")
    )
    if not starts_read:
        return {"error": "Only SELECT, WITH (CTE), and EXPLAIN queries are allowed for safety"}

    # Enforce a row limit on SELECT queries
    limited_query = query
    if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
        limited_query = query.rstrip(";").strip() + " LIMIT 1000"
    elif query_upper.startswith("SELECT") and "LIMIT" in query_upper:
        limit_match = re.search(r"LIMIT\s+(\d+)", query_upper)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > 1000:
                limited_query = re.sub(r"LIMIT\s+\d+", "LIMIT 1000", query, flags=re.IGNORECASE)

    # Resolve the user's active datasource
    ds = await resolve_active_datasource()
    if ds is None:
        return {"error": "No datasource configured"}

    logger.debug("Executing SQL on datasource: %s (%s)", ds["name"], ds["db_type"])

    async with async_session_factory() as session:
        try:
            result = await session.execute(text(limited_query))
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys()) if result.keys() else []
                result_rows = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        if val is not None and hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        elif isinstance(val, Decimal):
                            val = float(val)
                        row_dict[col] = val
                    result_rows.append(row_dict)
                return {
                    "columns": columns,
                    "rows": result_rows,
                    "row_count": len(result_rows),
                    "datasource": ds["name"],
                }
            else:
                return {"rows": [], "row_count": 0, "columns": []}
        except Exception as e:
            return {"error": f"Query failed: {e}"}


async def _tool_list_tables(_params: dict) -> dict:
    """List all available tables from the PostgreSQL application database."""
    from app.service.datasource import list_tables

    tables = await list_tables()
    return {
        "tables": [f"{t.datasource_name}.{t.table_name}" for t in tables],
    }


async def _tool_get_table_schema(params: dict) -> dict:
    """Get column definitions for a specific table."""
    from app.service.datasource import get_columns

    table_ref = params.get("table_ref", "")
    if "." not in table_ref:
        return {"error": "table_ref must be in format 'datasource_name.table_name' or just 'table_name'"}

    ds_name, tbl_name = table_ref.split(".", 1)
    try:
        cols = await get_columns(ds_name, tbl_name)
        return {
            "columns": [{"name": c.name, "type": c.type, "comment": c.comment} for c in cols],
        }
    except Exception as e:
        return {"error": str(e)}


async def _tool_read_file(params: dict) -> dict:
    """Read file content from object storage."""
    from app.service.storage import read_file

    key = params.get("key", "")
    try:
        content = read_file(key)
        return {"key": key, "content": content}
    except Exception as e:
        return {"error": str(e)}


async def _tool_list_files(params: dict) -> dict:
    """List files/directories in object storage."""
    from app.service.storage import list_files

    prefix = params.get("prefix", "")
    try:
        items = list_files(prefix)
        return {
            "items": [
                {"key": i.key, "size": i.size, "is_dir": i.is_dir}
                for i in items
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# ── Tools matching REACT_SYSTEM_PROMPT names ───────────────

async def _tool_sql_executor(params: dict) -> dict:
    """REACT_SYSTEM_PROMPT tool: execute verified SELECT SQL queries."""
    return await _tool_execute_sql({
        "query": params.get("sql", ""),
    })


def _to_dict(obj: Any) -> dict:
    """Convert an ORM object to a JSON-safe dict."""
    from datetime import date, datetime

    def _serialize(v):
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        return v

    if hasattr(obj, "__table__"):
        return {c.name: _serialize(getattr(obj, c.name)) for c in obj.__table__.columns}
    return obj if isinstance(obj, dict) else {"_raw": str(obj)}


async def _tool_ontology_query(params: dict) -> dict:
    """REACT_SYSTEM_PROMPT tool: query business context from ontology tables.

    Searches across business activities, objects, rules, metrics, data assets,
    and relationships by keyword. Accepts both string and list of strings.
    When matching business objects, also discovers the chain of activities that
    operate on them via the operated_objects field.
    """
    from app.ontology.database import (
        list_activities,
        list_objects,
        list_rules,
        list_metrics,
        list_data_assets,
        list_object_relationships,
        list_activity_entity_rels,
    )

    raw_keyword = params.get("keyword", "")
    if isinstance(raw_keyword, list):
        keywords = [str(k).strip().lower() for k in raw_keyword if k]
    else:
        keywords = [str(raw_keyword).strip().lower()]
    keywords = [k for k in keywords if k]
    if not keywords:
        return {"error": "keyword is required"}

    def _matches_any(text: str) -> bool:
        text_lower = text.lower()
        return any(k in text_lower for k in keywords)

    async with async_session_factory() as session:
        results: dict[str, list] = {}
        tenant_id = get_current_tenant_id()

        activities = [_to_dict(a) for a in await list_activities(session, tenant_id)]
        objects = [_to_dict(o) for o in await list_objects(session, tenant_id)]
        activity_map = {a.get("name", ""): a for a in activities}

        # ── Search activities ──
        matching_activities = []
        for a in activities:
            name_desc = (a.get("name", "") + (a.get("description", "") or ""))
            operated = a.get("operated_objects") or ""
            if _matches_any(name_desc) or _matches_any(operated):
                matching_activities.append(a)
        if matching_activities:
            results["activities"] = matching_activities

        # ── Search business objects ──
        matching_objects = [
            o for o in objects
            if _matches_any(o.get("name", "") + (o.get("description", "") or ""))
        ]
        if matching_objects:
            results["business_objects"] = matching_objects

        # ── Build object-based activity chain ──
        matched_object_names = {o.get("name", "").lower() for o in matching_objects}
        if matched_object_names:
            chain_activities: dict[int, dict] = {}
            for act in activities:
                operated = (act.get("operated_objects") or "").lower().split(",")
                operated = {o.strip() for o in operated if o.strip()}
                if operated & matched_object_names:
                    chain_activities[act["activity_id"]] = act

            expanded_ids = set(chain_activities.keys())
            for act in list(chain_activities.values()):
                for name in _parse_csv_names(act.get("pre_activities")):
                    parent = activity_map.get(name)
                    if parent and parent["activity_id"] not in expanded_ids:
                        chain_activities[parent["activity_id"]] = parent
                        expanded_ids.add(parent["activity_id"])
                for name in _parse_csv_names(act.get("post_activities")):
                    child = activity_map.get(name)
                    if child and child["activity_id"] not in expanded_ids:
                        chain_activities[child["activity_id"]] = child
                        expanded_ids.add(child["activity_id"])

            if chain_activities:
                results["object_activity_chain"] = [
                    {
                        "activity_name": a.get("name"),
                        "activity_id": a.get("activity_id"),
                        "description": a.get("description"),
                        "operated_objects": a.get("operated_objects"),
                        "pre_activities": [
                            {"name": n, "activity_id": activity_map[n].get("activity_id") if n in activity_map else None}
                            for n in _parse_csv_names(a.get("pre_activities"))
                        ],
                        "post_activities": [
                            {"name": n, "activity_id": activity_map[n].get("activity_id") if n in activity_map else None}
                            for n in _parse_csv_names(a.get("post_activities"))
                        ],
                    }
                    for a in chain_activities.values()
                ]

        # ── Search rules ──
        rules = [_to_dict(r) for r in await list_rules(session, tenant_id)]
        matching_rules = [
            r for r in rules
            if _matches_any(r.get("name", "") + (r.get("description", "") or ""))
        ]
        if matching_rules:
            results["rules"] = matching_rules

        # ── Search metrics ──
        metrics = [_to_dict(m) for m in await list_metrics(session, tenant_id)]
        matching_metrics = [
            m for m in metrics
            if _matches_any(m.get("name", "") + (m.get("business_meaning", "") or ""))
        ]
        if matching_metrics:
            results["metrics"] = matching_metrics

        # ── Search data assets ──
        assets = [_to_dict(a) for a in await list_data_assets(session, tenant_id)]
        matching_assets = [
            a for a in assets
            if _matches_any(a.get("table_name", "") + (a.get("table_comment", "") or ""))
        ]
        if matching_assets:
            results["data_assets"] = matching_assets

        # ── Search object relationships ──
        relationships = [_to_dict(r) for r in await list_object_relationships(session, tenant_id)]
        matching_rels = [
            r for r in relationships
            if _matches_any(str(r.get("object_id_1", "")) + str(r.get("object_id_2", "")) + (r.get("relationship_type", "") or ""))
        ]
        if matching_rels:
            results["object_relationships"] = matching_rels

        # ── Search activity-entity relations ──
        entity_rels = [_to_dict(e) for e in await list_activity_entity_rels(session, tenant_id)]
        matching_entity_rels = [
            e for e in entity_rels
            if _matches_any(e.get("entity_name", "") + (e.get("entity_type", "") or ""))
        ]
        if matching_entity_rels:
            results["activity_entity_relationships"] = matching_entity_rels

    return {
        "keywords": keywords,
        "results": {k: v for k, v in results.items() if v},
        "total_matches": sum(len(v) for v in results.values()),
    }


def _parse_csv_names(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


async def _tool_query_metadata(params: dict) -> dict:
    """REACT_SYSTEM_PROMPT tool: retrieve data asset definitions, column types, or documentation.

    Supports multiple parameter modes:
    - {"table_names": ["orders", "users"]} → returns schemas for all listed tables
    - {"table_name": "orders"} → returns detailed column schema with comments
    - {"keyword": "customer"} → returns tables/columns matching the keyword
    - {"keyword": ""} → returns list of all tables with brief column summaries

    Set include_columns=true to return full column definitions for each table.
    By default only table name and description are returned.
    """
    include_columns = params.get("include_columns", False)
    if isinstance(include_columns, str):
        include_columns = include_columns.lower() in ("true", "1", "yes")

    logger.debug("_tool_query_metadata params: %s", {k: type(v).__name__ for k, v in params.items()})

    # Mode 1: table_names list
    table_names = params.get("table_names")
    if isinstance(table_names, list) and len(table_names) > 0:
        return await _query_multiple_tables(table_names, include_columns)

    # Mode 2: single table
    table_name = params.get("table_name") or params.get("asset_name")
    keyword_param = params.get("keyword", "")
    if isinstance(keyword_param, list):
        keyword_param = keyword_param[0] if keyword_param else ""
    table_name = table_name or str(keyword_param).strip()
    if not table_name:
        return await _build_table_list(include_columns)

    if not params.get("table_name") and not params.get("asset_name"):
        keyword = str(keyword_param).strip().lower()
        if keyword:
            return await _search_tables_by_keyword(keyword, include_columns)

    return await _query_single_table(table_name, include_columns)


async def _query_single_table(table_name: str, include_columns: bool = False) -> dict:
    """Query schema and comments for a single table in PostgreSQL.

    When include_columns is False (default), returns only table_name + table_comment.
    When True, also includes full column definitions.
    """
    from app.ontology.database import list_data_assets
    tenant_id = get_current_tenant_id()

    result: dict[str, Any] = {"table_name": table_name}

    # Get comment from ontology data assets
    async with async_session_factory() as session:
        assets = [_to_dict(a) for a in await list_data_assets(session, tenant_id)]
        for a in assets:
            if table_name.lower() == a.get("table_name", "").lower():
                result["table_comment"] = a.get("table_comment")
                break

    if include_columns:
        try:
            from app.service.datasource import _get_postgres_columns_dsn
            from app.service.datasource_resolver import resolve_active_datasource
            ds = await resolve_active_datasource()
            cols = await _get_postgres_columns_dsn(ds["dsn"], table_name) if ds else []
            result["columns"] = [
                {"name": c.name, "type": c.type, "comment": c.comment}
                for c in cols
            ]
        except Exception as e:
            result["schema_error"] = str(e)

    return result


async def _query_multiple_tables(table_names: list[str], include_columns: bool = False) -> dict:
    """Query schemas and comments for multiple tables at once."""
    tables = []
    errors = []

    for name in table_names:
        if not isinstance(name, str) or not name.strip():
            continue
        result = await _query_single_table(name.strip(), include_columns)
        if "schema_error" in result:
            errors.append({"table_name": name, "error": result["schema_error"]})
        else:
            tables.append(result)

    response = {"tables": tables}
    if errors:
        response["errors"] = errors
    return response


async def _build_table_list(include_columns: bool = False) -> dict:
    """Build a list of all tables from PostgreSQL.

    When include_columns is False (default), returns only table_name + table_comment.
    When True, also includes column definitions for each table.
    """
    from app.ontology.database import list_data_assets
    from app.service.datasource import list_tables
    tenant_id = get_current_tenant_id()

    tables = await list_tables()

    # Load comments from ontology
    async with async_session_factory() as session:
        assets = [_to_dict(a) for a in await list_data_assets(session, tenant_id)]
        comment_map = {a.get("table_name", "").lower(): a.get("table_comment") for a in assets}

    result: list[dict] = []
    for t in tables:
        entry: dict = {
            "table_name": t.table_name,
        }
        comment = comment_map.get(t.table_name.lower())
        if comment:
            entry["table_comment"] = comment

        if include_columns:
            try:
                from app.service.datasource import _get_postgres_default_columns
                cols = await _get_postgres_default_columns(t.table_name)
                entry["columns"] = [
                    {"name": c.name, "type": c.type, "comment": c.comment}
                    for c in cols
                ]
            except Exception:
                entry["columns"] = []

        result.append(entry)

    return {"tables": result}


async def _search_tables_by_keyword(keyword: str, include_columns: bool = False) -> dict:
    """Search for tables and columns matching a keyword in PostgreSQL.

    When include_columns is False (default), returns only table_name + table_comment.
    When True, also includes matched column definitions.
    """
    from app.ontology.database import list_data_assets
    from app.service.datasource import list_tables
    tenant_id = get_current_tenant_id()

    tables_data = await list_tables()

    async with async_session_factory() as session:
        assets = [_to_dict(a) for a in await list_data_assets(session, tenant_id)]
        comment_map = {a.get("table_name", "").lower(): a.get("table_comment") for a in assets}

    matched_tables: list[dict] = []

    for t in tables_data:
        table_match = keyword in t.table_name.lower()
        entry: dict = {"table_name": t.table_name}
        comment = comment_map.get(t.table_name.lower())
        if comment:
            entry["table_comment"] = comment

        if include_columns:
            try:
                from app.service.datasource import _get_postgres_default_columns
                cols = await _get_postgres_default_columns(t.table_name)
                matched_cols = [
                    {"name": c.name, "type": c.type, "comment": c.comment}
                    for c in cols
                    if keyword in c.name.lower() or (c.comment or "").lower().find(keyword) >= 0
                ]
                if table_match or matched_cols:
                    entry["columns"] = [{"name": c.name, "type": c.type, "comment": c.comment} for c in cols] if table_match else matched_cols
                    matched_tables.append(entry)
            except Exception:
                if table_match:
                    matched_tables.append(entry)
        else:
            if table_match:
                matched_tables.append(entry)

    return {"keyword": keyword, "tables": matched_tables, "total_matches": len(matched_tables)}


# ── Skill tools ───────────────────────────────────────

async def _tool_list_skills(params: dict) -> dict:
    """List available skills, optionally filtered by group."""
    from app.service.skills import skill_registry

    group = params.get("group")
    summaries = skill_registry.list_skill_summaries(group)

    groups = {}
    for s in skill_registry.list_groups():
        groups[s.name] = [sk.name for sk in s.skills]

    return {
        "skills": summaries,
        "groups": groups,
        "total": len(summaries),
    }


async def _tool_load_skill(params: dict) -> dict:
    """Load a skill's full instructions by name. Use this when the agent needs detailed guidance for a task.

    Returns the skill's instruction that the agent should follow step by step.
    Call this BEFORE executing the skill's workflow so you know exactly what to do.
    """
    from app.service.skills import skill_registry

    name = params.get("name", "")
    if not name:
        return {"error": "Skill name is required"}

    skill = skill_registry.get_skill(name)
    if skill is None:
        available = [s["name"] for s in skill_registry.list_skill_summaries()]
        return {
            "error": f"Skill not found: {name}",
            "available_skills": available,
        }

    return {
        "name": skill.name,
        "group": skill.group,
        "display_name": skill.display_name,
        "description": skill.description,
        "instruction": skill.instruction,
    }


# ════════════════════════════════════════════════════════════════════════════
# Time Range Resolution Tool
# ════════════════════════════════════════════════════════════════════════════

async def _tool_resolve_time(params: dict) -> dict:
    """Resolve a time keyword (extracted by LLM from user's question) to a date range.

    LLM extracts the time-related word/phrase, this tool computes the actual dates.
    Supports Chinese and English keywords.
    """
    from datetime import date, timedelta
    import re

    keyword = (
        str(params.get("expression", "") or
             params.get("time", "") or
             params.get("time_expression", "") or
             params.get("keyword", "") or
             params.get("time_range", ""))
    ).strip()
    if not keyword:
        return {"error": "No time keyword provided. Extract the time-related word from the user's question."}

    today = date.today()
    kw = keyword.lower()

    # ── Parse number-based patterns (e.g. "最近3个月", "近30天", "last 2 weeks") ──
    num_match = re.search(r'(\d+)\s*(天|日|周|星期|月|季度|年|days?|weeks?|months?|quarters?|years?)', kw)
    period_match = re.search(r'(近|最近|过去|最近过去|last|past|recent)\s*(\d+)\s*(天|日|周|星期|月|季度|年|days?|weeks?|months?|quarters?|years?)', kw)

    if period_match:
        n = int(period_match.group(2))
        unit = period_match.group(3)
        if unit in ('天', '日', 'day', 'days'):
            return _range(today - timedelta(days=n - 1), today, keyword)
        elif unit in ('周', '星期', 'week', 'weeks'):
            return _range(today - timedelta(weeks=n), today, keyword)
        elif unit in ('月', '月', 'month', 'months'):
            start = today - timedelta(days=n * 30)
            return _range(start, today, keyword)
        elif unit in ('季度', 'quarter', 'quarters'):
            start = today - timedelta(days=n * 90)
            return _range(start, today, keyword)
        elif unit in ('年', 'year', 'years'):
            start = today.replace(year=today.year - n, month=1, day=1)
            return _range(start, today, keyword)
    elif num_match:
        n = int(num_match.group(1))
        unit = num_match.group(2)
        if unit in ('天', '日', 'day', 'days'):
            return _range(today - timedelta(days=n - 1), today, keyword)

    # ── Relative day ──
    if any(w in kw for w in ('今天', '今日', 'today')):
        return _range(today, today, keyword)
    if any(w in kw for w in ('昨天', '昨日', 'yesterday')):
        return _range(today - timedelta(days=1), today - timedelta(days=1), keyword)
    if any(w in kw for w in ('前天',)):
        return _range(today - timedelta(days=2), today - timedelta(days=2), keyword)
    if any(w in kw for w in ('明天', '明日', 'tomorrow')):
        return _range(today + timedelta(days=1), today + timedelta(days=1), keyword)

    # ── Week patterns ──
    if any(w in kw for w in ('本周', '这周', 'this week', 'current week')):
        start = today - timedelta(days=today.weekday())
        return _range(start, start + timedelta(days=6), keyword)
    if any(w in kw for w in ('上周', '上星期', 'last week')):
        end = today - timedelta(days=today.weekday() + 1)
        return _range(end - timedelta(days=6), end, keyword)
    if any(w in kw for w in ('下周', '下星期', 'next week')):
        start = today + timedelta(days=7 - today.weekday())
        return _range(start, start + timedelta(days=6), keyword)

    # ── Month patterns ──
    if any(w in kw for w in ('本月', '这个月', 'this month', 'current month')):
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)
    if any(w in kw for w in ('上月', '上个月', '上个月', 'last month')):
        end = today.replace(day=1) - timedelta(days=1)
        return _range(end.replace(day=1), end, keyword)
    if any(w in kw for w in ('下月', '下个月', 'next month')):
        start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)

    # ── Quarter patterns ──
    if any(w in kw for w in ('本季度', '本季', 'this quarter', 'current quarter')):
        q = (today.month - 1) // 3
        start = today.replace(month=q * 3 + 1, day=1)
        end = (start + timedelta(days=92)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)
    if any(w in kw for w in ('上季度', '上季', 'last quarter')):
        q = (today.month - 1) // 3
        if q == 0:
            start = today.replace(year=today.year - 1, month=10, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start = today.replace(month=(q - 1) * 3 + 1, day=1)
            end = (start + timedelta(days=92)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)
    if any(w in kw for w in ('下季度', '下季', 'next quarter')):
        q = (today.month - 1) // 3
        if q == 3:
            start = today.replace(year=today.year + 1, month=1, day=1)
        else:
            start = today.replace(month=(q + 1) * 3 + 1, day=1)
        end = (start + timedelta(days=92)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)

    # ── Year patterns ──
    if any(w in kw for w in ('本年', '今年', 'this year', 'current year')):
        return _range(today.replace(month=1, day=1), today.replace(month=12, day=31), keyword)
    if any(w in kw for w in ('去年', '上一年', 'last year')):
        return _range(today.replace(year=today.year - 1, month=1, day=1),
                      today.replace(year=today.year - 1, month=12, day=31), keyword)
    if any(w in kw for w in ('明年', '下一年', 'next year')):
        return _range(today.replace(year=today.year + 1, month=1, day=1),
                      today.replace(year=today.year + 1, month=12, day=31), keyword)

    # ── Specific year/month ──
    ym_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})?\s*月?', kw)
    if ym_match:
        y, m = int(ym_match.group(1)), int(ym_match.group(2) or 1)
        start = date(y, m, 1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)

    # ── Quarter pattern: "2024Q1", "2024 Q1" ──
    q_match = re.search(r'(\d{4})\s*[Qq](\d)', kw)
    if q_match:
        y, q = int(q_match.group(1)), int(q_match.group(2))
        start = date(y, (q - 1) * 3 + 1, 1)
        end = (start + timedelta(days=92)).replace(day=1) - timedelta(days=1)
        return _range(start, end, keyword)

    return {
        "error": f"Could not parse time keyword: '{keyword}'. Try simpler forms like '本月','上周','Q1 2024','近30天'.",
    }


def _range(start, end, keyword):
    from datetime import date
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "keyword": keyword,
        "today": date.today().isoformat(),
        "sql_filter": f"date_column >= '{start.isoformat()}' AND date_column <= '{end.isoformat()}'",
        "python_date": f"date({start.year}, {start.month}, {start.day}) to date({end.year}, {end.month}, {end.day})",
    }


def register_builtin_tools() -> None:
    register_tool("sql_executor", {
        "description": """
- **Description**: Executes verified SELECT SQL queries and returns the dataset.
- **Input**: `{"sql": "SELECT ..."}`       
        """,
        "parameters": {
            "sql": {"type": "string", "description": "SQL SELECT / WITH / EXPLAIN query to execute", "required": False},
            "query": {"type": "string", "description": "Alternative name for the SQL query", "required": False},
        },
    }, _tool_execute_sql)

    register_tool("ontology_query_tool", {
        "description": """
- **Description**: Retrieves business processes, calculation rules, metric definitions, and relationship logic. Supports a single keyword (string) or multiple keywords (array). When an array is provided, returns results matching **any** keyword.
- **Input**:
  - Single keyword: `{"keyword": "active user"}`
  - Multiple keywords: `{"keyword": ["material", "quality traceability", "batch"]}`
- **Output format example**:

```
{
  "concept": "active user",
  "definition": "A user who has logged in at least once in the last 30 days",
  "calculation": "COUNT(DISTINCT user_id) WHERE last_login_date >= CURRENT_DATE - 30",
  "related_business_objects": ["user_sessions", "login_history"],
  "business_process": "User engagement tracking"
}
```
        """,
        "parameters": {
            "keyword": {"type": "string", "description": "Keyword to search for in ontology entities"},
        },
    }, _tool_ontology_query)

    register_tool("query_metadata", {
        "description": """
- **Description**: Unified schema exploration tool. Returns table/column definitions, data types, foreign keys, and business meaning of fields (if annotated) only when `include_columns` is `True`. When `include_columns` is `False` or omitted, returns only table names and their descriptions (no column-level details). Does NOT return business rules or KPIs.
- **Input modes**:
  - Discover all tables (fallback): `{"table_names": "", "include_columns": false}` → returns list of table names with table descriptions.
  - Search by keyword: `{"table_names": "customer", "include_columns": false}` → returns tables matching the keyword (with table descriptions, no columns).
  - Get detailed table schema for a single table: `{"table_name": "orders", "include_columns": true}` → returns complete column definitions including foreign keys for that table.
  - Get detailed table schemas for multiple tables (batch): `{"table_names": ["orders", "customers", "products"], "include_columns": true}` → returns schemas for all specified tables in one call, including full column details. Use this when you need column-level information for several known tables to improve efficiency.
- **Output format examples**:

  When `include_columns: false` (or omitted):

```json
{
"tables": [
{"table_name": "orders", "description": "订单表"},
{"table_name": "customers", "description": "客户表"}
]
}
```
 When `include_columns: true`:
 ```json
 {
"tables": [{
"table_name": "orders",
"description": "订单表",
"columns": [{"name": "order_id", "type": "int", "business_meaning": "订单ID"}],
"foreign_keys": [{"column": "user_id", "references": "users.id"}]
}]
}
 ```
        """,
        "parameters": {
            "table_names": {"type": "array", "items": {"type": "string"}, "description": "List of table names to query at once (e.g., ['material', 'qc_order'])", "required": False},
            "table_name": {"type": "string", "description": "Single table name", "required": False},
            "keyword": {"type": "string", "description": "Keyword to search for in table names or column names. Empty string returns all tables.", "required": False},
            "include_columns": {"type": "boolean", "description": "Set to true to return full column definitions (name, type, comment) for each table. When omitted or false, only table_name and table_comment are returned.", "required": False},
        },
    }, _tool_query_metadata)

    register_tool("read_file", {
        "description": "Read the content of a file from object storage",
        "parameters": {
            "key": {"type": "string", "description": "File path/key in object storage"},
        },
    }, _tool_read_file)

    register_tool("list_files", {
        "description": "List files and directories in object storage at a given prefix",
        "parameters": {
            "prefix": {"type": "string", "description": "Directory prefix to list (empty string for root)"},
        },
    }, _tool_list_files)

    register_tool("list_skills", {
        "description": "List available skills organized by group. Use to discover what capabilities are available before loading a specific skill. Optionally filter by group to reduce results.",
        "parameters": {
            "group": {"type": "string", "description": "Optional group name to filter skills (e.g., 'sql', 'ontology')", "required": False},
        },
    }, _tool_list_skills)

    register_tool("load_skill", {
        "description": "Load a skill's full instructions by name. Call this BEFORE executing a task to get detailed step-by-step guidance. The returned instruction must be followed precisely.",
        "parameters": {
            "name": {"type": "string", "description": "Name of the skill to load (e.g., 'sql_query', 'ontology_search')"},
        },
    }, _tool_load_skill)

    register_tool("resolve_time", {
        "description": """
**Description:** Resolves natural language time expressions (e.g., "this month", "last week") into concrete date ranges to populate the `time_range` field in the Problem Breakdown JSON.  
**Input:** `expression` (string, required) – the time phrase to resolve (e.g., `"this month"`, `"last quarter"`).  
**Output:**  
- Success: `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}` (inclusive).  
- Failure: `{"error": "Unrecognized time expression", "start": null, "end": null}`.  
**Examples:**  
- `resolve_time("this month")` → `{"start": "2026-06-01", "end": "2026-06-30"}`  
- `resolve_time("last quarter")` → `{"start": "2026-04-01", "end": "2026-06-30"}`  
**Usage:** Call during Step 0 only, before the Problem Breakdown JSON. For absolute dates, do not call; use the literal value directly.
        """,
        "parameters": {
            "expression": {"type": "string", "description": "Time expression in Chinese or English, e.g. '本月','本周','上个月','today','current month'"},
        },
    }, _tool_resolve_time)
