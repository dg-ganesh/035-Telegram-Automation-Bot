
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Recipient Management Service
"""

from src.models.recipient import Recipient


class RecipientService:
    """Manage Telegram recipients in memory."""

    def __init__(self) -> None:
        """Initialize an empty recipient collection."""
        self._recipients: dict[str, Recipient] = {}

    def add_recipient(self, recipient: Recipient) -> Recipient:
        """Add a recipient if its chat ID is not already registered."""
        if not isinstance(recipient, Recipient):
            raise TypeError("recipient must be a Recipient instance.")

        if recipient.chat_id in self._recipients:
            raise ValueError(
                f"Recipient {recipient.chat_id} already exists."
            )

        self._recipients[recipient.chat_id] = recipient
        return recipient

    def get_recipient(self, chat_id: str) -> Recipient | None:
        """Return a recipient by chat ID, or None if not found."""
        normalized_chat_id = chat_id.strip()
        return self._recipients.get(normalized_chat_id)

    def list_recipients(
        self,
        active_only: bool = False,
    ) -> list[Recipient]:
        """Return recipients, optionally filtering to active entries."""
        recipients = list(self._recipients.values())

        if active_only:
            recipients = [
                recipient
                for recipient in recipients
                if recipient.is_active
            ]

        return recipients

    def update_recipient(
        self,
        chat_id: str,
        name: str,
    ) -> Recipient:
        """Update a recipient's display name."""
        normalized_chat_id = chat_id.strip()
        existing = self._recipients.get(normalized_chat_id)

        if existing is None:
            raise KeyError(
                f"Recipient {normalized_chat_id} was not found."
            )

        updated = Recipient(
            chat_id=existing.chat_id,
            name=name,
            is_active=existing.is_active,
        )

        self._recipients[normalized_chat_id] = updated
        return updated

    def activate_recipient(self, chat_id: str) -> Recipient:
        """Activate an existing recipient."""
        return self._change_active_status(chat_id, active=True)

    def deactivate_recipient(self, chat_id: str) -> Recipient:
        """Deactivate an existing recipient."""
        return self._change_active_status(chat_id, active=False)

    def remove_recipient(self, chat_id: str) -> Recipient:
        """Remove a recipient and return the removed record."""
        normalized_chat_id = chat_id.strip()

        try:
            return self._recipients.pop(normalized_chat_id)
        except KeyError as error:
            raise KeyError(
                f"Recipient {normalized_chat_id} was not found."
            ) from error

    def _change_active_status(
        self,
        chat_id: str,
        active: bool,
    ) -> Recipient:
        """Replace a recipient with an updated active-status record."""
        normalized_chat_id = chat_id.strip()
        existing = self._recipients.get(normalized_chat_id)

        if existing is None:
            raise KeyError(
                f"Recipient {normalized_chat_id} was not found."
            )

        updated = (
            existing.activate()
            if active
            else existing.deactivate()
        )

        self._recipients[normalized_chat_id] = updated
        return updated

