from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotspot_agent.intelligence.llm_client import OpenAICompatibleClient


class LLMClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "model": "test-model",
            "api_key_env": "TEST_LLM_API_KEY",
            "base_url_env": "TEST_LLM_BASE_URL",
        }

    def test_streams_and_concatenates_delta_content(self) -> None:
        response = MagicMock()
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"{\\"results\\":["}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"{\\"item_id\\":\\"news-0000\\"}"}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"]}"}}]}',
            "",
            "data: [DONE]",
            "",
        ]
        stream_context = MagicMock()
        stream_context.__enter__.return_value = response
        stream_context.__exit__.return_value = False

        with patch.dict(os.environ, {"TEST_LLM_API_KEY": "test-key", "TEST_LLM_BASE_URL": "https://llm.example/v1"}), patch(
            "hotspot_agent.intelligence.llm_client.httpx.stream", return_value=stream_context
        ) as stream:
            result = OpenAICompatibleClient(self.config).analyze([])

        self.assertEqual(result, {"results": [{"item_id": "news-0000"}]})
        self.assertTrue(stream.call_args.kwargs["json"]["stream"])
        self.assertEqual(stream.call_args.args[:2], ("POST", "https://llm.example/v1/chat/completions"))

    def test_http_status_error_logs_status_and_body(self) -> None:
        request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
        response = httpx.Response(400, content=b'{"error":"bad request"}', request=request)
        stream_context = MagicMock()
        stream_context.__enter__.return_value = response
        stream_context.__exit__.return_value = False

        with patch.dict(os.environ, {"TEST_LLM_API_KEY": "test-key", "TEST_LLM_BASE_URL": "https://llm.example/v1"}), patch(
            "hotspot_agent.intelligence.llm_client.httpx.stream", return_value=stream_context
        ), self.assertLogs("hotspot_agent.intelligence.llm_client", "ERROR") as logs:
            with self.assertRaises(Exception):
                OpenAICompatibleClient(self.config).analyze([])

        self.assertIn("status_code=400", logs.output[0])
        self.assertIn('{"error":"bad request"}', logs.output[0])

    def test_accumulates_multiple_data_lines_until_blank_event_separator(self) -> None:
        response = MagicMock()
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"{\\"results\\":["}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"{\\"item_id\\":\\"news-0000\\"}"}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"]}"}}]}',
            "",
            "data: [DONE]",
            "",
        ]
        stream_context = MagicMock()
        stream_context.__enter__.return_value = response
        stream_context.__exit__.return_value = False

        with patch.dict(os.environ, {"TEST_LLM_API_KEY": "test-key", "TEST_LLM_BASE_URL": "https://llm.example/v1"}), patch(
            "hotspot_agent.intelligence.llm_client.httpx.stream", return_value=stream_context
        ):
            result = OpenAICompatibleClient(self.config).analyze([])

        self.assertEqual(result, {"results": [{"item_id": "news-0000"}]})

    def test_extracts_responses_api_output_text_delta(self) -> None:
        response = MagicMock()
        response.iter_lines.return_value = [
            'event: response.output_text.delta',
            'data: {"type":"response.output_text.delta","delta":"{\\"results\\":["}',
            "",
            'event: response.output_text.delta',
            'data: {"type":"response.output_text.delta","delta":"{\\"item_id\\":\\"news-0000\\"}"}',
            "",
            'data: {"type":"response.output_text.delta","delta":"]}"}',
            "",
            "data: [DONE]",
            "",
        ]
        stream_context = MagicMock()
        stream_context.__enter__.return_value = response
        stream_context.__exit__.return_value = False

        with patch.dict(os.environ, {"TEST_LLM_API_KEY": "test-key", "TEST_LLM_BASE_URL": "https://llm.example/v1"}), patch(
            "hotspot_agent.intelligence.llm_client.httpx.stream", return_value=stream_context
        ):
            result = OpenAICompatibleClient(self.config).analyze([])

        self.assertEqual(result, {"results": [{"item_id": "news-0000"}]})


if __name__ == "__main__":
    unittest.main()
