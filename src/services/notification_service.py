"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Notification Orchestration Service
"""

from src.models.delivery_record import (
    DeliveryRecord,
    DeliveryStatus,
)
from src.models.recipient import Recipient
from src.services.recipient_service import RecipientService
from src.services.telegram_service import (
    TelegramSendResult,
    TelegramService,
)


class NotificationService:
    """Coordinate Telegram message delivery to registered recipients."""

    def __init__(
        self,
        telegram_service: TelegramService,
        recipient_service: RecipientService,
    ) -> None:
        """Initialize the notification service dependencies."""
        if not isinstance(telegram_service, TelegramService):
            raise TypeError(
                "telegram_service must be a TelegramService instance."
            )

        if not isinstance(recipient_service, RecipientService):
            raise TypeError(
                "recipient_service must be a RecipientService instance."
            )

        self.telegram_service = telegram_service
        self.recipient_service = recipient_service

    async def send_to_recipient(
        self,
        token: str,
        recipient: Recipient,
        message: str,
    ) -> DeliveryRecord:
        """Send one message and return its delivery record."""
        if not isinstance(recipient, Recipient):
            raise TypeError("recipient must be a Recipient instance.")

        if not recipient.is_active:
            raise ValueError(
                f"Recipient {recipient.chat_id} is inactive."
            )

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        result = await self.telegram_service.send_message(
            token=token,
            chat_id=recipient.chat_id,
            text=message,
        )

        return self._create_delivery_record(
            recipient,
            message,
            result,
        )

    async def send_to_active_recipients(
        self,
        token: str,
        message: str,
    ) -> list[DeliveryRecord]:
        """Send a message to each active recipient sequentially."""
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        recipients = self.recipient_service.list_recipients(
            active_only=True
        )

        records: list[DeliveryRecord] = []

        for recipient in recipients:
            try:
                record = await self.send_to_recipient(
                    token=token,
                    recipient=recipient,
                    message=message,
                )
            except Exception as error:
                record = DeliveryRecord(
                    chat_id=recipient.chat_id,
                    message=message,
                    status=DeliveryStatus.FAILED,
                    error_message=(
                        f"Delivery operation failed: "
                        f"{type(error).__name__}"
                    ),
                )

            records.append(record)

        return records

    @staticmethod
    def _create_delivery_record(
        recipient: Recipient,
        message: str,
        result: TelegramSendResult,
    ) -> DeliveryRecord:
        """Convert a Telegram send result into a delivery record."""
        if result.success:
            return DeliveryRecord(
                chat_id=recipient.chat_id,
                message=message,
                status=DeliveryStatus.SUCCESS,
            )

        error_message = result.message.strip()

        if not error_message:
            error_message = "Telegram message delivery failed."

        return DeliveryRecord(
            chat_id=recipient.chat_id,
            message=message,
            status=DeliveryStatus.FAILED,
            error_message=error_message,
        )


# Public methods:
# - send_to_recipient(token, recipient, message)
# - send_to_active_recipients(token, message)
#
# Dependencies:
# - Internal models: DeliveryRecord, DeliveryStatus, Recipient.
# - Internal services: RecipientService, TelegramService.