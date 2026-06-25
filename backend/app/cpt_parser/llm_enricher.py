"""LLM 描述增强模块：为数据集和 JOIN 关系生成业务语义描述"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from app.config import get_config

if TYPE_CHECKING:
    from app.cpt_parser.models import CPTAnalysisResult, JoinInfo, SQLAnalysisResult

logger = logging.getLogger(__name__)


async def enrich_cpt_analysis(result: CPTAnalysisResult) -> CPTAnalysisResult:
    """对 CPT 分析结果进行 LLM 描述增强"""
    config = get_config()
    client = AsyncOpenAI(base_url=config.llm.api_base, api_key=config.llm.api_key)
    logger.info("Starting LLM enrichment for %d datasets in '%s'", len(result.datasets), result.file_path)

    for name, ds in result.datasets.items():
        logger.info("Enriching dataset '%s' (%d tables, %d joins, %d columns)",
                     name, len(ds.tables), len(ds.joins), len(ds.columns))
        # 生成数据集描述
        ds.description = await _generate_dataset_description(
            client, config.llm.model, config.llm.max_tokens, config.llm.temperature,
            name, ds, result.field_mapping,
        )
        if ds.description:
            logger.info("Dataset '%s' description generated: %s", name, ds.description[:200])
        else:
            logger.info("Dataset '%s' description skipped (LLM failed or returned None)", name)
        # 生成 JOIN 关系描述
        for i, join in enumerate(ds.joins):
            join.description = await _generate_join_description(
                client, config.llm.model, config.llm.max_tokens, config.llm.temperature,
                join, ds,
            )
            if join.description:
                logger.info("  JOIN #%d %s %s %s: %s",
                            i, join.left_table, join.join_type, join.right_table, join.description)
        break

    logger.info("LLM enrichment completed for '%s'", result.file_path)
    return result


async def _generate_dataset_description(
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
    name: str,
    ds: SQLAnalysisResult,
    field_mapping: dict[str, str],
) -> str | None:
    """调用 LLM 生成数据集的业务描述"""
    tables_str = "\n".join(
        f"  - {t.name}" + (f" (别名: {t.alias})" if t.alias else "") + (f" [schema: {t.schema}]" if t.schema else "")
        for t in ds.tables
    )
    ctes_str = "\n".join(f"  - {c.name}: {c.sql[:200]}" for c in ds.ctes) if ds.ctes else "  无"
    columns_str = "\n".join(
        f"  - {c.name}" + (f" (来自: {c.table_alias})" if c.table_alias else "")
        for c in ds.columns[:30]  # 限制列数避免 prompt 过长
    )
    joins_str = "\n".join(
        f"  - {j.left_table_name or j.left_table} {j.join_type} {j.right_table_name or j.right_table}"
        + (f" ON {j.condition}" if j.condition else "")
        for j in ds.joins
    )
    mapping_str = "\n".join(f"  - {k} → {v}" for k, v in list(field_mapping.items())[:20])

    prompt = f"""你是一个数据分析师，请根据以下 SQL 数据集的结构化信息，生成业务描述。

数据集名称：{name}
引用的表：
{tables_str}
CTE 列表：
{ctes_str}
关键列：
{columns_str}
JOIN 关系：
{joins_str}
字段映射（中英文）：
{mapping_str}

请用中文输出以下内容（JSON 格式）：
{{
  "source": "数据来自哪些业务系统/表，一句话概括",
  "intent": "这个数据集的业务意图，解决什么问题",
  "key_data": "核心字段及其业务含义，列出3-5个"
}}"""

    try:
        logger.info("Calling LLM for dataset '%s' description (model=%s)", name, model)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        logger.info("LLM raw response for dataset '%s': %s", name, content[:300])
        # 尝试提取 JSON（LLM 可能包裹在 ```json ... ``` 中）
        content = _extract_json(content)
        # 验证是合法 JSON
        json.loads(content)
        logger.info("Dataset '%s' description generated successfully", name)
        return content
    except Exception as e:
        logger.warning("Failed to generate dataset description for '%s': %s", name, e)
        return None


async def _generate_join_description(
    client: AsyncOpenAI,
    model: str,
    max_tokens: int,
    temperature: float,
    join: JoinInfo,
    ds: SQLAnalysisResult,
) -> str | None:
    """调用 LLM 生成 JOIN 关系的业务描述"""
    other_tables = [
        t.name + (f" (别名: {t.alias})" if t.alias else "")
        for t in ds.tables
        if t.name not in (join.left_table_name or join.left_table, join.right_table_name or join.right_table)
    ]
    other_tables_str = "、".join(other_tables[:10]) if other_tables else "无"

    prompt = f"""你是一个数据分析师，请根据以下 JOIN 关系，生成业务描述。

左表：{join.left_table_name or join.left_table}（别名：{join.left_table}）
右表：{join.right_table_name or join.right_table}（别名：{join.right_table}）
JOIN 类型：{join.join_type}
ON 条件：{join.condition or '无'}
所属数据集的其他表：{other_tables_str}

请用中文输出一句话描述这个 JOIN 的业务含义，例如：
"通过产品编码关联产品基础信息表，获取产品详细描述"

只输出一句话，不要输出其他内容。"""

    try:
        logger.info("Calling LLM for JOIN description: %s %s %s", join.left_table, join.join_type, join.right_table)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        logger.info("LLM raw response for JOIN %s-%s: %s", join.left_table, join.right_table, content[:200])
        return content
    except Exception as e:
        logger.warning("Failed to generate JOIN description for %s %s %s: %s",
                       join.left_table, join.join_type, join.right_table, e)
        return None


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 内容（处理 ```json ... ``` 包裹）"""
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首尾的 ``` 行
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])
    return text.strip()
