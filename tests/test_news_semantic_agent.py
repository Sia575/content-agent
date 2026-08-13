from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.intelligence.news_semantic_agent import NewsSemanticAgent
from hotspot_agent.shared.schemas import NewsItem


class FakeClient:
    def analyze(self, items):
        return {
            "results": [
                {
                    "item_id": item["item_id"],
                    "is_technology": True,
                    "is_hotspot": True,
                    "region": "domestic",
                    "summary_zh": "模型生成的客观摘要。",
                    "impact_score": 77,
                    "topic": "AI",
                    "impact_factors": [],
                }
                for item in items
            ]
        }


class NewsSemanticAgentTests(unittest.TestCase):
    def test_normalizes_provider_field_names_before_validation(self) -> None:
        payload = {
            "results": [{
                "item_id": "news-0000",
                "is_tech_news": True,
                "category": "international",
                "summary": "abc",
                "impact_score": 80,
            }]
        }

        normalized = NewsSemanticAgent._normalize_response(payload)
        result = normalized["results"][0]

        self.assertTrue(result["is_technology"])
        self.assertTrue(result["is_hotspot"])
        self.assertEqual(result["region"], "international")
        self.assertEqual(result["summary_zh"], "abc")

    def test_normalizes_is_technology_news_alias_before_validation(self) -> None:
        payload = {
            "results": [{
                "item_id": "news-0000",
                "is_technology_news": True,
                "category": "international",
                "summary": "abc",
                "impact_score": 80,
            }]
        }

        normalized = NewsSemanticAgent._normalize_response(payload)
        result = normalized["results"][0]

        self.assertEqual(result["is_technology"], True)
        self.assertEqual(result["is_hotspot"], True)
        self.assertEqual(result["region"], "international")
        self.assertEqual(result["summary_zh"], "abc")

    def test_normalizes_is_target_alias_before_validation(self) -> None:
        payload = {
            "results": [{
                "item_id": "news-0000",
                "is_target": True,
                "category": "international",
                "summary": "abc",
                "impact_score": 80,
            }]
        }

        normalized = NewsSemanticAgent._normalize_response(payload)
        result = normalized["results"][0]

        self.assertEqual(result["is_technology"], True)
        self.assertEqual(result["is_hotspot"], True)
        self.assertEqual(result["region"], "international")
        self.assertEqual(result["summary_zh"], "abc")

    def test_normalizes_is_tech_news_hotspot_alias_before_validation(self) -> None:
        payload = {
            "results": [{
                "item_id": "news-0000",
                "is_tech_news_hotspot": True,
                "category": "international",
                "summary": "abc",
                "impact_score": 80,
            }]
        }

        normalized = NewsSemanticAgent._normalize_response(payload)
        result = normalized["results"][0]

        self.assertEqual(result["is_technology"], True)
        self.assertEqual(result["is_hotspot"], True)
        self.assertEqual(result["region"], "international")
        self.assertEqual(result["summary_zh"], "abc")

    def test_normalizes_is_relevant_alias_before_validation(self) -> None:
        payload = {
            "results": [{
                "item_id": "news-0000",
                "is_relevant": True,
                "category": "international",
                "summary": "abc",
                "impact_score": 80,
            }]
        }

        normalized = NewsSemanticAgent._normalize_response(payload)
        result = normalized["results"][0]

        self.assertEqual(result["is_technology"], True)
        self.assertEqual(result["is_hotspot"], True)
        self.assertEqual(result["region"], "international")
        self.assertEqual(result["summary_zh"], "abc")

    def test_merges_llm_semantics_without_changing_source_fields(self) -> None:
        item = NewsItem(
            "Original title", "https://source.example/article", "Source",
            datetime(2026, 8, 12, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")), "Source summary",
        )
        analyzed = NewsSemanticAgent({}, client=FakeClient()).analyze([item])[0]
        self.assertEqual(analyzed.url, item.url)
        self.assertEqual(analyzed.published_at, item.published_at)
        self.assertEqual(analyzed.region, "domestic")
        self.assertEqual(analyzed.summary_zh, "模型生成的客观摘要。")
