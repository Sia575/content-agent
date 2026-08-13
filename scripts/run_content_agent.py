"""Interactive production entry point for the content operations agent."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from hotspot_agent.collectors.hackernews import fetch
from hotspot_agent.intelligence.llm_client import OpenAICompatibleClient
from hotspot_agent.shared.config import load_settings
from export_report_html import export_latest_workbench


PLATFORM_NAMES = {"xiaohongshu": "小红书", "gongzhonghao": "公众号"}
HASHTAG_LINE_RE = re.compile(r"^\s*#[^\s#]+(?:\s+#[^\s#]+)*\s*$")


def main() -> None:
    print("\n=== 内容运营 Agent：开始运行 ===")
    print("[1/5] 正在采集 Hacker News 前 20 条内容，请稍候...")
    items = fetch()[:20]
    if not items:
        print("未采集到 Hacker News 条目，流程结束。")
        return
    print(f"已采集 {len(items)} 条。")

    client = OpenAICompatibleClient(load_settings().get("llm", {}))
    print("[2/5] 正在调用 judge_topics 评估选题，请稍候...")
    judgments = _as_list(client.judge_topics([_item_payload(item) for item in items]))
    item_by_id = {item.item_id: item for item in items}
    ranked = sorted(
        (j for j in judgments if isinstance(j, dict) and j.get("item_id") in item_by_id),
        key=lambda j: _score(j.get("spread_score")),
        reverse=True,
    )
    if not ranked:
        print("未返回与采集条目匹配的有效选题判断，流程结束。")
        return

    print("[3/5] 选题排行榜（按 spread_score 从高到低）")
    _print_topic_list(ranked)
    selected = _ask_topic_indexes(len(ranked))
    if selected is None:
        print("已退出，不生成内容。")
        return
    if not selected:
        print("没有选择任何选题，流程结束。")
        return

    generated_topics: list[dict[str, Any]] = []
    review_stats = {
        "contents_generated": 0,
        "contents_approved": 0,
        "contents_rejected": 0,
    }
    print(f"\n已选择 {len(selected)} 个选题，开始生成内容...")
    for number in selected:
        judgment = ranked[number - 1]
        item = item_by_id[judgment["item_id"]]
        print(f"\n正在生成第 {number} 题：{judgment.get('topic', '未命名选题')}")
        response = client.generate_content(
            topic=str(judgment.get("topic", "")),
            why_hot=str(judgment.get("why_hot", "")),
            target_audience=str(judgment.get("target_audience", "")),
            source_urls=[item.url],
            platforms=_as_platforms(judgment.get("suitable_platforms")),
        )
        contents = [c for c in _as_list(response) if isinstance(c, dict)]
        # Count every valid platform result returned by the LLM before review.
        review_stats["contents_generated"] += len(contents)
        generated_topics.append({
            "number": number,
            "judgment": judgment,
            "item": item,
            "contents": contents,
        })

    print("\n[4/5] 第二次人工确认：逐条确认生成内容")
    approved_topics: list[dict[str, Any]] = []
    for topic_data in generated_topics:
        approved = _review_topic(topic_data, review_stats)
        if approved:
            topic_data["contents"] = approved
            approved_topics.append(topic_data)

    if review_stats["contents_generated"] != (
        review_stats["contents_approved"] + review_stats["contents_rejected"]
    ):
        print(
            "警告：内容统计不一致："
            f"generated={review_stats['contents_generated']}, "
            f"approved={review_stats['contents_approved']}, "
            f"rejected={review_stats['contents_rejected']}"
        )

    if not approved_topics:
        print("没有通过确认的内容，不写入输出文件。")
        return

    print("\n[5/5] 正在写入输出文件...")
    settings = load_settings()
    output_dir = REPO_ROOT / settings.get("app", {}).get("output_dir", "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    date_text = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "candidates_total": len(items),
        "topics_selected": len(selected),
        "contents_generated": review_stats["contents_generated"],
        "contents_approved": review_stats["contents_approved"],
        "contents_rejected": review_stats["contents_rejected"],
    }
    package = _build_package(approved_topics, date_text, stats)
    markdown = _build_markdown(approved_topics, date_text, stats)
    package_path = output_dir / f"content-package-{date_text}.json"
    workbench_path = output_dir / f"content-workbench-{date_text}.md"
    _write_json(package_path, package)
    workbench_path.write_text(markdown, encoding="utf-8")
    _write_json(output_dir / "latest-content.json", package)
    (output_dir / "latest-workbench.md").write_text(markdown, encoding="utf-8")
    print(f"已写入：{package_path}")
    print(f"已写入：{workbench_path}")
    print(f"已更新：{output_dir / 'latest-content.json'}")
    print(f"已更新：{output_dir / 'latest-workbench.md'}")
    workbench_html_path = export_latest_workbench(output_dir)
    print(f"已更新：{workbench_html_path}")


def _item_payload(item: Any) -> dict[str, Any]:
    return {"item_id": item.item_id, "title": item.title, "url": item.url,
            "source_type": item.source_type, "rank": item.rank,
            "heat_value": item.heat_value, "raw_metrics": item.raw_metrics}


def _print_topic_list(ranked: list[dict[str, Any]]) -> None:
    for number, judgment in enumerate(ranked, start=1):
        print(f"\n[{number}] spread_score: {judgment.get('spread_score', '未返回')}")
        print(f"topic: {judgment.get('topic', '未返回')}")
        print(f"why_hot: {judgment.get('why_hot', '未返回')}")
        print(f"suitable_platforms: {_format_value(judgment.get('suitable_platforms', []))}")


def _ask_topic_indexes(total: int) -> list[int] | None:
    while True:
        answer = input("\n第一次人工确认：请输入要生成内容的选题编号（支持逗号分隔多选），输入 q 退出：").strip().lower()
        if answer == "q":
            return None
        try:
            numbers = [int(part.strip()) for part in answer.split(",") if part.strip()]
        except ValueError:
            print("输入格式不正确，请输入例如 1 或 1,3,5；输入 q 退出。")
            continue
        if not numbers or any(number < 1 or number > total for number in numbers):
            print(f"编号必须是 1 到 {total} 之间的数字，请重新输入。")
            continue
        if len(numbers) != len(set(numbers)):
            print("检测到重复编号，请每个选题只输入一次。")
            continue
        return numbers


def _review_topic(topic_data: dict[str, Any], stats: dict[str, int]) -> list[dict[str, Any]]:
    number, judgment, contents = topic_data["number"], topic_data["judgment"], topic_data["contents"]
    print("\n" + "=" * 80)
    print(f"选题 [{number}]：{judgment.get('topic', '未命名选题')}")
    print(f"来源：{topic_data['item'].url}")
    if not contents:
        print("模型没有返回可确认的平台内容，该选题丢弃。")
        return []
    approved: list[dict[str, Any]] = []
    for platform_number, content in enumerate(contents, start=1):
        _print_content(content, platform_number)
        while True:
            decision = input("人工确认：输入 y 通过，n 丢弃，e 编辑正文：").strip().lower()
            if decision == "y":
                approved.append(content)
                stats["contents_approved"] += 1
                break
            if decision == "n":
                print("该平台内容已丢弃。")
                stats["contents_rejected"] += 1
                break
            if decision == "e":
                print("编辑模式：请输入新的正文；输入完成后按回车提交。")
                content["body"] = input("新正文：")
                print("正文已更新，请再次确认。")
                _print_content(content, platform_number)
                continue
            print("输入无效，请输入 y、n 或 e。")
    return approved


def _print_content(content: dict[str, Any], platform_number: int) -> None:
    print("\n" + "-" * 72)
    print(f"平台内容 #{platform_number} | platform: {content.get('platform', '未返回')}")
    print(f"标题：{content.get('title', '')}")
    print(f"正文：\n{content.get('body', '')}")
    print(f"标签：{_format_value(content.get('tags', []))}")


def _build_package(topics: list[dict[str, Any]], date_text: str, stats: dict[str, int]) -> dict[str, Any]:
    return {"generated_date": date_text, **stats, "topics": [
        {"topic": d["judgment"].get("topic", ""), "why_hot": d["judgment"].get("why_hot", ""),
         "spread_score": d["judgment"].get("spread_score", ""),
         "target_audience": d["judgment"].get("target_audience", ""),
         "suitable_platforms": _as_platforms(d["judgment"].get("suitable_platforms")),
         "risk_note": d["judgment"].get("risk_note", ""), "source_urls": [d["item"].url],
         "contents": d["contents"]}
        for d in topics
    ]}


def _build_markdown(topics: list[dict[str, Any]], date_text: str, stats: dict[str, int]) -> str:
    lines = [f"# 内容工作台 - {date_text}", "", "> 仅收录通过第二次人工确认的内容。", ""]
    lines.extend([f"- 候选总数：{stats['candidates_total']}",
                  f"- 人工选中数：{stats['topics_selected']}",
                  f"- 生成条数：{stats['contents_generated']}",
                  f"- 确认通过数：{stats['contents_approved']}",
                  f"- 丢弃数：{stats['contents_rejected']}", ""])
    for index, data in enumerate(topics, start=1):
        judgment = data["judgment"]
        lines.extend([f"## {index}. {judgment.get('topic', '')}",
                      f"- topic：{judgment.get('topic', '')}", f"- why_hot：{judgment.get('why_hot', '')}",
                      f"- spread_score：{judgment.get('spread_score', '')}",
                      f"- target_audience：{judgment.get('target_audience', '')}",
                      f"- risk_note：{judgment.get('risk_note', '')}",
                      f"- 原始链接：{data['item'].url}", ""])
        for content in data["contents"]:
            platform = str(content.get("platform", "未返回"))
            lines.extend([f"### {PLATFORM_NAMES.get(platform, platform)}",
                          f"**标题：** {content.get('title', '')}", "", "**正文：**", "",
                          _format_body_for_markdown(content.get("body", "")), ""])
    return "\n".join(lines)


def _format_body_for_markdown(body: Any) -> str:
    """Keep standalone Xiaohongshu hashtag lines from becoming headings."""
    text = str(body)
    return "\n".join(
        f"标签：{line.strip()}" if HASHTAG_LINE_RE.fullmatch(line) else line
        for line in text.split("\n")
    )


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _as_list(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        return response["results"]
    raise ValueError("LLM 返回结果不是 JSON 数组或 results 数组")


def _as_platforms(value: Any) -> list[str]:
    return [str(platform) for platform in value] if isinstance(value, (list, tuple)) else []


def _score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def _format_value(value: Any) -> str:
    return ", ".join(str(item) for item in value) if isinstance(value, (list, tuple)) else str(value)


if __name__ == "__main__":
    main()
