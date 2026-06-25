"""基于 sqlglot 的 SQL 分析：提取表、列、JOIN、CTE、SETTINGS"""

from __future__ import annotations

import logging
import re
from typing import Any

import sqlglot
from sqlglot import exp

from app.cpt_parser.models import (
    CTEInfo,
    ColumnInfo,
    JoinInfo,
    SQLAnalysisResult,
    SubqueryAliasInfo,
    TableInfo,
)

logger = logging.getLogger(__name__)


def analyze_sql(sql: str, dataset_name: str = "") -> SQLAnalysisResult:
    """分析单条 SQL，提取表、列、JOIN、CTE、SETTINGS 信息"""
    result = SQLAnalysisResult(source_query=sql)

    # 预处理：替换 sqlglot 不支持的 ClickHouse 函数
    preprocessed = _preprocess_for_sqlglot(sql)

    try:
        ast = sqlglot.parse_one(preprocessed, dialect="clickhouse")
    except sqlglot.errors.ParseError as e:
        logger.warning("Failed to parse SQL for dataset '%s': %s", dataset_name, e)
        result.parse_errors.append(f"sqlglot parse error: {e}")
        # 降级策略：尝试逐段解析 CTE
        return _fallback_parse(sql, dataset_name, result)
    except Exception as e:
        logger.warning("Unexpected error parsing SQL for dataset '%s': %s", dataset_name, e)
        result.parse_errors.append(f"Unexpected parse error: {e}")
        return result

    result.tables = _extract_tables(ast)
    result.ctes = _extract_ctes(ast)
    result.columns = _extract_columns(ast)
    result.subquery_alias_map = _extract_subquery_alias_map(ast)
    result.joins = _extract_joins(ast, tables=result.tables, subquery_map=result.subquery_alias_map)
    result.settings = _extract_settings(ast)

    return result


# ── 预处理不兼容语法 ────────────────────────────────────


def _preprocess_for_sqlglot(sql: str) -> str:
    """替换 sqlglot 不支持的 ClickHouse 语法为可解析的形式"""
    result = sql

    # JSONExtractArrayRaw → JSONExtractString（占位，仅用于解析）
    result = re.sub(
        r"\bJSONExtractArrayRaw\b",
        "JSONExtractString",
        result,
        flags=re.IGNORECASE,
    )

    # 处理 row_number(col) OVER → row_number() OVER（sqlglot 不支持带参数的 row_number）
    # 使用括号匹配而非简单正则，正确处理嵌套括号的情况
    row_num_pattern = re.compile(r"\brow_number\s*\(", re.IGNORECASE)
    while True:
        rm = row_num_pattern.search(result)
        if not rm:
            break
        paren_start = rm.end() - 1
        paren_end = _find_matching_paren(result, paren_start)
        if paren_end < 0:
            break
        # 检查 ) 之后是否是 OVER
        rest = result[paren_end + 1:].lstrip()
        if rest.upper().startswith("OVER"):
            new_result = result[:rm.start()] + "row_number() OVER" + rest[4:]
            if new_result == result:
                break
            result = new_result
        else:
            break

    # 处理 '[]A' 这种 ClickHouse 特有的空数组占位符
    result = result.replace("'[]A'", "'[]'")
    result = result.replace('{"data":[]}', "'[]'")

    # arrayMap(x -> expr, arr) → 替换为简单的函数调用占位
    # sqlglot 不支持 lambda 语法
    result = re.sub(
        r"\barrayMap\s*\(",
        "arrayMap_simple(",
        result,
        flags=re.IGNORECASE,
    )

    # arrayStringConcat(...) → 简化为字符串函数
    result = re.sub(
        r"\barrayStringConcat\s*\(",
        "arrayStringConcat_simple(",
        result,
        flags=re.IGNORECASE,
    )

    # splitByChar(...) → 简化
    result = re.sub(
        r"\bsplitByChar\s*\(",
        "splitByChar_simple(",
        result,
        flags=re.IGNORECASE,
    )

    # COALESCE(...) 中的 ClickHouse 特有用法通常可以解析，保留

    # 处理 and(...) / or(...) 函数调用（ClickHouse 特有）
    # and(cond1, cond2) → cond1 AND cond2
    result = _convert_clickhouse_logical(result)

    return result


def _convert_clickhouse_logical(sql: str) -> str:
    """将 ClickHouse 的 and(...)/or(...) 函数调用转为标准 SQL 的 AND/OR

    ClickHouse 支持 and(cond1, cond2) 语法，sqlglot 不识别。
    转换策略：and(a, b) → (a AND b)，or(a, b) → (a OR b)
    """
    for func_name, op in [("and", "AND"), ("or", "OR")]:
        pattern = re.compile(rf"\b{func_name}\s*\(", re.IGNORECASE)
        while True:
            match = pattern.search(sql)
            if not match:
                break
            # 找到函数参数
            paren_start = match.end() - 1
            paren_end = _find_matching_paren(sql, paren_start)
            if paren_end < 0:
                break

            inner = sql[paren_start + 1 : paren_end]
            # 按顶层逗号分割
            args = _split_top_level(inner, ",")
            if len(args) >= 2:
                replacement = f"({f' {op} '.join(args)})"
            else:
                replacement = inner

            sql = sql[: match.start()] + replacement + sql[paren_end + 1 :]

    return sql


def _split_top_level(s: str, delimiter: str) -> list[str]:
    """按顶层分隔符分割字符串（忽略括号和引号内的）"""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    string_char: str | None = None

    for ch in s:
        if in_string:
            current.append(ch)
            if ch == string_char:
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == delimiter and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        parts.append("".join(current).strip())

    return parts


# ── 提取表 ──────────────────────────────────────────────


def _extract_tables(ast: exp.Expression) -> list[TableInfo]:
    """提取所有引用的表，包括子查询内部的表，去重

    去重策略：同一张表（name+schema）只保留一条，优先保留有别名的条目。
    子查询内部的表也会被收集。
    """
    tables: list[TableInfo] = []
    # 以 (name, schema) 为 key 去重
    seen: dict[tuple[str, str | None], TableInfo] = {}

    for table in ast.find_all(exp.Table):
        if not table.name:
            continue
        key = (table.name, table.db or None)
        alias = table.alias or None
        if key in seen:
            # 已存在，如果当前有条目有别名而之前没有，更新
            existing = seen[key]
            if not existing.alias and alias:
                existing.alias = alias
            continue
        info = TableInfo(
            name=table.name,
            alias=alias,
            schema=table.db or None,
        )
        seen[key] = info
        tables.append(info)

    # 补充子查询别名作为额外条目（同一张表可能有多个不同别名）
    for subquery in ast.find_all(exp.Subquery):
        alias = subquery.alias
        if not alias:
            continue
        for inner_table in subquery.find_all(exp.Table):
            if not inner_table.name:
                continue
            key = (inner_table.name, inner_table.db or None)
            if key not in seen:
                info = TableInfo(
                    name=inner_table.name,
                    alias=inner_table.alias or None,
                    schema=inner_table.db or None,
                )
                seen[key] = info
                tables.append(info)
            else:
                # 已存在，如果当前有条目有别名而之前没有，更新
                existing = seen[key]
                if not existing.alias and inner_table.alias:
                    existing.alias = inner_table.alias

    return tables


def _extract_subquery_alias_map(ast: exp.Expression) -> list[SubqueryAliasInfo]:
    """提取子查询别名映射：别名 → 子查询内部引用的所有表

    例如：(SELECT ... FROM dim.td_mm_lfa1 WHERE ...) AS lfa1
    → SubqueryAliasInfo(alias="lfa1", tables=[TableInfo(name="td_mm_lfa1", schema="dim")])
    """
    result: list[SubqueryAliasInfo] = []

    for subquery in ast.find_all(exp.Subquery):
        alias = subquery.alias
        if not alias:
            continue

        inner_tables: list[TableInfo] = []
        seen: set[tuple[str, str | None]] = set()
        for table in subquery.find_all(exp.Table):
            if not table.name:
                continue
            key = (table.name, table.db or None)
            if key in seen:
                continue
            seen.add(key)
            inner_tables.append(TableInfo(
                name=table.name,
                alias=table.alias or None,
                schema=table.db or None,
            ))

        if inner_tables:
            result.append(SubqueryAliasInfo(
                alias=alias,
                tables=inner_tables,
            ))

    return result


# ── 提取 CTE ────────────────────────────────────────────


def _extract_ctes(ast: exp.Expression) -> list[CTEInfo]:
    """提取 WITH 子句中的 CTE 定义"""
    ctes: list[CTEInfo] = []

    with_node = ast.find(exp.With)
    if with_node is None:
        return ctes

    for cte_expr in with_node.expressions:
        if isinstance(cte_expr, exp.CTE):
            cte_name = cte_expr.alias_or_name
            cte_sql = cte_expr.sql(dialect="clickhouse")

            cte_tables = _extract_tables(cte_expr)
            cte_columns = _extract_columns_from_cte(cte_expr)
            cte_subquery_aliases = _extract_subquery_alias_map(cte_expr.this)
            cte_joins = _extract_joins(
                cte_expr.this,
                tables=cte_tables,
                subquery_map=cte_subquery_aliases,
            )

            ctes.append(CTEInfo(
                name=cte_name,
                sql=cte_sql,
                tables=cte_tables,
                columns=cte_columns,
                joins=cte_joins,
            ))

    return ctes


def _extract_columns_from_cte(cte_expr: exp.CTE) -> list[ColumnInfo]:
    """从 CTE 表达式中提取输出列"""
    inner = cte_expr.this
    columns: list[ColumnInfo] = []

    select_node = inner.find(exp.Select) if inner else None
    if select_node is None:
        return columns

    for expr in select_node.args.get("expressions", []):
        columns.append(ColumnInfo(
            name=expr.alias or expr.name,
            expression=expr.sql(dialect="clickhouse"),
            type=type(expr).__name__,
        ))

    return columns


# ── 提取列 ──────────────────────────────────────────────


def _extract_columns(ast: exp.Expression) -> list[ColumnInfo]:
    """提取顶层 SELECT 的列"""
    columns: list[ColumnInfo] = []
    select_node = ast.find(exp.Select)
    if select_node is None:
        return columns

    for expr in select_node.args.get("expressions", []):
        info = ColumnInfo(
            name=expr.alias or expr.name,
            expression=expr.sql(dialect="clickhouse"),
            type=type(expr).__name__,
        )

        if isinstance(expr, exp.Column):
            info.table_alias = expr.table or None

        columns.append(info)

    return columns


# ── 提取 JOIN ────────────────────────────────────────────


def _extract_joins(
    ast: exp.Expression,
    tables: list[TableInfo] | None = None,
    subquery_map: list[SubqueryAliasInfo] | None = None,
) -> list[JoinInfo]:
    """提取 JOIN 关系，包含别名到真实表名的映射"""
    joins: list[JoinInfo] = []

    # 构建别名 → 真实表名的映射（优先用子查询映射）
    alias_to_name: dict[str, str] = {}
    if subquery_map:
        for sq in subquery_map:
            if sq.tables and len(sq.tables) == 1:
                # 仅单表子查询可映射到真实表名
                alias_to_name[sq.alias] = sq.tables[0].name
            # 多表子查询跳过：不存在单一的"真实"表
    if tables:
        for t in tables:
            if t.alias and t.alias not in alias_to_name:
                alias_to_name[t.alias] = t.name

    for join_node in ast.find_all(exp.Join):
        right_table = join_node.this
        right_name = right_table.name if hasattr(right_table, "name") else str(right_table)
        right_alias = right_table.alias if hasattr(right_table, "alias") else None

        # 确定 JOIN 类型
        join_type = "JOIN"
        side = join_node.args.get("side")
        kind = join_node.args.get("kind")
        if side == "LEFT":
            join_type = "LEFT JOIN"
        elif side == "RIGHT":
            join_type = "RIGHT JOIN"
        elif kind == "INNER":
            join_type = "INNER JOIN"
        elif kind == "CROSS":
            join_type = "CROSS JOIN"

        # 获取 ON 条件
        condition = None
        on_clause = join_node.args.get("on")
        if on_clause:
            condition = on_clause.sql(dialect="clickhouse")

        # 尝试确定左表
        left_alias = _find_left_table_for_join(join_node)
        right_alias_str = right_alias or right_name

        # 解析别名到真实表名（如果映射中找不到，就用别名本身）
        left_real = alias_to_name.get(left_alias, left_alias)
        right_real = alias_to_name.get(right_alias_str, right_alias_str)

        joins.append(JoinInfo(
            left_table=left_alias,
            right_table=right_alias_str,
            join_type=join_type,
            condition=condition,
            left_table_name=left_real,
            right_table_name=right_real,
        ))

    return joins


def _find_left_table_for_join(join_node: exp.Join) -> str:
    """尝试找到 JOIN 的左表名称

    策略：
    1. 查找同级的上一个 JOIN 或 FROM 子句作为左表
    2. 向上查找父级 Select 的 FROM
    """
    # 策略1：查找同级的前一个表源
    parent = join_node.parent
    if isinstance(parent, exp.Select):
        # FROM 子句中的表（sqlglot 用 from_ 键存储）
        from_clause = parent.args.get("from_") or parent.args.get("from")
        if from_clause:
            table = from_clause.this
            left_name = _get_table_name(table)
            if left_name:
                return left_name

        # 检查 joins 列表，找到当前 JOIN 之前的表
        joins = parent.args.get("joins") or []
        for i, j in enumerate(joins):
            if j is join_node:
                # 当前 JOIN 之前的那个 JOIN 或 FROM 就是左表
                if i > 0:
                    prev_join = joins[i - 1]
                    prev_table = prev_join.this
                    prev_alias = prev_table.alias if hasattr(prev_table, "alias") else None
                    if prev_alias:
                        return prev_alias
                    return prev_table.name if hasattr(prev_table, "name") else str(prev_table)
                else:
                    # 第一个 JOIN，左表就是 FROM 子句的表
                    if from_clause:
                        table = from_clause.this
                        return _get_table_name(table) or "__unknown__"

    # 策略2：向上查找父级 Select
    p = join_node.parent
    while p:
        if isinstance(p, exp.Select):
            from_clause = p.args.get("from_") or p.args.get("from")
            if from_clause:
                table = from_clause.this
                name = _get_table_name(table)
                if name:
                    return name
            break
        p = p.parent

    return "__unknown__"


def _get_table_name(table: exp.Expression) -> str | None:
    """从表表达式中提取名称（优先用别名）"""
    if table is None:
        return None
    if hasattr(table, "alias") and table.alias:
        return table.alias
    if hasattr(table, "name") and table.name:
        return table.name
    return None


# ── 提取 SETTINGS ──────────────────────────────────────


def _extract_settings(ast: exp.Expression) -> dict[str, Any]:
    """提取 ClickHouse SETTINGS"""
    settings: dict[str, Any] = {}

    settings_node = getattr(ast, "args", {}).get("settings")
    if settings_node:
        for setting in settings_node:
            if isinstance(setting, exp.EQ):
                key = setting.left.name if hasattr(setting.left, "name") else str(setting.left)
                value = getattr(setting.right, "this", None) or str(setting.right)
                settings[key] = value

    return settings


# ── 降级解析策略 ────────────────────────────────────────


def _fallback_parse(
    sql: str, dataset_name: str, result: SQLAnalysisResult
) -> SQLAnalysisResult:
    """当完整 SQL 无法解析时，尝试逐段解析 CTE"""
    result.parse_errors.append(
        f"Full SQL parse failed for dataset '{dataset_name}', attempting CTE-level parsing"
    )

    # 尝试按 CTE 名称提取并逐个解析
    cte_pattern = re.compile(r"(\w+)\s+as\s*\(", re.IGNORECASE)
    # CTE keyword phrases that could be confused with subquery aliases
    _from_join_pattern = re.compile(
        r"(\bfrom\b|\bjoin\b|\bcross\s+join\b|\bleft\b|\bright\b|\binner\b)\s+$",
        re.IGNORECASE,
    )
    for match in cte_pattern.finditer(sql):
        cte_name = match.group(1)
        # 跳过可能是 FROM/JOIN 别名的匹配（非 CTE）
        preceding = sql[:match.start()].strip()
        if preceding and _from_join_pattern.search(preceding):
            continue
        # 从 ( 开始找到匹配的 )
        paren_start = match.end() - 1  # ( 的位置
        paren_end = _find_matching_paren(sql, paren_start)
        if paren_end < 0:
            continue

        # 只取括号内的 SQL（不含 CTE 名和 AS），并应用 ClickHouse 预处理
        inner_sql = _preprocess_for_sqlglot(sql[paren_start : paren_end + 1])
        try:
            cte_ast = sqlglot.parse_one(
                f"WITH {cte_name} AS {inner_sql} SELECT 1",
                dialect="clickhouse",
            )
            cte_tables = _extract_tables(cte_ast)
            cte_columns = _extract_columns_from_cte(
                cte_ast.find(exp.CTE)  # type: ignore[arg-type]
            )
            result.ctes.append(CTEInfo(
                name=cte_name,
                sql=inner_sql,
                tables=cte_tables,
                columns=cte_columns,
            ))
        except Exception as e:
            result.parse_errors.append(f"CTE '{cte_name}' parse failed: {e}")

    return result


def _find_matching_paren(sql: str, start: int) -> int:
    """找到与 ( 匹配的 ) 位置"""
    depth = 0
    i = start
    in_string = False
    string_char: str | None = None

    while i < len(sql):
        ch = sql[i]
        if in_string:
            if ch == string_char:
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return -1
