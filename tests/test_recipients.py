
"""
Project : Telegram Automation Bot
Project ID : 035

Recipient Service Unit Tests
"""

import unittest

from src.models.recipient import Recipient
from src.services.recipient_service import RecipientService


class TestRecipientService(unittest.TestCase):
    """Tests for recipient management operations."""

    def setUp(self):
        """Create a fresh recipient service for each test."""
        self.service = RecipientService()
        self.recipient = Recipient(
            chat_id="123456789",
            name="Finance Team",
        )

    def test_add_and_get_recipient(self):
        """A recipient can be added and retrieved."""
        self.service.add_recipient(self.recipient)

        result = self.service.get_recipient("123456789")

        self.assertEqual(result, self.recipient)

    def test_list_recipients(self):
        """All recipients can be listed."""
        second = Recipient(
            chat_id="987654321",
            name="Management Team",
        )

        self.service.add_recipient(self.recipient)
        self.service.add_recipient(second)

        recipients = self.service.list_recipients()

        self.assertEqual(len(recipients), 2)

    def test_list_active_recipients(self):
        """Only active recipients are returned when requested."""
        active = Recipient(
            chat_id="123456789",
            name="Finance Team",
            is_active=True,
        )
        inactive = Recipient(
            chat_id="987654321",
            name="Management Team",
            is_active=False,
        )

        self.service.add_recipient(active)
        self.service.add_recipient(inactive)

        recipients = self.service.list_recipients(
            active_only=True
        )

        self.assertEqual(len(recipients), 1)
        self.assertEqual(
            recipients[0].chat_id,
            "123456789",
        )

    def test_update_recipient(self):
        """A recipient's name can be updated."""
        self.service.add_recipient(self.recipient)

        # The existing service accepts chat_id and name separately.
        self.service.update_recipient(
            "123456789",
            "Updated Finance Team",
        )

        result = self.service.get_recipient("123456789")

        self.assertEqual(
            result.name,
            "Updated Finance Team",
        )

    def test_activate_recipient(self):
        """An inactive recipient can be activated."""
        inactive = Recipient(
            chat_id="123456789",
            name="Finance Team",
            is_active=False,
        )
        self.service.add_recipient(inactive)

        self.service.activate_recipient("123456789")

        result = self.service.get_recipient("123456789")

        self.assertTrue(result.is_active)

    def test_deactivate_recipient(self):
        """An active recipient can be deactivated."""
        self.service.add_recipient(self.recipient)

        self.service.deactivate_recipient("123456789")

        result = self.service.get_recipient("123456789")

        self.assertFalse(result.is_active)

    def test_remove_recipient(self):
        """A recipient can be removed."""
        self.service.add_recipient(self.recipient)

        self.service.remove_recipient("123456789")

        self.assertIsNone(
            self.service.get_recipient("123456789")
        )

    def test_duplicate_recipient_is_rejected(self):
        """Adding the same recipient twice is rejected."""
        self.service.add_recipient(self.recipient)

        with self.assertRaises((ValueError, KeyError)):
            self.service.add_recipient(self.recipient)

    def test_invalid_recipient_data_is_rejected(self):
        """A non-numeric chat ID is rejected."""
        with self.assertRaises((ValueError, TypeError)):
            Recipient(
                chat_id="not-a-numeric-id",
                name="Invalid Recipient",
            )

    def test_empty_recipient_name_is_rejected(self):
        """A blank recipient name is rejected."""
        with self.assertRaises(ValueError):
            Recipient(
                chat_id="123456789",
                name=" ",
            )


if __name__ == "__main__":
    unittest.main()
