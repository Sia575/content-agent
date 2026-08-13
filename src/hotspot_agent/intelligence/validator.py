from __future__ import annotations

import logging
from typing import Any

from hotspot_agent.intelligence.schemas import SemanticResult, result_from_dict


LOGGER = logging.getLogger(__name__)


def validate_results(payload: dict[str, Any], expected_ids: set[str]) -> dict[str, SemanticResult]:
    values = payload.get("results")
    if not isinstance(values, list):
        LOGGER.error("LLM validation failed: missing or invalid results field; payload_keys=%s", sorted(payload.keys()))
        raise ValueError("LLM response must contain a results list")
    parsed: dict[str, SemanticResult] = {}
    for index, value in enumerate(values):
        try:
            result = result_from_dict(value)
        except ValueError as exc:
            if isinstance(value, dict):
                required = {"item_id", "is_technology", "is_hotspot", "region", "summary_zh", "impact_score"}
                LOGGER.error(
                    "LLM validation field mismatch result_index=%s missing_fields=%s present_fields=%s error=%s",
                    index,
                    sorted(required - value.keys()),
                    sorted(value.keys()),
                    exc,
                )
            else:
                LOGGER.error("LLM validation invalid result result_index=%s type=%s error=%s", index, type(value).__name__, exc)
            raise
        if result.item_id not in expected_ids:
            LOGGER.error("LLM validation unknown item_id=%s expected_count=%s", result.item_id, len(expected_ids))
            raise ValueError(f"Unknown item_id from LLM: {result.item_id}")
        if result.item_id in parsed:
            LOGGER.error("LLM validation duplicate item_id=%s", result.item_id)
            raise ValueError(f"Duplicate item_id from LLM: {result.item_id}")
        parsed[result.item_id] = result
    if set(parsed) != expected_ids:
        LOGGER.error(
            "LLM validation item_id mismatch missing_ids=%s extra_ids=%s",
            sorted(expected_ids - set(parsed)),
            sorted(set(parsed) - expected_ids),
        )
        raise ValueError("LLM response does not contain exactly one result per input item")
    return parsed
