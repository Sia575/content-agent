from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_REGIONS = {"international", "domestic"}
ALLOWED_TOPICS = {
    "AI", "芯片", "云计算", "航天", "自动驾驶", "具身智能", "加密货币",
    "AI数据中心", "电力能源", "散热", "网络基础设施", "卫星通信", "空间数据",
    "金融科技", "广告科技", "其他科技",
}


@dataclass(frozen=True)
class SemanticResult:
    item_id: str
    is_technology: bool
    is_hotspot: bool
    region: str
    summary_zh: str
    impact_score: int
    topic: str = "其他科技"
    impact_factors: tuple[str, ...] = ()


def result_from_dict(value: dict[str, Any]) -> SemanticResult:
    required = {"item_id", "is_technology", "is_hotspot", "region", "summary_zh", "impact_score"}
    missing = required - value.keys()
    if missing:
        raise ValueError(f"Missing LLM result fields: {sorted(missing)}")
    if not isinstance(value["item_id"], str) or not isinstance(value["summary_zh"], str):
        raise ValueError("item_id and summary_zh must be strings")
    if not isinstance(value["is_technology"], bool) or not isinstance(value["is_hotspot"], bool):
        raise ValueError("is_technology and is_hotspot must be booleans")
    if value["region"] not in ALLOWED_REGIONS:
        raise ValueError(f"Invalid region: {value['region']}")
    if not isinstance(value["impact_score"], int) or not 0 <= value["impact_score"] <= 100:
        raise ValueError("impact_score must be an integer from 0 to 100")
    if not value["summary_zh"].strip():
        raise ValueError("summary_zh cannot be empty")
    topic = value.get("topic", "其他科技")
    if topic not in ALLOWED_TOPICS:
        topic = "其他科技"
    factors = value.get("impact_factors", [])
    if not isinstance(factors, list) or not all(isinstance(item, str) for item in factors):
        raise ValueError("impact_factors must be a list of strings")
    return SemanticResult(
        item_id=value["item_id"], is_technology=value["is_technology"],
        is_hotspot=value["is_hotspot"], region=value["region"],
        summary_zh=value["summary_zh"].strip(), impact_score=value["impact_score"],
        topic=topic, impact_factors=tuple(factors),
    )
