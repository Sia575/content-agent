from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "v2.0.0"
SYSTEM_PROMPT = """你是科技新闻语义筛选器。只依据用户提供的标题和来源摘要判断。
对每条输入返回一个结果：判断是否为指定科技新闻和热点，分类为 international 或 domestic，并生成中文客观摘要。
不得补充输入之外的事实、数字、因果关系或预测；不得生成或修改 URL 和时间。必须返回 JSON：{"schema_version":"v2","results":[...]}。"""

TOPIC_JUDGE_PROMPT = """你是一个内容运营的选题编辑。下面是从公开热榜采集的一批条目，每条包含标题、来源、榜单排名和热度指标。

你的任务不是做新闻摘要，而是判断：这条热榜内容能不能变成一篇值得发的内容。

对每条判断以下几点:
1. topic —— 把原始标题转成一个具体的内容选题角度。不要复述标题。
   反例:"OpenAI 发布新模型"(这是新闻标题)
   正例:"新模型发布后，普通人手上的 AI 工具要不要换"(这是选题)
2. why_hot —— 它为什么能传播。只能从以下四类中选一类并说明:
   - 争议:有明确的对立立场，评论区会吵
   - 实用:读者看完能立刻用上
   - 情绪:触发焦虑、爽感、共鸣或愤怒
   - 新奇:反直觉、第一次听说
   如果四类都不明显，说明它不适合做内容，spread_score 给低分。
3. spread_score —— 0-100 的传播潜力。评分依据是"读者会不会转发"，不是"这件事重不重要"。
   注意:热榜排名高不等于传播潜力高。技术性强、门槛高、只有从业者关心的条目要给低分。
4. target_audience —— 具体到人群，不要写"对科技感兴趣的人"这种废话。
5. suitable_platforms —— 从 ["xiaohongshu","gongzhonghao"] 中选，可多选，也可以一个都不选。
   小红书:轻、有情绪、有画面感、和个人生活相关
   公众号:能展开、有信息增量、适合深度
6. risk_note —— 是否涉及未经证实的信息、企业负面、政治敏感、医疗金融建议。没有就写"无"。

只输出 JSON 数组，每个元素包含:item_id, topic, why_hot, spread_score, target_audience, suitable_platforms, risk_note。
不要输出任何解释文字或 markdown 代码块标记。

输入:
{items_json}"""

CONTENT_GEN_PROMPT = """你是一个熟悉中文社交平台调性的内容创作者。

选题信息:
- 选题角度:{topic}
- 传播抓手:{why_hot}
- 目标读者:{target_audience}
- 原始来源:{source_urls}

请为以下平台各生成一版内容:{platforms}

平台要求:
- xiaohongshu:标题 20 字以内，带 1-2 个 emoji，要有钩子；正文 300 字以内，短句分行，口语化，第一人称；结尾一句互动引导；5-8 个话题标签。
- gongzhonghao:标题 25 字以内，可以用悬念或数字；正文 800-1200 字，分 3-4 个小标题，开头要有一个具体场景或问题，中间给信息增量，结尾给一个可执行的建议；不要标签。

硬性要求:
- 所有事实性表述必须能追溯到给定的来源链接。不确定的细节直接不写，不要编造数字、人名、时间。
- 不要写"随着人工智能的快速发展"这类空洞开头。
- 每个平台的内容必须真的不同，不是同一篇文章改字数。

只输出 JSON 数组，每个元素包含:platform, title, body, tags(数组), source_urls(数组)。
不要输出任何解释文字或 markdown 代码块标记。"""


def build_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"task": "classify_and_summarize_technology_news", "schema_version": "v2", "language": "zh-CN", "items": items}


def build_user_prompt(items: list[dict[str, Any]]) -> str:
    return json.dumps(build_payload(items), ensure_ascii=False)
