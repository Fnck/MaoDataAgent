"""CPT XML 文件解析：提取数据集 SQL 和参数定义"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from app.cpt_parser.models import CPTDataset, CPTFile, CPTParameter

logger = logging.getLogger(__name__)


def _read_file_with_encoding(file_path: str) -> str:
    """读取文件，自动检测编码"""
    encodings = ("utf-8", "gbk", "gb2312", "latin-1")
    for i, encoding in enumerate(encodings):
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            if i == len(encodings) - 2:
                # 即将使用 latin-1 兜底，警告调用方
                logger.warning(
                    "Failed to decode '%s' with utf-8/gbk/gb2312, falling back to latin-1", file_path
                )
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Cannot decode file: {file_path}")


def parse_cpt_file(file_path: str) -> CPTFile:
    """解析 CPT XML 文件，提取数据集和参数"""
    content = _read_file_with_encoding(file_path)
    root = ET.fromstring(content)

    datasets = _extract_datasets(root)
    parameters = _extract_parameters(root)

    return CPTFile(file_path=file_path, datasets=datasets, parameters=parameters)


def _extract_datasets(root: ET.Element) -> list[CPTDataset]:
    """从 TableDataMap 中提取所有 TableData 的 SQL 查询"""
    datasets: list[CPTDataset] = []
    table_data_map = root.find(".//TableDataMap")
    if table_data_map is None:
        return datasets

    for td in table_data_map.findall("TableData"):
        name = td.get("name", "")
        query_elem = td.find("Query")
        query = (query_elem.text or "") if query_elem is not None else ""
        if query.strip():
            datasets.append(CPTDataset(name=name, query=query))

    return datasets


def _extract_parameters(root: ET.Element) -> list[CPTParameter]:
    """从 Parameter 元素中提取参数名和默认值"""
    parameters: list[CPTParameter] = []
    seen: set[str] = set()

    for param_elem in root.findall(".//Parameter"):
        attrs = param_elem.find("Attributes")
        if attrs is None:
            continue
        name = attrs.get("name", "")
        if not name or name in seen:
            continue
        seen.add(name)

        o_elem = param_elem.find("O")
        default = o_elem.text if o_elem is not None else None
        if default is not None:
            default = default.strip() or None

        parameters.append(CPTParameter(name=name, default_value=default))

    return parameters
