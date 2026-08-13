# MVP architecture

`DailyRunner` orchestrates a deterministic pipeline:

1. `RSSCollector` downloads configured feeds with `httpx`, then parses their response bytes with `feedparser`; `NewsApiCollector` is enabled only when `NEWSAPI_KEY` is present.
2. `RuleFilter` retains technology-topic matches in the configured 24-hour window and classifies domestic versus international.
3. `Deduplicator` normalizes URLs and titles, then retains one representative per matching title/URL.
4. `MarkdownRenderer` creates a Chinese report with a fixed factual template.

The MVP intentionally does not crawl web pages, perform semantic clustering or fact verification, or deliver notifications.
