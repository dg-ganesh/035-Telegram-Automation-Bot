
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Recipient Data Model
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Recipient:
    """Represent a Telegram message recipient."""

    chat_id: str
    name: str
    is_active: bool = True

    def __post_init__(self) -> None:
        """Validate recipient data when an instance is created."""
        normalized_chat_id = self.chat_id.strip()
        normalized_name = self.name.strip()

        if not normalized_chat_id:
            raise ValueError("Telegram chat ID cannot be empty.")

        if not normalized_chat_id.lstrip("-").isdigit():
            raise ValueError(
                "Telegram chat ID must contain a numeric ID."
            )

        if not normalized_name:
            raise ValueError("Recipient name cannot be empty.")

        if not isinstance(self.is_active, bool):
            raise ValueError(
                "Recipient active status must be True or False."
            )

        object.__setattr__(self, "chat_id", normalized_chat_id)
        object.__setattr__(self, "name", normalized_name)

    def activate(self) -> "Recipient":
        """Return an active copy of this recipient."""
        return Recipient(
            chat_id=self.chat_id,
            name=self.name,
            is_active=True,
        )

    def deactivate(self) -> "Recipient":
        """Return an inactive copy of this recipient."""
        return Recipient(
            chat_id=self.chat_id,
            name=self.name,
            is_active=False,
        )
