"""
测试数据加载工具。

支持 YAML、CSV 两种数据格式，满足用户偏好的数据驱动测试策略：
- YAML 管理全局配置与复杂结构测试数据
- CSV 管理 Q&A 对、接口参数等扁平列表数据
"""

import csv
from pathlib import Path
from typing import Any, Iterator

import yaml

from .config import DATA_DIR
from .logger import get_logger

log = get_logger(__name__)


def yaml_path(filename: str) -> Path:
    return DATA_DIR / filename


def csv_path(filename: str) -> Path:
    return DATA_DIR / filename


def load_yaml(filename: str, sub_key: str | None = None) -> Any:
    """加载 YAML 测试数据文件。

    Args:
        filename: 位于 data 目录下的 yaml 文件名，如 test_data.yaml
        sub_key: 若指定，则仅返回 yaml 顶层该 key 对应的值

    Returns:
        解析后的 YAML 对象
    """
    fpath = yaml_path(filename)
    if not fpath.exists():
        log.warning("YAML 文件不存在: %s, 返回空 dict", fpath)
        return {} if sub_key is None else None

    with open(fpath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if sub_key is not None:
        return data.get(sub_key)
    return data


def load_csv(filename: str, as_dict: bool = True) -> list[dict] | list[list[str]]:
    """加载 CSV 数据文件。

    Args:
        filename: 位于 data 目录下的 csv 文件名
        as_dict: True 则返回每行是 dict（首行为表头），False 返回 list[list]

    Returns:
        解析后的数据列表
    """
    fpath = csv_path(filename)
    if not fpath.exists():
        log.warning("CSV 文件不存在: %s, 返回空列表", fpath)
        return []

    rows: list[dict] | list[list[str]]
    with open(fpath, "r", encoding="utf-8-sig") as f:
        if as_dict:
            reader = csv.DictReader(f)
            rows = [dict(row) for row in reader]
        else:
            reader = csv.reader(f)
            rows = [list(row) for row in reader]
    return rows


def load_qa_pairs(filename: str = "qa_data.csv") -> list[dict[str, str]]:
    """专门加载 Q&A 对数据，给 ragas 评估使用。

    期望 CSV 至少含列: question, contexts（可选）, reference, type（可选）
    """
    rows = load_csv(filename, as_dict=True)
    cleaned: list[dict[str, str]] = []
    for r in rows:
        q = (r.get("question") or "").strip()
        if not q:
            continue
        cleaned.append({
            "question": q,
            "contexts": (r.get("contexts") or "").strip(),
            "reference": (r.get("reference") or "").strip(),
            "type": (r.get("type") or "general").strip(),
        })
    return cleaned
