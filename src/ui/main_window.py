

"""

Project : Telegram Automation Bot

Project ID : 035

Main Window

"""

import asyncio

import queue
import re

import threading

import tkinter as tk

from tkinter import messagebox, ttk

from src.config import AppConfig, validate_telegram_token

from src.models.delivery_record import (

    DeliveryRecord,

    DeliveryStatus,

)

from src.models.recipient import Recipient

from src.services.logging_service import LoggingService

from src.services.notification_service import NotificationService

from src.services.recipient_service import RecipientService

from src.services.telegram_service import (

    TelegramConnectionResult,

    TelegramService,

)

from src.ui.message_panel import MessagePanel

class MainWindow:

    """Provide Telegram connection and message-delivery controls."""

    def __init__(

        self,

        root: tk.Tk,

        config: AppConfig,

        logging_service: LoggingService,

    ) -> None:

        """Initialize the application window and its services."""

        self.root = root

        self.config = config

        self.logging_service = logging_service

        self.logger = logging_service.get_logger()

        self.telegram_service = TelegramService(

            request_timeout_seconds=config.request_timeout_seconds

        )

        self.recipient_service = RecipientService()

        self.notification_service = NotificationService(

            telegram_service=self.telegram_service,

            recipient_service=self.recipient_service,

        )

        self._connected = False

        self._checking = False

        self._sending = False

        self._closing = False

        self._token = ""

        self._result_queue: queue.Queue = queue.Queue()

        self.root.title(config.application_name)

        self.root.geometry("720x680")

        self.root.minsize(640, 560)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.token_var = tk.StringVar(

            value=config.telegram_token or ""

        )

        self.status_var = tk.StringVar(value="Not connected")

        self.identity_var = tk.StringVar(

            value="Bot identity: not verified"

        )

        self.delivery_var = tk.StringVar(

            value="No delivery results yet"

        )

        self._build_layout()

        self.logging_service.record_checkpoint(

            "Main window constructed",

            True,

            "Connection controls and message panel created.",

        )

        self.root.after(100, self._process_results)

    def _build_layout(self) -> None:

        """Create the connection controls and message panel."""

        frame = ttk.Frame(self.root, padding=16)

        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(

            frame,

            text="Telegram Automation Bot",

            font=("Segoe UI", 14, "bold"),

        ).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Bot token").pack(anchor=tk.W)

        token_row = ttk.Frame(frame)

        token_row.pack(fill=tk.X, pady=(4, 8))

        self.token_entry = ttk.Entry(

            token_row,

            textvariable=self.token_var,

            show="*",

            width=55,

        )

        self.token_entry.pack(

            side=tk.LEFT,

            fill=tk.X,

            expand=True,

        )

        self.show_token_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(

            token_row,

            text="Show",

            variable=self.show_token_var,

            command=self._toggle_token,

        ).pack(side=tk.LEFT, padx=(8, 0))

        connection_buttons = ttk.Frame(frame)

        connection_buttons.pack(fill=tk.X, pady=(2, 6))

        self.connect_button = ttk.Button(

            connection_buttons,

            text="Connect and Verify",

            command=self._connect,

        )

        self.connect_button.pack(side=tk.LEFT)

        self.disconnect_button = ttk.Button(

            connection_buttons,

            text="Disconnect",

            command=self._disconnect,

        )

        self.disconnect_button.pack(

            side=tk.LEFT,

            padx=(8, 0),

        )

        ttk.Label(

            frame,

            textvariable=self.status_var,

        ).pack(anchor=tk.W, pady=(2, 2))

        ttk.Label(

            frame,

            textvariable=self.identity_var,

            wraplength=660,

        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Separator(frame).pack(fill=tk.X, pady=8)

        self.message_panel = MessagePanel(

            frame,

            on_submit=self._send,

        )

        self.message_panel.pack(

            fill=tk.BOTH,

            expand=True,

            pady=(0, 8),

        )

        self.message_panel.set_submission_enabled(False)

        ttk.Label(

            frame,

            textvariable=self.delivery_var,

            wraplength=660,

        ).pack(anchor=tk.W, pady=(4, 0))

        ttk.Label(

            frame,

            text=(

                "The bot token remains in memory for this session "

                "and is not saved by this window."

            ),

            wraplength=660,

        ).pack(anchor=tk.W, pady=(8, 0))

    @staticmethod
    def _parse_chat_ids(raw: str) -> tuple[list[str], str | None]:
        """Parse, validate, and de-duplicate comma/newline-separated chat IDs."""
        if not isinstance(raw, str) or not raw.strip():
            return [], "Enter at least one recipient chat ID."

        entries = [
            entry.strip()
            for entry in re.split(r"[,\r\n]+", raw)
            if entry.strip()
        ]

        if not entries:
            return [], "Enter at least one recipient chat ID."

        chat_ids: list[str] = []
        seen: set[str] = set()

        for chat_id in entries:
            if not TelegramService.CHAT_ID_PATTERN.fullmatch(chat_id):
                return [], f"Invalid Telegram chat ID: {chat_id}"

            if chat_id not in seen:
                seen.add(chat_id)
                chat_ids.append(chat_id)

        return chat_ids, None

    def _toggle_token(self) -> None:

        """Show or mask the token in the entry field."""

        self.token_entry.configure(

            show="" if self.show_token_var.get() else "*"

        )

    def _connect(self) -> None:

        """Validate the token and start background verification."""

        if self._checking or self._sending or self._closing:

            return

        token = self.token_var.get().strip()

        token_error = validate_telegram_token(token)

        if token_error:

            self._connected = False

            self._token = ""

            self.message_panel.set_submission_enabled(False)

            self.status_var.set("Connection failed")

            self.identity_var.set(token_error)

            self.logging_service.record_checkpoint(

                "Telegram connection verification",

                False,

                "Bot token format validation failed.",

            )

            self.logger.warning(

                "Telegram token format validation failed."

            )

            return

        self._checking = True

        self.connect_button.configure(state=tk.DISABLED)

        self.message_panel.set_submission_enabled(False)

        self.status_var.set("Connecting to Telegram...")

        self.identity_var.set("Bot identity: verification in progress")

        threading.Thread(

            target=self._verify_worker,

            args=(token,),

            daemon=True,

        ).start()

    def _verify_worker(self, token: str) -> None:

        """Verify the bot without blocking the GUI thread."""

        try:

            result = asyncio.run(

                self.telegram_service.verify_connection(token)

            )

            self._result_queue.put(("connection", token, result, None))

        except Exception as error:

            self.logger.error(

                "Unexpected connection error type: %s",

                type(error).__name__,

            )

            self._result_queue.put(

                ("connection_error", token, None, type(error).__name__)

            )

    def _send(

        self,

        chat_ids: list[str],

        message: str,

    ) -> None:

        """Validate panel input and start message delivery."""

        if self._sending or self._checking or self._closing:

            self.message_panel.set_status(

                "Another operation is in progress."

            )

            return

        if not self._connected or not self._token:

            self.message_panel.set_status(

                "Connect and verify the bot before sending."

            )

            return

        token_error = validate_telegram_token(self._token)

        if token_error:

            self._connected = False

            self._token = ""

            self.message_panel.set_submission_enabled(False)

            self.message_panel.set_status(

                "The saved token is invalid. Connect again."

            )

            return

        if not chat_ids:

            self.message_panel.set_status(

                "Enter at least one recipient chat ID."

            )

            return

        if not message.strip():

            self.message_panel.set_status(

                "Enter a message before sending."

            )

            return

        if len(message) > TelegramService.MAX_MESSAGE_LENGTH:

            self.message_panel.set_status(

                "Message exceeds Telegram's character limit."

            )

            return

        self._sending = True

        self.connect_button.configure(state=tk.DISABLED)

        self.message_panel.set_submission_enabled(False)

        self.delivery_var.set(

            f"Sending to {len(chat_ids)} recipient(s)..."

        )

        self.message_panel.set_status("Message delivery in progress.")

        threading.Thread(

            target=self._send_worker,

            args=(self._token, chat_ids, message),

            daemon=True,

        ).start()

    def _send_worker(

        self,

        token: str,

        chat_ids: list[str],

        message: str,

    ) -> None:

        """Send to recipients sequentially and queue delivery records."""

        try:

            records = asyncio.run(

                self._send_all(token, chat_ids, message)

            )

            self._result_queue.put(

                ("delivery_results", records, None, None)

            )

        except Exception as error:

            self.logger.error(

                "Unexpected message-delivery error type: %s",

                type(error).__name__,

            )

            self._result_queue.put(

                ("delivery_error", None, None, type(error).__name__)

            )

    async def _send_all(

        self,

        token: str,

        chat_ids: list[str],

        message: str,

    ) -> list[DeliveryRecord]:

        """Send to every supplied chat ID and retain individual outcomes."""

        records: list[DeliveryRecord] = []

        for chat_id in chat_ids:

            recipient = Recipient(

                chat_id=chat_id,

                name=chat_id,

                is_active=True,

            )

            try:

                record = await self.notification_service.send_to_recipient(

                    token=token,

                    recipient=recipient,

                    message=message,

                )

            except Exception as error:

                self.logger.error(

                    "Delivery processing error for chat ID %s: %s",

                    chat_id,

                    type(error).__name__,

                )

                record = DeliveryRecord(

                    chat_id=chat_id,

                    message=message,

                    status=DeliveryStatus.FAILED,

                    error_message=(

                        "Delivery operation failed: "

                        f"{type(error).__name__}"

                    ),

                )

            records.append(record)

        return records

    def _process_results(self) -> None:

        """Handle background results on Tkinter's main thread."""

        if self._closing:

            return

        while True:

            try:

                kind, token, result, error_type = (

                    self._result_queue.get_nowait()

                )

            except queue.Empty:

                break

            if kind == "connection":

                self._show_connection_result(token, result)

            elif kind == "connection_error":

                self._show_connection_error(token, error_type)

            elif kind == "delivery_results":

                self._show_delivery_results(token)

            elif kind == "delivery_error":

                self._show_delivery_error(error_type)

        self.root.after(100, self._process_results)

    def _show_connection_result(

        self,

        token: str,

        result: TelegramConnectionResult,

    ) -> None:

        """Display and record the Telegram connection result."""

        self._checking = False

        self.connect_button.configure(state=tk.NORMAL)

        self._connected = result.success

        self._token = token if result.success else ""

        self.status_var.set(

            "Connected" if result.success else "Connection failed"

        )

        if result.success and result.identity:

            identity = result.identity

            username = (

                f"@{identity.username}"

                if identity.username

                else "(no username)"

            )

            self.identity_var.set(

                f"Bot identity: {identity.first_name} | "

                f"{username} | ID: {identity.user_id}"

            )

            self.message_panel.set_submission_enabled(True)

        else:

            self.identity_var.set(result.message)

            self.message_panel.set_submission_enabled(False)

        self.logging_service.record_checkpoint(

            "Telegram connection verification",

            result.success,

            result.message,

        )

    def _show_connection_error(

        self,

        token: str,

        error_type: str,

    ) -> None:

        """Restore controls after an unexpected connection error."""

        self._checking = False

        self._connected = False

        self._token = ""

        self.connect_button.configure(state=tk.NORMAL)

        self.message_panel.set_submission_enabled(False)

        self.status_var.set("Connection failed")

        self.identity_var.set(

            "Unexpected error. Review logs/application.log."

        )

        self.logging_service.record_checkpoint(

            "Telegram connection verification",

            False,

            f"Unexpected error type: {error_type}",

        )

    def _show_delivery_results(

        self,

        records: list[DeliveryRecord],

    ) -> None:

        """Display the outcome for every recipient."""

        self._sending = False

        self.connect_button.configure(state=tk.NORMAL)

        self.message_panel.set_submission_enabled(self._connected)

        sent = sum(

            record.status == DeliveryStatus.SUCCESS

            for record in records

        )

        failed = sum(

            record.status == DeliveryStatus.FAILED

            for record in records

        )

        lines = [

            f"Delivery complete: {sent} sent, {failed} failed."

        ]

        for record in records:

            label = (

                "SENT"

                if record.status == DeliveryStatus.SUCCESS

                else "FAILED"

            )

            detail = (

                f"{label} | Chat ID {record.chat_id}"

            )

            if record.error_message:

                detail += f" | {record.error_message}"

            lines.append(detail)

            log_method = (

                self.logger.info

                if record.status == DeliveryStatus.SUCCESS

                else self.logger.warning

            )

            log_method(

                "Telegram delivery %s for chat ID %s",

                label,

                record.chat_id,

            )

        summary = "\n".join(lines)

        self.delivery_var.set(summary)

        self.message_panel.set_status(

            f"Delivery finished: {sent} successful, {failed} failed."

        )

        self.logging_service.record_checkpoint(

            "Telegram message delivery attempt",

            failed == 0,

            f"{sent} sent; {failed} failed. Results displayed.",

        )

    def _show_delivery_error(self, error_type: str) -> None:

        """Restore controls after an unexpected delivery error."""

        self._sending = False

        self.connect_button.configure(state=tk.NORMAL)

        self.message_panel.set_submission_enabled(self._connected)

        self.delivery_var.set(

            "Message delivery failed unexpectedly. "

            "Review logs/application.log."

        )

        self.message_panel.set_status(

            "Delivery failed unexpectedly. Review the application log."

        )

        self.logging_service.record_checkpoint(

            "Telegram message delivery attempt",

            False,

            f"Unexpected error type: {error_type}",

        )

    def _disconnect(self) -> None:

        """Clear the locally cached bot identity and connection state."""

        if self._checking or self._sending:

            messagebox.showinfo(

                "Operation in progress",

                "Wait for the current request to finish.",

                parent=self.root,

            )

            return

        self.telegram_service.disconnect()

        self._connected = False

        self._token = ""

        self.status_var.set("Disconnected")

        self.identity_var.set("Bot identity: not verified")

        self.message_panel.set_submission_enabled(False)

        self.logging_service.record_checkpoint(

            "Local disconnect",

            True,

            "Cached bot identity cleared.",

        )

    def _on_close(self) -> None:

        """Record shutdown and close the application window."""

        if self._checking or self._sending:

            should_close = messagebox.askyesno(

                "Operation in progress",

                "A Telegram request is in progress. Close the application?",

                parent=self.root,

            )

            if not should_close:

                return

        self._closing = True

        self._connected = False

        self._token = ""

        self.logging_service.record_checkpoint(

            "Application shutdown",

            True,

            "Window closed by user.",

        )

        self.root.destroy()

# Public interface:

# - MainWindow(root, config, logging_service)

#

# Dependencies:

# - Python standard library: asyncio, queue, threading, tkinter.

# - Internal modules: src.config, src.models, src.services,

#   src.ui.message_panel.
