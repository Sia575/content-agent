from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dateutil import parser as date_parser

from hotspot_agent.shared.schemas import NewsItem

LOGGER = logging.getLogger(__name__)


class NewsApiCollector:
    """Optional NewsAPI adapter. It does nothing until NEWSAPI_KEY is configured."""

    def __init__(self, settings: dict[str, Any], timezone: ZoneInfo, timeout_seconds: int):
        self.settings = settings
        self.timezone = timezone
        self.timeout_seconds = timeout_seconds

    def collect(self, window_start: datetime, window_end: datetime) -> list[NewsItem]:
        api_key = os.getenv("NEWSAPI_KEY")
        if not self.settings.get("enabled") or not api_key:
            return []

        items: list[NewsItem] = []
        for query in self.settings.get("queries", []):
            try:
                response = httpx.get(
                    self.settings["endpoint"],
                    params={
                        "q": query,
                        "from": window_start.isoformat(),
                        "to": window_end.isoformat(),
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 100,
                        "apiKey": api_key,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                items.extend(self._parse_articles(response.json().get("articles", [])))
            except (httpx.HTTPError, ValueError):
                LOGGER.exception("Failed to collect NewsAPI query")
        return items

    def _parse_articles(self, articles: list[dict[str, Any]]) -> list[NewsItem]:
        parsed: list[NewsItem] = []
        for article in articles:
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            published = article.get("publishedAt")
            if not title or not url or not published:
                continue
            try:
                published_at = date_parser.parse(published).astimezone(self.timezone)
            except (TypeError, ValueError, OverflowError):
                continue
            parsed.append(
                NewsItem(
                    title=title,
                    url=url,
                    source_name=(article.get("source") or {}).get("name") or "NewsAPI",
                    published_at=published_at,
                    summary=(article.get("description") or "").strip(),
                )
            )
        return parsed
