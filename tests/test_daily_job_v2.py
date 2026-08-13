from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.scheduler.daily_job import DailyRunner
from hotspot_agent.shared.schemas import NewsItem


class DailyJobV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = NewsItem(
            "AI chip launch", "https://source.example/a", "Source",
            datetime(2026, 8, 12, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")), "AI chip summary",
        )
        self.settings = {
            "app": {"timezone": "Asia/Shanghai", "output_dir": "output", "max_items_per_section": 8},
            "collection": {"lookback_hours": 24}, "llm": {"enabled": True, "model": "gpt-5.6-luna"},
        }

    def test_llm_failure_falls_back_to_original_items(self) -> None:
        with patch("hotspot_agent.scheduler.daily_job.NewsSemanticAgent") as agent:
            agent.return_value.analyze.side_effect = RuntimeError("service unavailable")
            result = DailyRunner(self.settings)._analyze([self.item])
        self.assertEqual(result.items, [self.item])
        self.assertEqual(result.analysis_mode, "fallback")
        self.assertEqual(result.fallback_reason, "service unavailable")

    def test_build_report_sorts_by_impact_and_limits_each_region(self) -> None:
        from hotspot_agent.shared.schemas import AnalyzedNewsItem
        items = [
            AnalyzedNewsItem("1", "one", "https://1", "S", self.item.published_at, "", "international", True, True, 20),
            AnalyzedNewsItem("2", "two", "https://2", "S", self.item.published_at, "", "international", True, True, 90),
        ]
        report = DailyRunner._build_report(items, self.item.published_at, self.item.published_at, 1)
        self.assertEqual(report.international[0].item_id, "2")

    def test_json_intermediate_file_serializes_datetime_and_tuple(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analyzed.json"
            DailyRunner._write_json(path, [self.item])
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data[0]["url"], self.item.url)
        self.assertIn("2026-08-12", data[0]["published_at"])

    def test_analyzed_json_includes_metadata_and_items(self) -> None:
        outcome = DailyRunner(self.settings)._analyze([])
        generated_at = datetime(2026, 8, 12, 16, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analyzed.json"
            DailyRunner(self.settings)._write_analyzed_json(path, outcome, generated_at)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["metadata"]["analysis_mode"], "llm")
        self.assertEqual(data["metadata"]["llm_model"], "gpt-5.6-luna")
        self.assertEqual(data["metadata"]["generated_at"], "2026-08-12T16:00:00+08:00")
        self.assertEqual(data["items"], [])

    def test_copy_latest_copies_generated_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "hotspot-daily-2026-08-12.md"
            target = Path(directory) / "latest-report.md"
            source.write_text("# Report\n", encoding="utf-8")
            DailyRunner._copy_latest(source, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "# Report\n")


if __name__ == "__main__":
    unittest.main()
