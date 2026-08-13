from __future__ import annotations

import logging
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.collectors.rss import RSSCollector


TECHCRUNCH_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
<title>AI startup launches new chip</title>
<link>https://techcrunch.com/2026/08/12/ai-chip/</link>
<pubDate>Wed, 12 Aug 2026 04:30:00 +0000</pubDate>
<description>Company details an artificial intelligence processor.</description>
</item></channel></rss>"""

GOOGLE_NEWS_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
<title>AI&#36171;&#33021;&#33455;&#29255;&#30740;&#21457; - Example News</title>
<link>https://news.google.com/rss/articles/example?oc=5</link>
<pubDate>Wed, 12 Aug 2026 01:55:18 GMT</pubDate>
<description><![CDATA[<a href="https://news.google.com/rss/articles/example?oc=5">AI&#36171;&#33021;&#33455;&#29255;&#30740;&#21457;</a>]]></description>
</item></channel></rss>"""


class RSSCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.timezone = ZoneInfo("Asia/Shanghai")

    def _response(self, url: str, content: bytes) -> httpx.Response:
        return httpx.Response(200, content=content, request=httpx.Request("GET", url))

    @patch("hotspot_agent.collectors.rss.httpx.get")
    def test_parses_techcrunch_rss_response(self, get: unittest.mock.Mock) -> None:
        url = "https://techcrunch.com/feed/"
        get.return_value = self._response(url, TECHCRUNCH_RSS)

        with self.assertLogs("hotspot_agent.collectors.rss", logging.INFO) as logs:
            items = RSSCollector([{"name": "TechCrunch", "region": "international", "url": url}], self.timezone).collect()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "AI startup launches new chip")
        self.assertEqual(items[0].url, "https://techcrunch.com/2026/08/12/ai-chip/")
        self.assertEqual(items[0].summary, "Company details an artificial intelligence processor.")
        self.assertEqual(items[0].published_at.hour, 12)
        self.assertIn("http_status=200", logs.output[0])
        self.assertIn("bozo=False", logs.output[0])
        self.assertIn("entries=1", logs.output[0])
        self.assertTrue(get.call_args.kwargs["trust_env"])

    @patch("hotspot_agent.collectors.rss.httpx.get")
    def test_parses_google_news_rss_response(self, get: unittest.mock.Mock) -> None:
        url = "https://news.google.com/rss/search?q=AI"
        get.return_value = self._response(url, GOOGLE_NEWS_RSS)

        items = RSSCollector([{"name": "Google News", "region": "domestic", "url": url}], self.timezone).collect()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "AI赋能芯片研发 - Example News")
        self.assertEqual(items[0].url, "https://news.google.com/rss/articles/example?oc=5")
        self.assertIn("AI", items[0].summary)
        self.assertEqual(items[0].source_region, "domestic")

    @patch("hotspot_agent.collectors.rss.httpx.get")
    def test_request_failure_is_logged_and_returns_no_items(self, get: unittest.mock.Mock) -> None:
        url = "https://unavailable.example/feed"
        get.side_effect = httpx.ConnectError("DNS lookup failed", request=httpx.Request("GET", url))

        with self.assertLogs("hotspot_agent.collectors.rss", logging.WARNING) as logs:
            items = RSSCollector([{"name": "Unavailable", "region": "international", "url": url}], self.timezone).collect()

        self.assertEqual(items, [])
        self.assertIn("source=Unavailable", logs.output[0])
        self.assertIn("http_status=None", logs.output[0])
        self.assertIn("bozo=False", logs.output[0])
        self.assertIn("entries=0", logs.output[0])

    @patch("hotspot_agent.collectors.rss.httpx.get")
    def test_uses_environment_proxy_configuration_when_present(self, get: unittest.mock.Mock) -> None:
        url = "https://techcrunch.com/feed/"
        get.return_value = self._response(url, TECHCRUNCH_RSS)

        with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:7890", "HTTPS_PROXY": "http://127.0.0.1:7890"}):
            RSSCollector([{"name": "TechCrunch", "region": "international", "url": url}], self.timezone).collect()

        self.assertTrue(get.call_args.kwargs["trust_env"])


if __name__ == "__main__":
    unittest.main()
