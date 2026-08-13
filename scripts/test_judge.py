"""Validate topic judgment against the current Hacker News top stories."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from hotspot_agent.collectors.hackernews import fetch
from hotspot_agent.intelligence.llm_client import OpenAICompatibleClient
from hotspot_agent.shared.config import load_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    items = fetch()[:20]
    if not items:
        print("未采集到 Hacker News 条目。")
        return

    item_payloads = [
        {
            "item_id": item.item_id,
            "title": item.title,
            "url": item.url,
            "source_type": item.source_type,
            "rank": item.rank,
            "heat_value": item.heat_value,
            "raw_metrics": item.raw_metrics,
        }
        for item in items
    ]
    response = OpenAICompatibleClient(load_settings().get("llm", {})).judge_topics(item_payloads)
    judgments = _as_list(response)
    judgments_by_id = {
        judgment.get("item_id"): judgment
        for judgment in judgments
        if isinstance(judgment, dict) and judgment.get("item_id")
    }

    print(f"\n选题判断结果（{len(items)} 条）")
    for item in items:
        judgment = judgments_by_id.get(item.item_id, {})
        print("\n" + "=" * 72)
        print(f"rank: {item.rank}")
        print(f"原标题: {item.title}")
        print(f"heat_value: {item.heat_value}")
        print(f"topic: {judgment.get('topic', '未返回')}")
        print(f"why_hot: {judgment.get('why_hot', '未返回')}")
        print(f"spread_score: {judgment.get('spread_score', '未返回')}")
        print(f"target_audience: {judgment.get('target_audience', '未返回')}")
        print(f"suitable_platforms: {_format_value(judgment.get('suitable_platforms', '未返回'))}")
        print(f"risk_note: {judgment.get('risk_note', '未返回')}")

    ranked = sorted(
        (judgment for judgment in judgments if isinstance(judgment, dict)),
        key=lambda judgment: _score(judgment.get("spread_score")),
        reverse=True,
    )
    print("\n传播潜力简表（从高到低）")
    for judgment in ranked:
        print(f"{judgment.get('spread_score', '未返回'):>3} | {judgment.get('topic', '未返回')}")


def _as_list(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        return response["results"]
    raise ValueError(f"LLM 返回结果不是 JSON 数组: {json.dumps(response, ensure_ascii=False)}")


def _score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def _format_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


if __name__ == "__main__":
    main()
