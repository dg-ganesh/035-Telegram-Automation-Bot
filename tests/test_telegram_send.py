
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Message Delivery Tests
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from src.services.telegram_service import (
    TelegramSendResult,
    TelegramService,
)
from src.ui.main_window import MainWindow


class TestTelegramMessageDelivery(unittest.IsolatedAsyncioTestCase):
    """Test message delivery without real Telegram API requests."""

    def setUp(self) -> None:
        self.service = TelegramService(
            request_timeout_seconds=5
        )

    async def test_successful_single_recipient_send(self) -> None:
        """A successful API result should be reported as success."""
        expected = TelegramSendResult(
            success=True,
            chat_id="123456789",
            message="Message sent successfully.",
        )

        with patch.object(
            self.service,
            "_request_send_message",
            return_value=expected,
        ):
            result = await self.service.send_message(
                "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                "123456789",
                "Test message",
            )

        self.assertTrue(result.success)
        self.assertEqual(result.chat_id, "123456789")

    async def test_multiple_recipients_have_independent_results(
        self,
    ) -> None:
        """One recipient's failure must not hide another's success."""
        success_result = TelegramSendResult(
            success=True,
            chat_id="111111111",
            message="Message sent successfully.",
        )
        failure_result = TelegramSendResult(
            success=False,
            chat_id="222222222",
            message="Recipient could not be reached.",
        )

        with patch.object(
            self.service,
            "send_message",
            new_callable=AsyncMock,
            side_effect=[success_result, failure_result],
        ) as mocked_send:
            results = await self.service.send_messages(
                "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                ["111111111", "222222222"],
                "Test message",
            )

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)
        self.assertEqual(mocked_send.await_count, 2)

    async def test_invalid_token_is_rejected(self) -> None:
        """A malformed token should fail before an API request."""
        with patch.object(
            self.service,
            "_request_send_message",
        ) as mocked_request:
            result = await self.service.send_message(
                "not-a-valid-token",
                "123456789",
                "Test message",
            )

        self.assertFalse(result.success)
        mocked_request.assert_not_called()

    async def test_invalid_chat_id_is_rejected(self) -> None:
        """A non-numeric chat ID should not be sent to Telegram."""
        result = await self.service.send_message(
            "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            "not-a-chat-id",
            "Test message",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.chat_id, "not-a-chat-id")

    async def test_empty_message_is_rejected(self) -> None:
        """An empty message should fail validation."""
        result = await self.service.send_message(
            "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            "123456789",
            "",
        )

        self.assertFalse(result.success)

    async def test_message_over_limit_is_rejected(self) -> None:
        """Messages longer than Telegram's limit should be rejected."""
        long_message = (
            "A" * (TelegramService.MAX_MESSAGE_LENGTH + 1)
        )

        result = await self.service.send_message(
            "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            "123456789",
            long_message,
        )

        self.assertFalse(result.success)


class TestRecipientParsing(unittest.TestCase):
    """Test the GUI's recipient ID parsing rules."""

    def test_comma_separated_ids(self) -> None:
        chat_ids, error = MainWindow._parse_chat_ids(
            "111111111,222222222,333333333"
        )

        self.assertIsNone(error)
        self.assertEqual(
            chat_ids,
            ["111111111", "222222222", "333333333"],
        )

    def test_newline_separated_ids(self) -> None:
        chat_ids, error = MainWindow._parse_chat_ids(
            "111111111\n222222222"
        )

        self.assertIsNone(error)
        self.assertEqual(
            chat_ids,
            ["111111111", "222222222"],
        )

    def test_duplicate_ids_are_removed(self) -> None:
        chat_ids, error = MainWindow._parse_chat_ids(
            "111111111,222222222,111111111"
        )

        self.assertIsNone(error)
        self.assertEqual(
            chat_ids,
            ["111111111", "222222222"],
        )

    def test_invalid_id_is_rejected(self) -> None:
        chat_ids, error = MainWindow._parse_chat_ids(
            "111111111,abc"
        )

        self.assertEqual(chat_ids, [])
        self.assertIsNotNone(error)

    def test_empty_recipient_list_is_rejected(self) -> None:
        chat_ids, error = MainWindow._parse_chat_ids("  \n  ")

        self.assertEqual(chat_ids, [])
        self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
