"""
Project : Telegram Automation Bot
Project ID : 035

Module Name : Telegram Connection Unit Tests

Purpose:
Validate Telegram bot connection behavior, including successful
verification, invalid tokens, unauthorized access, network failures,
and Telegram API errors.
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from src.services.telegram_service import TelegramService


class TestTelegramConnection(unittest.TestCase):
    """Test Telegram connection success and failure scenarios."""

    def setUp(self):
        """Initialize test dependencies."""
        self.service = TelegramService()
        self.valid_token = (
            "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
        )

    @staticmethod
    def create_mock_response(payload, status=200):
        """Create a mock HTTP response containing JSON data."""
        response = MagicMock()
        response.status = status
        response.read.return_value = json.dumps(
            payload
        ).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        return response

    def test_valid_token_connects_successfully(self):
        """A successful Telegram response should verify the bot."""
        payload = {
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "Test Bot",
                "username": "test_automation_bot",
            },
        }

        with patch(
            "src.services.telegram_service.urllib.request.urlopen",
            return_value=self.create_mock_response(payload),
        ):
            result = asyncio.run(
                self.service.verify_connection(self.valid_token)
            )

        self.assertTrue(result.success)
        self.assertIsNotNone(result.identity)

    def test_invalid_token_is_rejected(self):
        """A malformed token should be rejected safely."""
        result = asyncio.run(
            self.service.verify_connection("invalid-token")
        )

        self.assertFalse(result.success)

    def test_unauthorized_token_is_handled(self):
        """An HTTP 401 response should indicate connection failure."""
        error = HTTPError(
            url="https://api.telegram.org/",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

        with patch(
            "src.services.telegram_service.urllib.request.urlopen",
            side_effect=error,
        ):
            result = asyncio.run(
                self.service.verify_connection(self.valid_token)
            )

        self.assertFalse(result.success)

    def test_network_error_is_handled(self):
        """A network failure should not crash the application."""
        with patch(
            "src.services.telegram_service.urllib.request.urlopen",
            side_effect=URLError("Network unavailable"),
        ):
            result = asyncio.run(
                self.service.verify_connection(self.valid_token)
            )

        self.assertFalse(result.success)

    def test_telegram_api_error_is_handled(self):
        """A Telegram API error response should not report success."""
        payload = {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized",
        }

        with patch(
            "src.services.telegram_service.urllib.request.urlopen",
            return_value=self.create_mock_response(payload),
        ):
            result = asyncio.run(
                self.service.verify_connection(self.valid_token)
            )

        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()