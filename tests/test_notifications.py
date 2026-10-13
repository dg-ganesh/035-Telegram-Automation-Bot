
"""
Project : Telegram Automation Bot
Project ID : 035

Notification Service Unit Tests
"""

import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from src.models.delivery_record import DeliveryRecord, DeliveryStatus
from src.models.recipient import Recipient
from src.services.notification_service import NotificationService
from src.services.recipient_service import RecipientService
from src.services.telegram_service import TelegramService


class TestNotificationService(unittest.IsolatedAsyncioTestCase):
    """Tests for notification delivery orchestration."""

    def setUp(self):
        self.recipient_service = RecipientService()

        self.active_recipient = Recipient(
            chat_id="123456789",
            name="Finance Team",
        )

        self.inactive_recipient = Recipient(
            chat_id="987654321",
            name="Inactive Team",
            is_active=False,
        )

        self.recipient_service.add_recipient(
            self.active_recipient
        )
        self.recipient_service.add_recipient(
            self.inactive_recipient
        )

        # Create a real TelegramService instance without running its
        # constructor. Its network operation is mocked in each test.
        self.telegram_service = object.__new__(TelegramService)

        self.service = NotificationService(
            telegram_service=self.telegram_service,
            recipient_service=self.recipient_service,
        )

    async def test_successful_delivery(self):
        telegram_result = SimpleNamespace(
            success=True,
            chat_id="123456789",
            message="Message sent successfully",
        )

        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            return_value=telegram_result,
            create=True,
        ):
            record = await self.service.send_to_recipient(
                token="test-token",
                recipient=self.active_recipient,
                message="Test notification",
            )

        self.assertIsInstance(record, DeliveryRecord)
        self.assertEqual(record.chat_id, "123456789")
        self.assertEqual(record.status, DeliveryStatus.SUCCESS)

    async def test_failed_delivery_result(self):
        telegram_result = SimpleNamespace(
            success=False,
            chat_id="123456789",
            message="Telegram rejected the message",
        )

        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            return_value=telegram_result,
            create=True,
        ):
            record = await self.service.send_to_recipient(
                token="test-token",
                recipient=self.active_recipient,
                message="Test notification",
            )

        self.assertEqual(record.status, DeliveryStatus.FAILED)
        self.assertTrue(record.error_message)

    async def test_inactive_recipient_is_not_sent_to(self):
        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            create=True,
        ) as send_mock:
            with self.assertRaises(ValueError):
                await self.service.send_to_recipient(
                    token="test-token",
                    recipient=self.inactive_recipient,
                    message="Test notification",
                )

        send_mock.assert_not_awaited()

    async def test_empty_message_is_rejected(self):
        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            create=True,
        ) as send_mock:
            with self.assertRaises(ValueError):
                await self.service.send_to_recipient(
                    token="test-token",
                    recipient=self.active_recipient,
                    message=" ",
                )

        send_mock.assert_not_awaited()

    async def test_send_to_active_recipients(self):
        telegram_result = SimpleNamespace(
            success=True,
            chat_id="123456789",
            message="Message sent successfully",
        )

        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            return_value=telegram_result,
            create=True,
        ) as send_mock:
            records = await self.service.send_to_active_recipients(
                token="test-token",
                message="Team announcement",
            )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].chat_id, "123456789")
        self.assertEqual(records[0].status, DeliveryStatus.SUCCESS)
        send_mock.assert_awaited_once()

    async def test_delivery_exception_is_recorded(self):
        with patch.object(
            self.telegram_service,
            "send_message",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Simulated network failure"),
            create=True,
        ):
            records = await self.service.send_to_active_recipients(
                token="test-token",
                message="Team announcement",
            )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, DeliveryStatus.FAILED)
        self.assertTrue(records[0].error_message)


if __name__ == "__main__":
    unittest.main()
