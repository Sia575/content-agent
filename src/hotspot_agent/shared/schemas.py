from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    """A normalized source item used throughout the daily pipeline."""

    title: str
    url: str
    source_name: str
    published_at: datetime
    summary: str = ""
    source_region: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class AnalyzedNewsItem:
    """A source item enriched by the semantic LLM, with source fields preserved."""

    item_id: str
    title: str
    url: str
    source_name: str
    published_at: datetime
    summary: str
    region: str
    is_technology: bool
    is_hotspot: bool
    impact_score: int | None
    topic: str | None = None
    impact_factors: tuple[str, ...] = ()
    summary_zh: str | None = None


@dataclass(frozen=True)
class DailyReport:
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    international: tuple[NewsItem | AnalyzedNewsItem, ...]
    domestic: tuple[NewsItem | AnalyzedNewsItem, ...]


@dataclass(frozen=True)
class TrendItem:
    item_id: str
    title: str
    url: str
    source_type: str
    rank: int
    heat_value: float | int | str
    collected_at: datetime
    raw_metrics: dict[str, int | None] | None = None


@dataclass(frozen=True)
class TopicJudgment:
    topic: str
    why_hot: str
    spread_score: int | float
    target_audience: str
    suitable_platforms: tuple[str, ...]
    risk_note: str


@dataclass(frozen=True)
class PlatformContent:
    platform: str
    title: str
    body: str
    tags: tuple[str, ...]
    source_urls: tuple[str, ...]
