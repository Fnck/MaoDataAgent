from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CPTParameter(BaseModel):
    """FineReport 模板参数"""
    name: str
    default_value: str | None = None


class CPTDataset(BaseModel):
    """CPT 文件中的数据集"""
    name: str
    query: str
    cleaned_query: str | None = None


class CPTFile(BaseModel):
    """CPT 文件解析结果"""
    file_path: str
    datasets: list[CPTDataset] = []
    parameters: list[CPTParameter] = []


class TableInfo(BaseModel):
    """SQL 表信息"""
    name: str
    alias: str | None = None
    schema: str | None = None


class ColumnInfo(BaseModel):
    """SQL 列信息"""
    name: str
    expression: str
    table_alias: str | None = None
    type: str = "unknown"


class CTEInfo(BaseModel):
    """CTE（WITH 子句）信息"""
    name: str
    sql: str
    tables: list[TableInfo] = []
    columns: list[ColumnInfo] = []
    joins: list[JoinInfo] = []


class JoinInfo(BaseModel):
    """JOIN 关系信息"""
    left_table: str
    right_table: str
    join_type: str
    condition: str | None = None
    left_table_name: str | None = None
    right_table_name: str | None = None
    description: str | None = None


class PhysicalJoinInfo(BaseModel):
    """物理表 JOIN 关系（CTE 已解析为底层物理表）"""
    left_table: str
    right_table: str
    join_type: str
    condition: str | None = None
    source: str = "main"  # "main" 或 CTE 名称，用于追溯


class SubqueryAliasInfo(BaseModel):
    """子查询别名信息：别名 → 内部表列表"""
    alias: str
    tables: list[TableInfo] = []


class SQLAnalysisResult(BaseModel):
    """SQL 分析结果"""
    source_query: str
    tables: list[TableInfo] = []
    ctes: list[CTEInfo] = []
    columns: list[ColumnInfo] = []
    joins: list[JoinInfo] = []
    subquery_alias_map: list[SubqueryAliasInfo] = []
    settings: dict[str, Any] = {}
    parse_errors: list[str] = []
    description: str | None = None
    physical_tables: list[TableInfo] = []
    physical_joins: list[PhysicalJoinInfo] = []


class CPTAnalysisResult(BaseModel):
    """CPT 文件完整分析结果"""
    file_path: str
    parameters: list[CPTParameter] = []
    datasets: dict[str, SQLAnalysisResult] = {}
    field_mapping: dict[str, str] = {}
    errors: list[str] = []
