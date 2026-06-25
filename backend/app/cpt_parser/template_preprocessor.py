"""FineReport 模板语法预处理：将 ${if()}/${var} 转为 sqlglot 可解析的 SQL"""

from __future__ import annotations

import re
import logging

from app.cpt_parser.models import CPTParameter

logger = logging.getLogger(__name__)


def preprocess_sql(sql: str, parameters: list[CPTParameter] | None = None) -> str:
    """将 FineReport 模板语法预处理为可解析的 SQL

    核心策略：
    - ${if(len(x)=0, "", "and ...")} → 移除（参数为空时不加条件）
    - ${if(x='1', "inner join ...", "")} → 取 true 分支（参数有值时加条件）
    - ${if(cond, sql_fragment, "")} → 取 sql_fragment
    - ${if(cond, "", sql_fragment)} → 取空（false 分支是条件片段时不适用）
    - ${variable} → 替换为参数默认值
    """
    result = sql

    # Step 1: 处理 ARRAY JOIN（sqlglot 不识别此语法）
    result = _handle_array_join(result)

    # Step 2: 处理 ${if(...)} 表达式
    result = _resolve_if_expressions(result)

    # Step 3: 处理 ${variable} 替换
    param_map = {p.name: p.default_value or "" for p in (parameters or [])}
    result = _resolve_variables(result, param_map)

    # Step 4: 清理残留的模板标记和无效 SQL 片段
    result = _cleanup_residual(result)

    return result


# ── ARRAY JOIN ──────────────────────────────────────────


def _handle_array_join(sql: str) -> str:
    """将 ARRAY JOIN 替换为 sqlglot 可解析的形式"""
    sql = re.sub(
        r"\bARRAY\s+JOIN\b",
        "/* ARRAY_JOIN */ CROSS JOIN",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


# ── ${if(...)} 解析 ────────────────────────────────────


_IF_PATTERN = re.compile(r"\$\{if\s*\(", re.IGNORECASE)


def _resolve_if_expressions(sql: str) -> str:
    """解析 ${if(condition, true_expr, false_expr)} 模板语法

    策略：
    - 分析 condition 来决定取哪个分支
    - len(x)=0 类条件：参数为空，取 true_expr（通常是空字符串）
    - x='value' 类条件：根据参数默认值决定
    - 无法判断时：取能产生合法 SQL 的分支（优先取空字符串分支）
    """
    max_iterations = 200
    for _ in range(max_iterations):
        match = _IF_PATTERN.search(sql)
        if not match:
            break

        start = match.start()
        brace_start = sql.index("{", start)
        brace_end = _find_closing_brace(sql, brace_start)
        if brace_end < 0:
            sql = sql[:start] + " " + sql[start + 6 :]
            continue

        paren_start = sql.index("(", start)
        args = _split_if_args(sql, paren_start)

        if args and len(args) >= 3:
            condition = args[0].strip()
            true_expr = args[1].strip()
            false_expr = args[2].strip()

            resolved = _resolve_if_condition(condition, true_expr, false_expr)
            sql = sql[:start] + resolved + sql[brace_end + 1 :]
        elif args and len(args) == 2:
            # ${if(cond, expr)} - 只有条件和一个表达式
            condition = args[0].strip()
            true_expr = args[1].strip()
            resolved = _resolve_if_condition(condition, true_expr, "")
            sql = sql[:start] + resolved + sql[brace_end + 1 :]
        else:
            sql = sql[:start] + " " + sql[brace_end + 1 :]

    return sql


def _resolve_if_condition(condition: str, true_expr: str, false_expr: str) -> str:
    """根据条件决定取哪个分支

    FineReport 模板中常见的条件模式：
    1. len(ewm) = 0 → 参数为空，取 true_expr（通常是空字符串，表示不加条件）
    2. drfs = '1' → 参数等于某值，取 true_expr（通常是 SQL 片段）
    3. and(len(x)=0, len(y)=0, ...) → 多条件组合
    """
    # 处理字符串拼接
    true_resolved = _resolve_string_concat(true_expr)
    false_resolved = _resolve_string_concat(false_expr)

    # 判断条件类型
    # 支持: len(x)=0, len(x)==0, LEN(x)=0, (len(x)=0), len(x)=='', len(x)==""
    is_empty_check = bool(re.match(
        r"\(?\s*len\s*\(\s*\w+\s*\)\s*[=]{1,2}\s*[0\"']",
        condition, re.IGNORECASE,
    ))
    is_and_empty = bool(re.match(r"\s*and\s*\(", condition, re.IGNORECASE))
    # 支持: x='val', x="val", x=='val'
    is_value_check = bool(re.match(r"\s*\w+\s*[=!]=\s*['\"]", condition, re.IGNORECASE))

    if is_empty_check:
        # len(x)=0 → 参数为空，取 true_expr（通常为空字符串，不加条件）
        return true_resolved
    elif is_and_empty:
        # and(len(x)=0, len(y)=0, ...) → 多个空检查，取 true_expr
        return true_resolved
    elif is_value_check:
        # x='value' → 参数有值，取 true_expr（通常是 SQL 片段如 inner join）
        return true_resolved
    else:
        # 无法判断，优先取空字符串分支（产生更干净的 SQL）
        if not true_resolved.strip() or true_resolved.strip() == '""':
            return ""
        if not false_resolved.strip() or false_resolved.strip() == '""':
            return ""
        # 两个分支都有内容，取 true_expr
        return true_resolved


def _split_if_args(sql: str, paren_start: int) -> list[str] | None:
    """在 ${if(condition, true_val, false_val)} 中按逗号分割参数

    需要处理嵌套括号和引号内的逗号
    """
    depth = 0
    args: list[str] = []
    current: list[str] = []
    in_string = False
    string_char: str | None = None
    i = paren_start + 1  # 跳过 '('

    while i < len(sql):
        ch = sql[i]

        if in_string:
            current.append(ch)
            if ch == string_char:
                # 检查是否是转义引号
                if i + 1 < len(sql) and sql[i + 1] == string_char:
                    current.append(sql[i + 1])
                    i += 2
                    continue
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            if depth == 0:
                args.append("".join(current))
                return args
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current))
            current = []
        else:
            current.append(ch)

        i += 1

    return None


def _find_closing_brace(sql: str, brace_start: int) -> int:
    """找到与 ${ 对应的 } 位置"""
    depth = 0
    in_string = False
    string_char: str | None = None
    i = brace_start
    while i < len(sql):
        ch = sql[i]
        if in_string:
            if ch == string_char:
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _resolve_string_concat(expr: str) -> str:
    """处理 FineReport 字符串拼接: "str1" + var + "str2" → 拼接结果"""
    # 如果不包含 + 拼接，直接返回
    if "+" not in expr:
        # 处理 FineReport 双引号字符串
        if expr.startswith('"') and expr.endswith('"') and expr.count('"') == 2:
            return expr[1:-1]  # 去掉双引号，返回内容
        return expr

    parts = re.split(r"\s*\+\s*", expr)
    if len(parts) <= 1:
        return expr

    result_parts: list[str] = []
    for part in parts:
        part = part.strip()
        if part.startswith('"') and part.endswith('"'):
            # FineReport 双引号字符串 → 直接内容
            result_parts.append(part[1:-1])
        elif part.startswith("'") and part.endswith("'"):
            # SQL 单引号字符串 → 保留
            result_parts.append(part)
        else:
            # 变量名 → 用占位符
            result_parts.append(f"__{part}__")

    return "".join(result_parts)


# ── ${variable} 替换 ───────────────────────────────────


def _resolve_variables(sql: str, param_map: dict[str, str]) -> str:
    """替换 ${variable_name} 为参数默认值

    未找到默认值的变量替换为 NULL，避免产生 'WHERE col = ' 这类无效 SQL。
    例如: WHERE col = ${x} → WHERE col = NULL
    """
    pattern = re.compile(r"\$\{(\w+)\}")

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in param_map:
            val = param_map[var_name]
            return val if val else "NULL"
        return "NULL"

    return pattern.sub(replacer, sql)


# ── 清理 ────────────────────────────────────────────────


def _strip_sql_comments(sql: str) -> str:
    """移除 SQL 中的注释（-- 和 /* */）

    sqlglot 无法正确处理 CTE 括号内的 -- 注释，
    会将 ) 也视为注释的一部分导致解析失败。
    """
    result: list[str] = []
    i = 0
    in_string = False
    string_char: str | None = None

    while i < len(sql):
        ch = sql[i]

        if in_string:
            result.append(ch)
            if ch == string_char:
                if i + 1 < len(sql) and sql[i + 1] == string_char:
                    result.append(sql[i + 1])
                    i += 2
                    continue
                in_string = False
            i += 1
            continue

        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
        elif ch == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
            # -- 单行注释：跳到行尾
            while i < len(sql) and sql[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
            # /* */ 块注释：跳到 */
            i += 2
            while i < len(sql) - 1:
                if sql[i] == "*" and sql[i + 1] == "/":
                    i += 2
                    break
                i += 1
            else:
                i = len(sql)
        else:
            result.append(ch)
            i += 1

    return "".join(result)


def _cleanup_residual(sql: str) -> str:
    """清理残留的模板标记和无效 SQL 片段"""
    # 移除 FineReport 双引号字符串残留（如 "inner join ..."）
    # 这些是模板拼接产生的 SQL 片段，需要去掉外层双引号
    # 但要小心不要误删 SQL 中的合法内容

    # 移除 SQL 注释（-- 和 /* */），sqlglot 无法正确处理 CTE 内的注释
    sql = _strip_sql_comments(sql)

    # 移除空的 AND/OR 条件
    sql = re.sub(r"\bAND\s+AND\b", "AND", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bOR\s+OR\b", "OR", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bWHERE\s+AND\b", "WHERE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bWHERE\s+OR\b", "WHERE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bWHERE\s+ORDER\b", "ORDER", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bWHERE\s+GROUP\b", "GROUP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bWHERE\s*$", "", sql, flags=re.IGNORECASE | re.MULTILINE)
    sql = re.sub(r"\bAND\s+ORDER\b", "ORDER", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bAND\s+GROUP\b", "GROUP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bAND\s+SETTINGS\b", "SETTINGS", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bAND\s*$", "", sql, flags=re.IGNORECASE | re.MULTILINE)
    sql = re.sub(r"\bOR\s*$", "", sql, flags=re.IGNORECASE | re.MULTILINE)
    sql = re.sub(r"\bGROUP\s+AND\b", "GROUP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bSETTINGS\s+AND\b", "SETTINGS", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bORDER\s+AND\b", "ORDER", sql, flags=re.IGNORECASE)

    # 清理 __var__ 占位符：将 dwd_kf__bi_dev__ 转为 dwd_kf_ 等合理形式
    # 如果占位符紧跟在 . 前面，说明是 schema 名的一部分，用空字符串替换
    sql = re.sub(r"__\w+__\.", ".", sql)
    # 其他位置的占位符也替换为空
    sql = re.sub(r"__\w+__", "", sql)

    # 移除连续空格
    sql = re.sub(r"\s+", " ", sql).strip()

    # 移除开头的空 AND/OR
    sql = re.sub(r"^\s*AND\s+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^\s*OR\s+", "", sql, flags=re.IGNORECASE)

    return sql
