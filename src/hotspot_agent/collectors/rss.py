from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import httpx
from dateutil import parser as date_parser

from hotspot_agent.shared.schemas import NewsItem

LOGGER = logging.getLogger(__name__)


class RSSCollector:
    def __init__(self, sources: list[dict[str, Any]], timezone: ZoneInfo, timeout_seconds: int = 20):
        self.sources = sources
        self.timezone = timezone
        self.timeout_seconds = timeout_seconds

    def collect(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        for source in self.sources:
            try:
                response = httpx.get(
                    source["url"],
                    follow_redirects=True,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": "HotspotAI-Agent/0.1 (+RSS collector)"},
                    # httpx reads HTTP_PROXY/HTTPS_PROXY (and lowercase variants) from the environment.
                    trust_env=True,
                )
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                LOGGER.info(
                    "RSS fetched source=%s http_status=%s final_url=%s bozo=%s "
                    "bozo_exception=%r entries=%s",
                    source["name"],
                    response.status_code,
                    response.url,
                    feed.bozo,
                    getattr(feed, "bozo_exception", None),
                    len(feed.entries),
                )
                items.extend(self._parse_entries(feed.entries, source))
            except httpx.HTTPError as exc:
                LOGGER.warning(
                    "RSS request failed source=%s http_status=%s final_url=%s bozo=%s "
                    "bozo_exception=%r entries=%s error=%r",
                    source["name"],
                    getattr(getattr(exc, "response", None), "status_code", None),
                    getattr(getattr(exc, "response", None), "url", source["url"]),
                    False,
                    None,
                    0,
                    exc,
                )
            except Exception:
                LOGGER.exception("RSS processing failed source=%s", source["name"])
        return items

    def _parse_entries(self, entries: list[Any], source: dict[str, Any]) -> list[NewsItem]:
        parsed: list[NewsItem] = []
        for entry in entries:
            published = self._parse_published(entry)
            url = str(entry.get("link", "")).strip()
            title = str(entry.get("title", "")).strip()
            if not published or not url or not title:
                continue
            parsed.append(
                NewsItem(
                    title=title,
                    url=url,
                    source_name=source["name"],
                    published_at=published,
                    summary=str(entry.get("summary", "")).strip(),
                    source_region=source.get("region"),
                )
            )
        return parsed

    def _parse_published(self, entry: Any) -> datetime | None:
        raw_date = entry.get("published") or entry.get("updated")
        if not raw_date:
            return None
        try:
            parsed = date_parser.parse(raw_date)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=self.timezone)
            return parsed.astimezone(self.timezone)
        except (TypeError, ValueError, OverflowError):
            return None
