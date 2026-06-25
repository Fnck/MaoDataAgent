"""CPT 文件解析与 ClickHouse SQL 分析模块"""

from __future__ import annotations

import logging
import re

import sqlglot
from sqlglot import exp

from app.cpt_parser.xml_parser import parse_cpt_file
from app.cpt_parser.template_preprocessor import preprocess_sql
from app.cpt_parser.sql_analyzer import analyze_sql
from app.cpt_parser.physical_resolver import resolve_physical_relations
from app.cpt_parser.models import (
    CPTAnalysisResult,
    CPTDataset,
    CPTFile,
    CPTParameter,
    CTEInfo,
    ColumnInfo,
    JoinInfo,
    PhysicalJoinInfo,
    SQLAnalysisResult,
    TableInfo,
)

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_cpt_file",
    "analyze_cpt_file_with_llm",
    "CPTAnalysisResult",
    "CPTParameter",
    "CPTDataset",
    "CPTFile",
    "SQLAnalysisResult",
    "TableInfo",
    "ColumnInfo",
    "CTEInfo",
    "JoinInfo",
    "PhysicalJoinInfo",
]


def analyze_cpt_file(file_path: str) -> CPTAnalysisResult:
    """完整的 CPT 文件分析流程：XML 解析 → 模板预处理 → SQL 分析"""
    # Step 1: 解析 XML
    cpt_file = parse_cpt_file(file_path)

    result = CPTAnalysisResult(
        file_path=file_path,
        parameters=cpt_file.parameters,
    )

    # Step 2: 提取字段映射（来自 zdsx 数据集）
    result.field_mapping = _extract_field_mapping(cpt_file)

    # Step 3: 对每个数据集进行 SQL 分析
    for dataset in cpt_file.datasets:
        try:
            # 预处理模板语法
            cleaned = preprocess_sql(dataset.query, cpt_file.parameters)
            dataset.cleaned_query = cleaned

            # SQL 分析
            analysis = analyze_sql(cleaned, dataset_name=dataset.name)

            # Step 4: 解析物理表关系（展开 CTE，提取物理表 JOIN）
            analysis.physical_tables, analysis.physical_joins = resolve_physical_relations(analysis)

            result.datasets[dataset.name] = analysis

        except Exception as e:
            logger.error("Failed to analyze dataset '%s': %s", dataset.name, e)
            result.errors.append(f"Failed to analyze dataset '{dataset.name}': {e}")

    return result


def _extract_field_mapping(cpt_file: CPTFile) -> dict[str, str]:
    """从 zdsx 数据集中提取中英文字段映射

    zdsx 的典型结构：
    select zd, xs, num, filed from (
      select '产品二维码' zd, '产品二维码' xs, 1 num, 'product_code' filed
      union all
      select '总成号行号' zd, '总成号行号' xs, 2 num, 'box' filed
      ...
    )

    映射关系：中文名(zd/xs) → 英文列名(filed)
    """
    mapping: dict[str, str] = {}
    zdsx = next((d for d in cpt_file.datasets if d.name == "zdsx"), None)
    if zdsx is None:
        return mapping

    cleaned = preprocess_sql(zdsx.query, cpt_file.parameters)

    # 方法1：按 union all 分段，提取每段中的中文名和英文列名
    # 每段格式：select '`中文名`' zd, '中文名' as xs, N as num, 'english_col' [as filed]
    segments = re.split(r"\bunion\s+all\b", cleaned, flags=re.IGNORECASE)
    for seg in segments:
        # 提取 xs 列的值（中文显示名）
        xs_match = re.search(r"['`]([^'`]+)['`]\s+(?:as\s+)?xs\b", seg, re.IGNORECASE)
        # 提取最后一个单引号字符串（英文列名，即 filed 列的值）
        filed_matches = re.findall(r"'(\w+)'", seg)
        if xs_match and filed_matches:
            chinese_name = xs_match.group(1).strip("`")
            english_name = filed_matches[-1]  # 最后一个单引号字符串是 filed 值
            if chinese_name and english_name:
                mapping[chinese_name] = english_name

    if mapping:
        return mapping

    # 方法2：用 sqlglot 解析 UNION ALL 子查询
    try:
        ast = sqlglot.parse_one(cleaned, dialect="clickhouse")
        for subquery in ast.find_all(exp.Select):
            expressions = subquery.args.get("expressions", [])
            zd_val = None
            filed_val = None
            for expr in expressions:
                alias = expr.alias or ""
                if alias.lower() == "filed" and isinstance(expr, exp.Alias):
                    inner = expr.this
                    if isinstance(inner, exp.Literal):
                        filed_val = inner.this
                elif alias.lower() in ("zd", "xs") and isinstance(expr, exp.Alias):
                    inner = expr.this
                    if isinstance(inner, exp.Literal) and not zd_val:
                        zd_val = inner.this
            if zd_val and filed_val:
                mapping[zd_val] = filed_val
    except Exception as e:
        logger.warning("Failed to extract field mapping from zdsx: %s", e)

    return mapping


async def analyze_cpt_file_with_llm(file_path: str) -> CPTAnalysisResult:
    """完整的 CPT 文件分析流程 + LLM 描述增强"""
    from app.cpt_parser.llm_enricher import enrich_cpt_analysis

    result = analyze_cpt_file(file_path)
    result = await enrich_cpt_analysis(result)
    return result
