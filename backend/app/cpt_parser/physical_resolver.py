"""物理表关系解析：将 CTE 引用展开为底层物理表之间的 JOIN 关系"""

from __future__ import annotations

import logging
from itertools import product
from typing import TYPE_CHECKING

from app.cpt_parser.models import PhysicalJoinInfo, TableInfo

if TYPE_CHECKING:
    from app.cpt_parser.models import SQLAnalysisResult

logger = logging.getLogger(__name__)


def resolve_physical_relations(
    analysis: SQLAnalysisResult,
) -> tuple[list[TableInfo], list[PhysicalJoinInfo]]:
    """解析 SQL 分析结果，提取物理表及其 JOIN 关系

    将数据集中的所有 CTE 递归展开为底层物理表，
    并收集 CTE 内部及主查询中的所有物理表 JOIN 关系。

    Returns:
        (physical_tables, physical_joins)
    """
    # Step A: 构建 CTE 查询映射
    cte_map: dict[str, "CTEInfo"] = {}
    for cte in analysis.ctes:
        cte_map[cte.name] = cte

    # Step B: 递归计算每个 CTE 的底层物理表集合
    # leaf_map[cte_name] = {物理表名1, 物理表名2, ...}
    leaf_map: dict[str, set[str]] = {}
    for cte in analysis.ctes:
        leaf_map[cte.name] = _get_leaf_tables(cte.name, cte_map, set())

    physical_joins: list[PhysicalJoinInfo] = []

    # Step C: 收集 CTE 内部的 JOIN 关系
    _collect_cte_internal_joins(analysis.ctes, leaf_map, cte_map, physical_joins)

    # Step D: 解析主查询的 JOIN 关系到物理表
    _resolve_main_query_joins(
        analysis.joins, leaf_map, cte_map, analysis.tables, physical_joins
    )

    # Step E: 收集所有物理表（去重）
    physical_tables = _collect_physical_tables(
        analysis.tables, analysis.ctes, leaf_map, cte_map
    )

    return physical_tables, physical_joins


def _get_leaf_tables(
    name: str,
    cte_map: dict[str, "CTEInfo"],
    visited: set[str],
) -> set[str]:
    """递归获取 CTE 的底层物理表名集合

    如果 name 不在 CTE 映射中，则它本身就是物理表名。
    使用 visited 集合防止循环引用。
    """
    cte = cte_map.get(name)
    if cte is None:
        # 不是 CTE，直接返回物理表名
        return {name}

    if name in visited:
        # 循环引用，返回空集合
        logger.warning("Circular CTE reference detected for '%s'", name)
        return set()

    visited.add(name)
    leaf_tables: set[str] = set()
    for table_info in cte.tables:
        leaf_tables |= _get_leaf_tables(table_info.name, cte_map, visited)
    visited.remove(name)

    return leaf_tables


def _collect_cte_internal_joins(
    ctes: list["CTEInfo"],
    leaf_map: dict[str, set[str]],
    cte_map: dict[str, "CTEInfo"],
    physical_joins: list[PhysicalJoinInfo],
) -> None:
    """收集 CTE 内部的 JOIN 关系，并展开为物理表之间的 JOIN"""
    for cte in ctes:
        if not cte.joins:
            continue

        # 构建 CTE 内部的别名映射（CTE 内的别名 → 物理表名）
        alias_map = _build_alias_to_physical_map(cte.tables, leaf_map, cte_map)

        for join in cte.joins:
            left_physical = _resolve_to_physical_set(
                join.left_table_name or join.left_table, alias_map, cte.name, leaf_map
            )
            right_physical = _resolve_to_physical_set(
                join.right_table_name or join.right_table, alias_map, cte.name, leaf_map
            )
            for lp, rp in product(sorted(left_physical), sorted(right_physical)):
                _add_join_if_new(
                    physical_joins,
                    PhysicalJoinInfo(
                        left_table=lp,
                        right_table=rp,
                        join_type=join.join_type,
                        condition=join.condition,
                        source=cte.name,
                    ),
                )


def _resolve_main_query_joins(
    joins: list["JoinInfo"],
    leaf_map: dict[str, set[str]],
    cte_map: dict[str, "CTEInfo"],
    tables: list[TableInfo],
    physical_joins: list[PhysicalJoinInfo],
) -> None:
    """解析主查询的 JOIN 关系到物理表"""
    # 构建主查询的别名映射
    alias_map = _build_alias_to_physical_map(tables, leaf_map, cte_map)

    for join in joins:
        left_physical = _resolve_to_physical_set(
            join.left_table_name or join.left_table, alias_map, "main", leaf_map
        )
        right_physical = _resolve_to_physical_set(
            join.right_table_name or join.right_table, alias_map, "main", leaf_map
        )
        # 跳过自引用（CTE 内部引用自身的情况）
        if not left_physical or not right_physical:
            continue
        for lp, rp in product(sorted(left_physical), sorted(right_physical)):
            _add_join_if_new(
                physical_joins,
                PhysicalJoinInfo(
                    left_table=lp,
                    right_table=rp,
                    join_type=join.join_type,
                    condition=join.condition,
                    source="main",
                ),
            )


def _build_alias_to_physical_map(
    tables: list[TableInfo],
    leaf_map: dict[str, set[str]],
    cte_map: dict[str, "CTEInfo"],
) -> dict[str, set[str]]:
    """构建别名/表名到物理表名集合的映射

    对于有别名且指向单个物理表的条目，使用别名和原始表名都可查找到。
    对于不知道的别名，尝试通过 leaf_map 解析。
    """
    alias_map: dict[str, set[str]] = {}
    for table_info in tables:
        if table_info.name in leaf_map:
            # CTE 名称 → 展开为底层物理表集合
            tables_set = leaf_map[table_info.name]
        else:
            # 纯物理表
            tables_set = {table_info.name}

        # 使用表名本身作为 key
        alias_map[table_info.name] = tables_set
        # 使用别名作为 key（如果有）
        if table_info.alias and table_info.alias != table_info.name:
            alias_map[table_info.alias] = tables_set

    return alias_map


def _resolve_to_physical_set(
    name_or_alias: str,
    alias_map: dict[str, set[str]],
    source_name: str,
    leaf_map: dict[str, set[str]],
) -> set[str]:
    """将表名/别名解析为物理表名集合

    查找顺序：
    1. 别名映射中查找
    2. leaf_map 中查找（CTE 名称）
    3. 假定它就是物理表名
    """
    if name_or_alias in alias_map:
        return alias_map[name_or_alias]

    if name_or_alias in leaf_map:
        return leaf_map[name_or_alias]

    # 未知名称，假定为物理表
    return {name_or_alias}


def _collect_physical_tables(
    all_tables: list[TableInfo],
    ctes: list["CTEInfo"],
    leaf_map: dict[str, set[str]],
    cte_map: dict[str, "CTEInfo"],
) -> list[TableInfo]:
    """收集所有物理表（非 CTE），去重"""
    cte_names = {cte.name for cte in ctes}
    physical_names: set[str] = set()
    physical_tables: list[TableInfo] = []

    for table_info in all_tables:
        name = table_info.name
        if name in cte_names:
            # CTE 引用，展开为底层物理表
            for leaf_name in leaf_map.get(name, set()):
                _add_table_if_new(physical_names, physical_tables, leaf_name, table_info.schema)
        else:
            # 直接是物理表
            _add_table_if_new(
                physical_names, physical_tables, name, table_info.schema
            )

    # 也收集 CTE 内部出现的物理表（可能未出现在顶层 tables 中）
    for cte_name, leaves in leaf_map.items():
        for leaf_name in leaves:
            cte = cte_map.get(cte_name)
            schema = cte.tables[0].schema if cte and cte.tables else None
            _add_table_if_new(physical_names, physical_tables, leaf_name, schema)

    return physical_tables


def _add_table_if_new(
    seen: set[str],
    table_list: list[TableInfo],
    name: str,
    schema: str | None = None,
) -> None:
    """向列表中添加 TableInfo，以 name 去重"""
    if name not in seen:
        seen.add(name)
        table_list.append(TableInfo(name=name, schema=schema))


def _add_join_if_new(
    existing: list[PhysicalJoinInfo],
    join: PhysicalJoinInfo,
) -> None:
    """添加 JOIN 关系，避免重复（忽略方向性）"""
    key = (join.left_table, join.right_table, join.join_type, join.condition)
    reverse_key = (join.right_table, join.left_table, join.join_type, join.condition)
    for ej in existing:
        ej_key = (ej.left_table, ej.right_table, ej.join_type, ej.condition)
        if ej_key == key or ej_key == reverse_key:
            return
    existing.append(join)
