
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Connection and Message Delivery Service
"""

import asyncio
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TelegramBotIdentity:
    """Represent the identity returned by Telegram getMe."""

    user_id: int
    username: str | None
    first_name: str
    is_bot: bool


@dataclass(frozen=True, slots=True)
class TelegramConnectionResult:
    """Represent the outcome of a Telegram connection check."""

    success: bool
    message: str
    identity: TelegramBotIdentity | None = None


@dataclass(frozen=True, slots=True)
class TelegramSendResult:
    """Represent one recipient's message-delivery result."""

    success: bool
    chat_id: str
    message: str
    message_id: int | None = None


class TelegramAPIError(ValueError):
    """Represent a safe error returned by Telegram's Bot API."""


class TelegramService:
    """Verify bot credentials and send messages through Telegram's Bot API."""

    API_BASE_URL = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 4096

    TOKEN_PATTERN = re.compile(r"[0-9]+:[A-Za-z0-9_-]+")
    CHAT_ID_PATTERN = re.compile(r"-?[0-9]+")

    def __init__(self, request_timeout_seconds: float = 15.0) -> None:
        """Initialize the service with a positive network timeout."""
        if request_timeout_seconds <= 0:
            raise ValueError("Request timeout must be greater than zero.")

        self.request_timeout_seconds = request_timeout_seconds
        self._identity: TelegramBotIdentity | None = None

    @property
    def identity(self) -> TelegramBotIdentity | None:
        """Return the most recently verified bot identity."""
        return self._identity

    async def verify_connection(
        self,
        token: str,
    ) -> TelegramConnectionResult:
        """Verify the token using Telegram's getMe endpoint."""
        candidate = token.strip()

        if not self.TOKEN_PATTERN.fullmatch(candidate):
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message="The Telegram bot token format is invalid.",
            )

        try:
            identity = await asyncio.to_thread(
                self._request_bot_identity,
                candidate,
            )
        except TimeoutError:
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message="Telegram connection timed out.",
            )
        except urllib.error.HTTPError as error:
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message=self._describe_http_error(error),
            )
        except urllib.error.URLError:
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message=(
                    "Unable to reach Telegram. Check your internet "
                    "connection and try again."
                ),
            )
        except TelegramAPIError as error:
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message=str(error),
            )
        except (OSError, ValueError):
            self._identity = None
            return TelegramConnectionResult(
                success=False,
                message=(
                    "Telegram returned an invalid response or "
                    "a connection error occurred."
                ),
            )

        self._identity = identity

        return TelegramConnectionResult(
            success=True,
            message="Telegram bot connected successfully.",
            identity=identity,
        )

    async def send_message(
        self,
        token: str,
        chat_id: str,
        text: str,
    ) -> TelegramSendResult:
        """Send one text message to one Telegram chat."""
        candidate_token = token.strip()
        candidate_chat_id = str(chat_id).strip()
        candidate_text = text.strip()

        if not self.TOKEN_PATTERN.fullmatch(candidate_token):
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "The Telegram bot token format is invalid.",
            )

        if not self.CHAT_ID_PATTERN.fullmatch(candidate_chat_id):
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "Chat ID must be a numeric Telegram chat ID.",
            )

        if not candidate_text:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "Message text cannot be empty.",
            )

        if len(candidate_text) > self.MAX_MESSAGE_LENGTH:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                f"Message exceeds Telegram's "
                f"{self.MAX_MESSAGE_LENGTH}-character limit.",
            )

        try:
            message_id = await asyncio.to_thread(
                self._request_send_message,
                candidate_token,
                candidate_chat_id,
                candidate_text,
            )
        except TimeoutError:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "Telegram request timed out.",
            )
        except urllib.error.HTTPError as error:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                self._describe_send_http_error(error),
            )
        except urllib.error.URLError:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "Unable to reach Telegram. Check your internet connection.",
            )
        except TelegramAPIError as error:
            return TelegramSendResult(
                False,
                candidate_chat_id,
                str(error),
            )
        except (OSError, ValueError):
            return TelegramSendResult(
                False,
                candidate_chat_id,
                "Telegram returned an invalid response or a connection error occurred.",
            )

        return TelegramSendResult(
            success=True,
            chat_id=candidate_chat_id,
            message="Message sent successfully.",
            message_id=message_id,
        )

    async def send_messages(
        self,
        token: str,
        chat_ids: Sequence[str],
        text: str,
    ) -> list[TelegramSendResult]:
        """
        Send the same text to each chat ID sequentially.

        Telegram receives one sendMessage request per chat ID.
        The method returns a separate result for each recipient.
        """
        results: list[TelegramSendResult] = []

        for chat_id in chat_ids:
            result = await self.send_message(
                token=token,
                chat_id=chat_id,
                text=text,
            )
            results.append(result)

        return results

    def _request_bot_identity(
        self,
        token: str,
    ) -> TelegramBotIdentity:
        """Call getMe and validate the response structure."""
        encoded_token = urllib.parse.quote(token, safe=":")
        endpoint = f"{self.API_BASE_URL}/bot{encoded_token}/getMe"

        request = urllib.request.Request(
            endpoint,
            headers={"Accept": "application/json"},
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=self.request_timeout_seconds,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise TelegramAPIError("Telegram rejected the connection request.")

        result = payload.get("result")

        if not isinstance(result, dict):
            raise ValueError("Telegram response did not contain a bot.")

        user_id = result.get("id")
        username = result.get("username")
        first_name = result.get("first_name")
        is_bot = result.get("is_bot")

        if (
            not isinstance(user_id, int)
            or isinstance(user_id, bool)
            or not isinstance(first_name, str)
            or not isinstance(is_bot, bool)
            or not is_bot
            or (
                username is not None
                and not isinstance(username, str)
            )
        ):
            raise ValueError("Telegram returned invalid bot details.")

        return TelegramBotIdentity(
            user_id=user_id,
            username=username,
            first_name=first_name,
            is_bot=is_bot,
        )

    def _request_send_message(
        self,
        token: str,
        chat_id: str,
        text: str,
    ) -> int:
        """Call Telegram's sendMessage endpoint using a JSON POST."""
        encoded_token = urllib.parse.quote(token, safe=":")
        endpoint = f"{self.API_BASE_URL}/bot{encoded_token}/sendMessage"

        request_body = json.dumps(
            {
                "chat_id": chat_id,
                "text": text,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            endpoint,
            data=request_body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=self.request_timeout_seconds,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Unexpected Telegram response.")

        if payload.get("ok") is not True:
            description = payload.get(
                "description",
                "Telegram rejected the message.",
            )
            raise TelegramAPIError(str(description))

        result = payload.get("result")

        if not isinstance(result, dict):
            raise ValueError(
                "Telegram response did not contain a sent message."
            )

        message_id = result.get("message_id")

        if (
            not isinstance(message_id, int)
            or isinstance(message_id, bool)
        ):
            raise ValueError(
                "Telegram response did not contain a valid message ID."
            )

        return message_id

    @staticmethod
    def _describe_http_error(
        error: urllib.error.HTTPError,
    ) -> str:
        """Describe common connection errors without exposing credentials."""
        if error.code == 401:
            return "Telegram rejected the bot token. Check the token."

        if error.code == 403:
            return "Telegram denied access to this bot resource."

        if error.code == 429:
            return "Telegram rate limit reached. Try again later."

        if error.code >= 500:
            return "Telegram is temporarily unavailable. Try again later."

        return f"Telegram request failed with HTTP status {error.code}."

    @staticmethod
    def _describe_send_http_error(
        error: urllib.error.HTTPError,
    ) -> str:
        """Describe common message-delivery failures."""
        if error.code == 400:
            return (
                "Telegram rejected the recipient or message. "
                "Check the chat ID and bot access."
            )

        if error.code == 401:
            return "Telegram rejected the bot token. Check the token."

        if error.code == 403:
            return (
                "Telegram forbids delivery to this chat. "
                "The recipient may need to start the bot."
            )

        if error.code == 429:
            return "Telegram rate limit reached. Try again later."

        if error.code >= 500:
            return "Telegram is temporarily unavailable. Try again later."

        return (
            f"Telegram message request failed with HTTP status "
            f"{error.code}."
        )

    def disconnect(self) -> None:
        """Clear the locally cached bot identity."""
        self._identity = None


# Public methods:
# - verify_connection(token) -> TelegramConnectionResult (async)
# - send_message(token, chat_id, text) -> TelegramSendResult (async)
# - send_messages(token, chat_ids, text) -> list[TelegramSendResult] (async)
# - disconnect() -> None
#
# Public property:
# - identity -> TelegramBotIdentity | None
#
# Dependencies:
# - Python standard library only.
