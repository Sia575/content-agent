from __future__ import annotations

import re
from datetime import datetime

from hotspot_agent.shared.schemas import NewsItem


class RuleFilter:
    def __init__(self, topic_keywords: list[str], domestic_keywords: list[str]):
        self.topic_keywords = tuple(keyword.casefold() for keyword in topic_keywords)
        self.domestic_keywords = tuple(keyword.casefold() for keyword in domestic_keywords)

    def filter_and_classify(
        self, items: list[NewsItem], window_start: datetime, window_end: datetime
    ) -> list[NewsItem]:
        retained: list[NewsItem] = []
        for item in items:
            if not window_start <= item.published_at <= window_end:
                continue
            searchable_text = f"{item.title} {item.summary}".casefold()
            if not any(keyword in searchable_text for keyword in self.topic_keywords):
                continue
            region = self._classify(item, searchable_text)
            retained.append(
                NewsItem(
                    title=item.title,
                    url=item.url,
                    source_name=item.source_name,
                    published_at=item.published_at,
                    summary=item.summary,
                    source_region=item.source_region,
                    region=region,
                )
            )
        return retained

    def _classify(self, item: NewsItem, text: str) -> str:
        if item.source_region == "domestic" or any(word in text for word in self.domestic_keywords):
            return "domestic"
        return "international"


def normalized_title(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", title.casefold())
