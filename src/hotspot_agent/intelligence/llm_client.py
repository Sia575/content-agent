from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from hotspot_agent.intelligence.prompts import CONTENT_GEN_PROMPT, SYSTEM_PROMPT, TOPIC_JUDGE_PROMPT


LOGGER = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    def analyze(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        key = os.getenv(self.config.get("api_key_env", "LLM_API_KEY"))
        if not key:
            raise LLMClientError("LLM API key is not configured")
        base_url = os.getenv(self.config.get("base_url_env", "LLM_BASE_URL"), self.config.get("base_url", "https://api.openai.com/v1"))
        endpoint = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.config["model"],
            "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps({"items": items}, ensure_ascii=False)}],
            "response_format": {"type": "json_object"},
            "stream": True,
        }
        content_parts: list[str] = []
        raw_sse_lines: list[str] = []
        event_data_lines: list[str] = []

        def parse_event(data_lines: list[str]) -> bool:
            if not data_lines:
                return False
            # Providers may split one JSON payload across data lines, including inside a string.
            data = "".join(data_lines).strip()
            data_lines.clear()
            if data == "[DONE]":
                return True
            try:
                event = json.loads(data)
            except (TypeError, ValueError) as exc:
                LOGGER.debug(
                    "Ignoring non-JSON or malformed SSE event message=%s event_data=%s",
                    exc,
                    data,
                )
                return False
            if not isinstance(event, dict):
                LOGGER.debug("Ignoring non-object SSE event event_data=%s", data)
                return False
            if event.get("type") == "response.output_text.delta":
                piece = event.get("delta")
            else:
                delta = event.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content") if isinstance(delta, dict) else None
            if isinstance(piece, str) and piece:
                content_parts.append(piece)
            return False

        try:
            with httpx.stream(
                "POST",
                endpoint,
                headers={"Authorization": f"Bearer {key}"},
                json=body,
                timeout=self.config.get("timeout_seconds", 60),
                trust_env=True,
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    # Read the body before logging so streaming error responses are available.
                    response.read()
                    LOGGER.error(
                        "LLM HTTP error status_code=%s response_text=%s",
                        exc.response.status_code,
                        exc.response.text,
                    )
                    raise LLMClientError(f"LLM request or response failed: {exc}") from exc
                for line in response.iter_lines():
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")
                    raw_sse_lines.append(line)
                    if not line:
                        if parse_event(event_data_lines):
                            break
                        continue
                    if line.startswith("data:"):
                        event_data_lines.append(line[len("data:"):].lstrip())
                else:
                    # Some providers omit the final blank line; flush the last event at EOF.
                    parse_event(event_data_lines)
            raw_sse = "\n".join(raw_sse_lines)
            self._save_debug_response(raw_sse, len(raw_sse), suffix="-raw")
            content = "".join(content_parts)
            LOGGER.info("LLM streamed response raw_text=%s", content)
            self._save_debug_response(content, len(content), suffix="-content")
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                LOGGER.error(
                    "LLM response JSON parse failed position=%s message=%s raw_text=%s",
                    exc.pos,
                    exc.msg,
                    content,
                )
                raise
            LOGGER.info("LLM response JSON parse succeeded top_level_keys=%s", sorted(parsed.keys()))
            return parsed
        except LLMClientError:
            raise
        except json.JSONDecodeError as exc:
            # Preserve the received SSE text even when an event is incomplete.
            raw_text = "\n".join(raw_sse_lines)
            self._save_debug_response(raw_text, len(raw_text), suffix="-raw-partial")
            LOGGER.error("LLM stream parsing failed position=%s message=%s", exc.pos, exc.msg)
            raise LLMClientError(f"LLM request or response failed: {exc}") from exc

    def judge_topics(self, items: list[dict[str, Any]]) -> Any:
        user_prompt = TOPIC_JUDGE_PROMPT.replace(
            "{items_json}", json.dumps(items, ensure_ascii=False)
        )
        return self._request_json(TOPIC_JUDGE_PROMPT, user_prompt, "-topic-judge")

    def generate_content(
        self,
        topic: str,
        why_hot: str,
        target_audience: str,
        source_urls: list[str],
        platforms: list[str],
    ) -> Any:
        replacements = {
            "{topic}": topic,
            "{why_hot}": why_hot,
            "{target_audience}": target_audience,
            "{source_urls}": json.dumps(source_urls, ensure_ascii=False),
            "{platforms}": json.dumps(platforms, ensure_ascii=False),
        }
        user_prompt = CONTENT_GEN_PROMPT
        for placeholder, value in replacements.items():
            user_prompt = user_prompt.replace(placeholder, value)
        return self._request_json(CONTENT_GEN_PROMPT, user_prompt, "-content-gen")

    def _request_json(self, system_prompt: str, user_prompt: str, suffix: str) -> Any:
        key = os.getenv(self.config.get("api_key_env", "LLM_API_KEY"))
        if not key:
            raise LLMClientError("LLM API key is not configured")
        base_url = os.getenv(
            self.config.get("base_url_env", "LLM_BASE_URL"),
            self.config.get("base_url", "https://api.openai.com/v1"),
        )
        endpoint = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.config["model"],
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
        }
        content_parts: list[str] = []
        raw_sse_lines: list[str] = []
        event_data_lines: list[str] = []

        def parse_event(data_lines: list[str]) -> bool:
            if not data_lines:
                return False
            data = "".join(data_lines).strip()
            data_lines.clear()
            if data == "[DONE]":
                return True
            try:
                event = json.loads(data)
            except (TypeError, ValueError) as exc:
                LOGGER.debug(
                    "Ignoring non-JSON or malformed SSE event message=%s event_data=%s",
                    exc,
                    data,
                )
                return False
            if not isinstance(event, dict):
                LOGGER.debug("Ignoring non-object SSE event event_data=%s", data)
                return False
            if event.get("type") == "response.output_text.delta":
                piece = event.get("delta")
            else:
                delta = event.get("choices", [{}])[0].get("delta", {})
                piece = delta.get("content") if isinstance(delta, dict) else None
            if isinstance(piece, str) and piece:
                content_parts.append(piece)
            return False

        try:
            with httpx.stream(
                "POST",
                endpoint,
                headers={"Authorization": f"Bearer {key}"},
                json=body,
                timeout=self.config.get("timeout_seconds", 60),
                trust_env=True,
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    response.read()
                    LOGGER.error(
                        "LLM HTTP error status_code=%s response_text=%s",
                        exc.response.status_code,
                        exc.response.text,
                    )
                    raise LLMClientError(f"LLM request or response failed: {exc}") from exc
                for line in response.iter_lines():
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")
                    raw_sse_lines.append(line)
                    if not line:
                        if parse_event(event_data_lines):
                            break
                        continue
                    if line.startswith("data:"):
                        event_data_lines.append(line[len("data:"):].lstrip())
                else:
                    parse_event(event_data_lines)
            raw_sse = "\n".join(raw_sse_lines)
            self._save_debug_response(raw_sse, len(raw_sse), suffix=f"{suffix}-raw")
            content = "".join(content_parts)
            LOGGER.info("LLM streamed response raw_text=%s", content)
            self._save_debug_response(content, len(content), suffix=f"{suffix}-content")
            parsed = json.loads(content)
            LOGGER.info("LLM response JSON parse succeeded type=%s", type(parsed).__name__)
            return parsed
        except LLMClientError:
            raise
        except json.JSONDecodeError as exc:
            raw_text = "\n".join(raw_sse_lines)
            self._save_debug_response(raw_text, len(raw_text), suffix=f"{suffix}-raw-partial")
            LOGGER.error("LLM stream parsing failed position=%s message=%s", exc.pos, exc.msg)
            raise LLMClientError(f"LLM request or response failed: {exc}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raw_text = "\n".join(raw_sse_lines)
            self._save_debug_response(raw_text, len(raw_text), suffix=f"{suffix}-raw-partial")
            raise LLMClientError(f"LLM request or response failed: {exc}") from exc
    def _save_debug_response(self, content: str, length: int, suffix: str) -> Path:
        response_path = Path(self.config.get("debug_output_dir", "output")) / (
            f"llm-response-{datetime.now():%Y-%m-%d-%H%M%S%f}{suffix}.txt"
        )
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_text(content, encoding="utf-8")
        LOGGER.info("LLM streamed response saved path=%s length=%s", response_path, length)
        return response_path
