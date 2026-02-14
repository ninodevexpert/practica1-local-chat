from __future__ import annotations

import io
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from src.lmstudio_client import LMStudioAPIError, LMStudioClient


def _mock_response_with_body(body: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = body

    context = MagicMock()
    context.__enter__.return_value = response
    context.__exit__.return_value = None
    return context


class LMStudioClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = LMStudioClient()

    @patch("src.lmstudio_client.urlopen")
    def test_list_models_parses_data_ids(self, urlopen_mock: MagicMock) -> None:
        urlopen_mock.return_value = _mock_response_with_body(
            b'{"data":[{"id":"model-a"},{"id":"model-b"}]}'
        )

        models = self.client.list_models(base_url="http://127.0.0.1:1234/v1")

        self.assertEqual(models, ["model-a", "model-b"])

    @patch("src.lmstudio_client.urlopen")
    def test_chat_completion_parses_first_choice_message(self, urlopen_mock: MagicMock) -> None:
        urlopen_mock.return_value = _mock_response_with_body(
            b'{"choices":[{"message":{"role":"assistant","content":"hola"}}]}'
        )

        answer = self.client.chat_completion(
            base_url="http://127.0.0.1:1234/v1",
            model="model-a",
            messages=[{"role": "user", "content": "saluda"}],
            temperature=0.7,
            max_tokens=128,
            timeout_seconds=30.0,
        )

        self.assertEqual(answer, "hola")

    @patch("src.lmstudio_client.urlopen")
    def test_http_error_is_raised_with_readable_message(self, urlopen_mock: MagicMock) -> None:
        http_error = HTTPError(
            url="http://127.0.0.1:1234/v1/models",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"boom"}}'),
        )
        urlopen_mock.side_effect = http_error

        with self.assertRaises(LMStudioAPIError) as context:
            self.client.list_models(base_url="http://127.0.0.1:1234/v1")

        self.assertIn("HTTP 500", str(context.exception))
        self.assertIn("boom", str(context.exception))

    @patch("src.lmstudio_client.urlopen")
    def test_timeout_error_is_handled(self, urlopen_mock: MagicMock) -> None:
        urlopen_mock.side_effect = URLError(socket.timeout("timed out"))

        with self.assertRaises(LMStudioAPIError) as context:
            self.client.list_models(base_url="http://127.0.0.1:1234/v1")

        self.assertIn("Tiempo de espera agotado", str(context.exception))


if __name__ == "__main__":
    unittest.main()
