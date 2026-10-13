
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Message Delivery Record
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class DeliveryStatus(str, Enum):
    """Represent the outcome of a Telegram delivery attempt."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """Represent one message delivery attempt."""

    chat_id: str
    message: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempted_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize delivery record fields."""
        normalized_chat_id = self.chat_id.strip()

        if not normalized_chat_id:
            raise ValueError("Telegram chat ID cannot be empty.")

        if not normalized_chat_id.lstrip("-").isdigit():
            raise ValueError(
                "Telegram chat ID must contain a numeric ID."
            )

        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Delivery message cannot be empty.")

        if not isinstance(self.status, DeliveryStatus):
            raise ValueError("Invalid delivery status.")

        timestamp = self.attempted_at

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError(
                "Delivery timestamp must include timezone information."
            )

        normalized_error = (
            self.error_message.strip()
            if self.error_message is not None
            else None
        )

        if self.status == DeliveryStatus.FAILED and not normalized_error:
            raise ValueError(
                "A failed delivery must include an error description."
            )

        if self.status != DeliveryStatus.FAILED and normalized_error:
            raise ValueError(
                "An error description is only valid for failed delivery."
            )

        object.__setattr__(self, "chat_id", normalized_chat_id)
        object.__setattr__(self, "attempted_at", timestamp)
        object.__setattr__(self, "error_message", normalized_error)
