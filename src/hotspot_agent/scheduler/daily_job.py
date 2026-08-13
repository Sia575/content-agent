from __future__ import annotations

import logging
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hotspot_agent.collectors.newsapi import NewsApiCollector
from hotspot_agent.collectors.rss import RSSCollector
from hotspot_agent.intelligence.news_semantic_agent import NewsSemanticAgent
from hotspot_agent.processing.deduplication import Deduplicator
from hotspot_agent.processing.filtering import RuleFilter
from hotspot_agent.publishing.markdown import MarkdownRenderer
from hotspot_agent.shared.schemas import DailyReport, NewsItem
from hotspot_agent.shared.time_utils import get_timezone, lookback_window, now_in_timezone

LOGGER = logging.getLogger(__name__)


@dataclass
class DailyRunner:
    settings: dict[str, Any]

    def run(self) -> Path:
        app = self.settings["app"]
        collection = self.settings["collection"]
        filtering = self.settings["filtering"]
        timezone = get_timezone(app["timezone"])
        window_end = now_in_timezone(timezone)
        window_start, window_end = lookback_window(window_end, collection["lookback_hours"])

        raw_items = RSSCollector(
            collection["rss_sources"], timezone, collection["request_timeout_seconds"]
        ).collect()
        raw_items.extend(
            NewsApiCollector(
                collection["newsapi"], timezone, collection["request_timeout_seconds"]
            ).collect(window_start, window_end)
        )
        candidates = RuleFilter(
            filtering["topic_keywords"], filtering["domestic_keywords"]
        ).filter_and_classify(raw_items, window_start, window_end)
        items = Deduplicator().deduplicate(candidates)
        output_dir = Path(app["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(output_dir / f"raw-news-{window_end:%Y-%m-%d}.json", items)
        analysis = self._analyze(items)
        analyzed_path = output_dir / f"analyzed-news-{window_end:%Y-%m-%d}.json"
        self._write_analyzed_json(analyzed_path, analysis, window_end)
        self._copy_latest(analyzed_path, output_dir / "latest-analysis.json")
        analyzed_items = analysis.items
        report = self._build_report(analyzed_items, window_start, window_end, app["max_items_per_section"])
        renderer = MarkdownRenderer()
        output_path = renderer.write(renderer.render(report), output_dir, window_end)
        self._copy_latest(output_path, output_dir / "latest-report.md")
        LOGGER.info("Wrote report: %s", output_path)
        return output_path

    def _analyze(self, items: list[NewsItem]) -> AnalysisOutcome:
        config = self.settings.get("llm", {})
        if not config.get("enabled", False):
            return AnalysisOutcome(items=items, analysis_mode="fallback", fallback_reason="LLM disabled")
        if not items:
            return AnalysisOutcome(items=items, analysis_mode="llm")
        try:
            analyzed = NewsSemanticAgent(config).analyze(items)
            return AnalysisOutcome(
                items=[item for item in analyzed if item.is_technology and item.is_hotspot],
                analysis_mode="llm",
            )
        except Exception as exc:
            LOGGER.exception("LLM analysis failed; falling back to rule-based report")
            return AnalysisOutcome(items=items, analysis_mode="fallback", fallback_reason=str(exc))

    @staticmethod
    def _write_json(path: Path, items: list[Any]) -> None:
        path.write_text(json.dumps([DailyRunner._encode_item(item) for item in items], ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _copy_latest(source: Path, target: Path) -> None:
        shutil.copy(source, target)

    def _write_analyzed_json(self, path: Path, analysis: AnalysisOutcome, generated_at) -> None:
        llm_config = self.settings.get("llm", {})
        metadata = {
            "analysis_mode": analysis.analysis_mode,
            "generated_at": generated_at.isoformat(),
            "llm_model": llm_config.get("model"),
        }
        if analysis.fallback_reason:
            metadata["fallback_reason"] = analysis.fallback_reason
        payload = {
            "metadata": metadata,
            "items": [self._encode_item(item) for item in analysis.items],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _encode_item(item: Any) -> dict[str, Any]:
        value = dict(item.__dict__)
        value["published_at"] = item.published_at.isoformat()
        if isinstance(value.get("impact_factors"), tuple):
            value["impact_factors"] = list(value["impact_factors"])
        return value

    @staticmethod
    def _build_report(
        items: list[NewsItem | Any], window_start, window_end, limit: int
    ) -> DailyReport:
        ordered = sorted(
            items,
            key=lambda item: (getattr(item, "impact_score", None) if getattr(item, "impact_score", None) is not None else -1, item.published_at),
            reverse=True,
        )
        international = tuple(item for item in ordered if item.region == "international")[:limit]
        domestic = tuple(item for item in ordered if item.region == "domestic")[:limit]
        return DailyReport(window_end, window_start, window_end, international, domestic)


@dataclass(frozen=True)
class AnalysisOutcome:
    items: list[NewsItem | Any]
    analysis_mode: str
    fallback_reason: str | None = None
