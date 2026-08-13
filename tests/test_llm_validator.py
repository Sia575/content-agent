from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.intelligence.validator import validate_results


class LLMValidatorTests(unittest.TestCase):
    def _result(self, item_id="news-0000", **overrides):
        value = {
            "item_id": item_id,
            "is_technology": True,
            "is_hotspot": True,
            "region": "international",
            "summary_zh": "来源报道了一项科技事件。",
            "impact_score": 80,
            "topic": "AI",
            "impact_factors": ["core_technology"],
        }
        value.update(overrides)
        return value

    def test_validates_structured_results(self) -> None:
        result = validate_results({"results": [self._result()]}, {"news-0000"})["news-0000"]
        self.assertEqual(result.impact_score, 80)

    def test_rejects_invalid_region_and_score(self) -> None:
        with self.assertRaises(ValueError):
            validate_results({"results": [self._result(region="local")]}, {"news-0000"})
        with self.assertRaises(ValueError):
            validate_results({"results": [self._result(impact_score=101)]}, {"news-0000"})

    def test_requires_exact_input_ids(self) -> None:
        with self.assertRaises(ValueError):
            validate_results({"results": [self._result(item_id="unknown")]}, {"news-0000"})
