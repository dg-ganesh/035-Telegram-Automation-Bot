
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Message Delivery Record
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class DeliveryStatus(str, Enum):
    """Supported delivery states."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """Immutable record of a Telegram message delivery attempt."""

    chat_id: str
    message: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempted_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        chat_id = str(self.chat_id).strip()
        message = self.message.strip()

        if not chat_id:
            raise ValueError("Chat ID cannot be empty.")

        if not chat_id.lstrip("-").isdigit():
            raise ValueError("Chat ID must be numeric.")

        if not message:
            raise ValueError("Message cannot be empty.")

        if not isinstance(self.status, DeliveryStatus):
            raise TypeError("Status must be a DeliveryStatus value.")

        timestamp = self.attempted_at
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif (
            not isinstance(timestamp, datetime)
            or timestamp.tzinfo is None
            or timestamp.utcoffset() is None
        ):
            raise ValueError(
                "Attempt timestamp must be timezone-aware."
            )

        error = self.error_message
        if error is not None:
            error = str(error).strip() or None

        if self.status == DeliveryStatus.FAILED and not error:
            raise ValueError(
                "Failed delivery requires an error description."
            )

        if self.status != DeliveryStatus.FAILED and error:
            raise ValueError(
                "Only failed deliveries can contain an error description."
            )

        object.__setattr__(self, "chat_id", chat_id)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "attempted_at", timestamp)
        object.__setattr__(self, "error_message", error)
