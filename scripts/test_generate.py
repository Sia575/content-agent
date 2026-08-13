"""Generate content for the highest-scoring topic from one topic-judge run."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from hotspot_agent.collectors.hackernews import fetch
from hotspot_agent.intelligence.llm_client import OpenAICompatibleClient
from hotspot_agent.shared.config import load_settings
from test_judge import _as_list, _score


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
    client = OpenAICompatibleClient(load_settings().get("llm", {}))
    judgments = _as_list(client.judge_topics(item_payloads))
    ranked = sorted(
        (judgment for judgment in judgments if isinstance(judgment, dict)),
        key=lambda judgment: _score(judgment.get("spread_score")),
        reverse=True,
    )
    if not ranked:
        print("未返回有效的选题判断结果。")
        return

    # Keep this probe intentionally limited to one topic until the three formats pass review.
    judgment = ranked[0]
    item_by_id = {item.item_id: item for item in items}
    item = item_by_id.get(judgment.get("item_id"))
    if item is None:
        raise ValueError(f"选题判断缺少对应采集条目: {judgment.get('item_id')}")

    platforms = judgment.get("suitable_platforms", [])
    if not isinstance(platforms, list):
        platforms = list(platforms) if isinstance(platforms, tuple) else []
    print("\n选中选题")
    print(json.dumps(judgment, ensure_ascii=False, indent=2))
    print(f"source_urls: {json.dumps([item.url], ensure_ascii=False)}")

    generated = client.generate_content(
        topic=str(judgment.get("topic", "")),
        why_hot=str(judgment.get("why_hot", "")),
        target_audience=str(judgment.get("target_audience", "")),
        source_urls=[item.url],
        platforms=platforms,
    )
    contents = _as_list(generated)
    print("\n生成内容")
    for content in contents:
        if not isinstance(content, dict):
            continue
        platform = content.get("platform", "未返回")
        title = str(content.get("title", ""))
        body = str(content.get("body", ""))
        print("\n" + "=" * 72)
        print(f"platform: {platform}")
        print(f"title ({len(title)} 字): {title}")
        print(f"body ({len(body)} 字):\n{body}")
        print(f"tags: {json.dumps(content.get('tags', []), ensure_ascii=False)}")
        print(f"source_urls: {json.dumps(content.get('source_urls', []), ensure_ascii=False)}")

    bodies = [
        str(content.get("body", ""))
        for content in contents
        if isinstance(content, dict) and content.get("body")
    ]
    print("\n格式检查")
    print(f"公众号正文 800 字以上: {_gongzhonghao_long_enough(contents)}")
    print(f"三版正文均不同: {len(bodies) == len(set(bodies))}")


def _gongzhonghao_long_enough(contents: list[dict[str, Any]]) -> bool:
    return any(
        content.get("platform") == "gongzhonghao"
        and len(str(content.get("body", ""))) >= 800
        for content in contents
    )


if __name__ == "__main__":
    main()
