from __future__ import annotations

from typing import Any

from hotspot_agent.intelligence.llm_client import OpenAICompatibleClient
from hotspot_agent.intelligence.validator import validate_results
from hotspot_agent.shared.schemas import AnalyzedNewsItem, NewsItem


class NewsSemanticAgent:
    def __init__(self, config: dict[str, Any], client: Any | None = None):
        self.config = config
        self.client = client or OpenAICompatibleClient(config)

    def analyze(self, items: list[NewsItem]) -> list[AnalyzedNewsItem]:
        inputs = [self._input(item, index) for index, item in enumerate(items)]
        payload = self._normalize_response(self.client.analyze(inputs))
        results = validate_results(payload, {item["item_id"] for item in inputs})
        analyzed: list[AnalyzedNewsItem] = []
        for item, input_item in zip(items, inputs):
            result = results[input_item["item_id"]]
            analyzed.append(AnalyzedNewsItem(
                item_id=input_item["item_id"], title=item.title, url=item.url,
                source_name=item.source_name, published_at=item.published_at, summary=item.summary,
                region=result.region, is_technology=result.is_technology, is_hotspot=result.is_hotspot,
                impact_score=result.impact_score, topic=result.topic,
                impact_factors=result.impact_factors, summary_zh=result.summary_zh,
            ))
        return analyzed

    @staticmethod
    def _normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
        """Map provider-specific field names into the internal V2 response schema."""
        normalized = dict(payload)
        results = normalized.get("results", [])
        normalized["results"] = []
        for value in results:
            item = dict(value)
            provider_is_tech = next(
                (
                    item[key]
                    for key in ("is_tech_news", "is_technology_news", "is_target", "is_tech_news_hotspot", "is_relevant")
                    if key in item
                ),
                None,
            )
            if "is_technology" not in item and provider_is_tech is not None:
                item["is_technology"] = provider_is_tech
            if "region" not in item and "category" in item:
                item["region"] = item["category"]
            if "summary_zh" not in item and "summary" in item:
                item["summary_zh"] = item["summary"]
            if "is_hotspot" not in item and provider_is_tech is not None:
                item["is_hotspot"] = provider_is_tech
            normalized["results"].append(item)
        return normalized

    @staticmethod
    def _input(item: NewsItem, index: int) -> dict[str, Any]:
        return {"item_id": f"news-{index:04d}", "title": item.title, "source_name": item.source_name, "published_at": item.published_at.isoformat(), "summary": item.summary}
