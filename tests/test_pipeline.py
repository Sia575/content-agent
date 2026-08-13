from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.processing.deduplication import Deduplicator
from hotspot_agent.processing.filtering import RuleFilter
from hotspot_agent.publishing.markdown import MarkdownRenderer
from hotspot_agent.shared.schemas import DailyReport, NewsItem
from hotspot_agent.shared.schemas import AnalyzedNewsItem


SHANGHAI = ZoneInfo("Asia/Shanghai")


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 12, 8, 0, tzinfo=SHANGHAI)
        self.filter = RuleFilter(["ai", "人工智能", "芯片"], ["中国", "华为", "China"])

    def test_filter_respects_time_topic_and_region(self) -> None:
        items = [
            NewsItem("AI platform update", "https://example.com/one", "Source", self.now - timedelta(hours=2)),
            NewsItem("华为发布人工智能产品", "https://example.com/two", "Source", self.now - timedelta(hours=3)),
            NewsItem("AI old news", "https://example.com/old", "Source", self.now - timedelta(hours=25)),
            NewsItem("Sports update", "https://example.com/sports", "Source", self.now - timedelta(hours=1)),
        ]

        filtered = self.filter.filter_and_classify(items, self.now - timedelta(hours=24), self.now)

        self.assertEqual([item.region for item in filtered], ["international", "domestic"])

    def test_deduplicate_ignores_tracking_query_parameters(self) -> None:
        first = NewsItem("AI chip launch", "https://example.com/news?id=1&utm_source=rss", "A", self.now)
        second = NewsItem("AI chip launch", "https://example.com/news?id=1", "B", self.now - timedelta(minutes=1))

        unique = Deduplicator().deduplicate([second, first])

        self.assertEqual(unique, [first])

    def test_renderer_uses_fixed_source_attribution_template(self) -> None:
        item = NewsItem(
            "AI chip launch",
            "https://example.com/news",
            "Example Source",
            self.now,
            "<p>A company announced an AI chip.</p>",
            region="international",
        )
        report = DailyReport(self.now, self.now - timedelta(hours=24), self.now, (item,), ())

        rendered = MarkdownRenderer().render(report)

        self.assertIn("Example Source 报道：A company announced an AI chip.", rendered)
        self.assertIn("## 国内科技新闻", rendered)

    def test_renderer_prefers_llm_summary_and_score_over_rss_summary(self) -> None:
        item = AnalyzedNewsItem(
            item_id="news-0001",
            title="Original RSS title",
            url="https://example.com/news",
            source_name="Example Source",
            published_at=self.now,
            summary="RSS original summary must not be rendered in LLM mode.",
            region="international",
            is_technology=True,
            is_hotspot=True,
            impact_score=93,
            summary_zh="LLM 生成的中文客观摘要。",
        )
        report = DailyReport(self.now, self.now - timedelta(hours=24), self.now, (item,), ())

        rendered = MarkdownRenderer().render(report)

        self.assertIn("LLM 生成的中文客观摘要。", rendered)
        self.assertNotIn("RSS original summary must not be rendered", rendered)
        self.assertIn("影响力评分：93/100", rendered)


if __name__ == "__main__":
    unittest.main()
