from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from hotspot_agent.processing.filtering import normalized_title
from hotspot_agent.shared.schemas import NewsItem


class Deduplicator:
    def deduplicate(self, items: list[NewsItem]) -> list[NewsItem]:
        # Sorting makes the selected representative deterministic: newest item wins.
        sorted_items = sorted(items, key=lambda item: item.published_at, reverse=True)
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        unique: list[NewsItem] = []
        for item in sorted_items:
            canonical_url = self._canonical_url(item.url)
            title_key = normalized_title(item.title)
            if canonical_url in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(canonical_url)
            seen_titles.add(title_key)
            unique.append(item)
        return unique

    @staticmethod
    def _canonical_url(url: str) -> str:
        split = urlsplit(url)
        query = urlencode(
            [(key, value) for key, value in parse_qsl(split.query) if not key.startswith("utm_")]
        )
        return urlunsplit((split.scheme, split.netloc, split.path.rstrip("/"), query, ""))
