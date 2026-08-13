from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from hotspot_agent.shared.schemas import TrendItem


LOGGER = logging.getLogger(__name__)

TOPSTORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
DEFAULT_TIMEOUT_SECONDS = 10
TOP_STORIES_LIMIT = 30
REQUEST_INTERVAL_SECONDS = 0.1


def fetch(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> list[TrendItem]:
    try:
        response = requests.get(TOPSTORIES_URL, timeout=timeout_seconds)
        response.raise_for_status()
        story_ids = response.json()
        if not isinstance(story_ids, list):
            raise ValueError("HN topstories response must be a list")
    except (requests.RequestException, ValueError, TypeError) as exc:
        LOGGER.warning("Failed to fetch Hacker News top stories: %s", exc)
        return []

    collected_at = datetime.now(timezone.utc)
    items: list[TrendItem] = []
    for rank, item_id in enumerate(story_ids[:TOP_STORIES_LIMIT], start=1):
        try:
            response = requests.get(
                ITEM_URL_TEMPLATE.format(item_id=item_id),
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            item = response.json()
            if not isinstance(item, dict):
                raise ValueError("HN item response must be an object")
            parsed = _to_trend_item(item, rank, collected_at)
            if parsed is not None:
                items.append(parsed)
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            LOGGER.warning("Failed to fetch Hacker News item id=%s: %s", item_id, exc)
        finally:
            time.sleep(REQUEST_INTERVAL_SECONDS)
    return items


def _to_trend_item(item: dict[str, Any], rank: int, collected_at: datetime) -> TrendItem | None:
    item_id = item.get("id")
    title = str(item.get("title") or "").strip()
    if item_id is None or not title:
        return None
    url = str(item.get("url") or f"https://news.ycombinator.com/item?id={item_id}").strip()
    score = item.get("score")
    descendants = item.get("descendants")
    if not isinstance(score, int):
        score = None
    if not isinstance(descendants, int):
        descendants = None
    return TrendItem(
        item_id=f"hn_{item_id}",
        title=title,
        url=url,
        source_type="hackernews",
        rank=rank,
        heat_value=score if score is not None else 0,
        collected_at=collected_at,
        raw_metrics={"score": score, "descendants": descendants},
    )
