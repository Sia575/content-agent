from __future__ import annotations

import html
import re
from pathlib import Path

from hotspot_agent.shared.schemas import AnalyzedNewsItem, DailyReport, NewsItem


class MarkdownRenderer:
    def render(self, report: DailyReport) -> str:
        lines = [
            "# 科技热点日报",
            "",
            f"统计区间：{self._format_time(report.window_start)} 至 {self._format_time(report.window_end)}（Asia/Shanghai）",
            "",
            "## 国际科技新闻",
            "",
        ]
        lines.extend(self._render_section(report.international))
        lines.extend(["## 国内科技新闻", ""])
        lines.extend(self._render_section(report.domestic))
        return "\n".join(lines).rstrip() + "\n"

    def write(self, content: str, output_dir: Path, generated_at) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"hotspot-daily-{generated_at:%Y-%m-%d}.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _render_section(self, items: tuple[NewsItem | AnalyzedNewsItem, ...]) -> list[str]:
        if not items:
            return ["暂无符合筛选规则的新闻。", ""]
        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.extend([f"### {index}. {item.title}", f"- 时间：{self._format_time(item.published_at)}（Asia/Shanghai）"])
            if isinstance(item, AnalyzedNewsItem):
                lines.append(f"- 摘要：{item.summary_zh or self._summary(item)}")
                if item.impact_score is not None:
                    lines.append(f"- 影响力评分：{item.impact_score}/100")
            else:
                lines.append(f"- 摘要：{self._summary(item)}")
            lines.extend([f"- 来源：[{item.source_name}]({item.url})", ""])
        return lines

    @staticmethod
    def _format_time(value) -> str:
        return value.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _summary(item: NewsItem) -> str:
        # Fixed template: source text is only cleaned and truncated, never interpreted.
        text = re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", item.summary))).strip()
        if not text:
            return f"{item.source_name} 发布了题为《{item.title}》的报道。"
        if len(text) > 180:
            text = text[:177].rstrip() + "..."
        return f"{item.source_name} 报道：{text}"
