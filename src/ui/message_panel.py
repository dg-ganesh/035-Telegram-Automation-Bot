
"""
Project : Telegram Automation Bot
Project ID : 035

Telegram Message Composition Panel
"""

import re
import tkinter as tk
from tkinter import ttk
from collections.abc import Callable


class MessagePanel(ttk.LabelFrame):
    """Provide message composition and recipient selection controls."""

    MAX_MESSAGE_LENGTH = 4096

    def __init__(
        self,
        master: tk.Misc,
        on_submit: Callable[[list[str], str], None],
    ) -> None:
        """Create the panel and register its submission callback."""
        super().__init__(
            master,
            text="Compose Telegram Message",
            padding=12,
        )

        if not callable(on_submit):
            raise TypeError("on_submit must be callable.")

        self._on_submit = on_submit

        self.message_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self._build_layout()

    def _build_layout(self) -> None:
        """Create recipient, message, and submission controls."""
        ttk.Label(
            self,
            text="Recipient chat IDs",
        ).grid(
            row=0,
            column=0,
            sticky=tk.W,
            pady=(0, 4),
        )

        ttk.Label(
            self,
            text="Enter numeric chat IDs separated by commas or new lines.",
        ).grid(
            row=1,
            column=0,
            sticky=tk.W,
            pady=(0, 4),
        )

        self.recipient_text = tk.Text(
            self,
            height=3,
            wrap=tk.WORD,
            undo=True,
        )
        self.recipient_text.grid(
            row=2,
            column=0,
            sticky=tk.EW,
            pady=(0, 10),
        )

        ttk.Label(
            self,
            text="Message",
        ).grid(
            row=3,
            column=0,
            sticky=tk.W,
            pady=(0, 4),
        )

        self.message_text = tk.Text(
            self,
            height=6,
            wrap=tk.WORD,
            undo=True,
        )
        self.message_text.grid(
            row=4,
            column=0,
            sticky=tk.EW,
            pady=(0, 4),
        )
        self.message_text.bind(
            "<KeyRelease>",
            self._update_character_count,
        )

        self.character_count_var = tk.StringVar(
            value=f"0 / {self.MAX_MESSAGE_LENGTH}"
        )

        ttk.Label(
            self,
            textvariable=self.character_count_var,
        ).grid(
            row=5,
            column=0,
            sticky=tk.E,
            pady=(0, 8),
        )

        button_row = ttk.Frame(self)
        button_row.grid(
            row=6,
            column=0,
            sticky=tk.EW,
            pady=(0, 8),
        )

        ttk.Button(
            button_row,
            text="Clear",
            command=self.clear,
        ).pack(side=tk.LEFT)

        self.send_button = ttk.Button(
            button_row,
            text="Submit Message",
            command=self.submit,
        )
        self.send_button.pack(side=tk.RIGHT)

        ttk.Label(
            self,
            textvariable=self.status_var,
            wraplength=500,
        ).grid(
            row=7,
            column=0,
            sticky=tk.W,
        )

        self.columnconfigure(0, weight=1)

    def get_recipient_ids(self) -> list[str]:
        """Return unique, validated recipient chat IDs."""
        raw_text = self.recipient_text.get(
            "1.0",
            tk.END,
        ).strip()

        if not raw_text:
            raise ValueError("Enter at least one recipient chat ID.")

        candidates = re.split(r"[\s,;]+", raw_text)
        chat_ids: list[str] = []
        seen: set[str] = set()

        for candidate in candidates:
            if not candidate:
                continue

            if not candidate.lstrip("-").isdigit():
                raise ValueError(
                    f"Invalid recipient chat ID: {candidate}"
                )

            if candidate not in seen:
                chat_ids.append(candidate)
                seen.add(candidate)

        if not chat_ids:
            raise ValueError("Enter at least one valid recipient chat ID.")

        return chat_ids

    def get_message(self) -> str:
        """Return the message after validating its content and length."""
        message = self.message_text.get(
            "1.0",
            "end-1c",
        )

        if not message.strip():
            raise ValueError("Enter a message before submitting.")

        if len(message) > self.MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message exceeds {self.MAX_MESSAGE_LENGTH} characters."
            )

        return message

    def submit(self) -> None:
        """Validate inputs and invoke the registered callback."""
        try:
            chat_ids = self.get_recipient_ids()
            message = self.get_message()
        except ValueError as error:
            self.status_var.set(str(error))
            return

        self._on_submit(chat_ids, message)
        self.status_var.set(
            f"Submitted for {len(chat_ids)} recipient(s)."
        )

    def clear(self) -> None:
        """Clear the recipient and message fields."""
        self.recipient_text.delete("1.0", tk.END)
        self.message_text.delete("1.0", tk.END)
        self.character_count_var.set(
            f"0 / {self.MAX_MESSAGE_LENGTH}"
        )
        self.status_var.set("Ready")

    def set_status(self, message: str) -> None:
        """Display a status message supplied by the parent window."""
        self.status_var.set(message)

    def set_submission_enabled(self, enabled: bool) -> None:
        """Enable or disable the submit button."""
        self.send_button.configure(
            state=tk.NORMAL if enabled else tk.DISABLED
        )

    def _update_character_count(self, _event=None) -> None:
        """Refresh the message character counter."""
        message = self.message_text.get(
            "1.0",
            "end-1c",
        )

        self.character_count_var.set(
            f"{len(message)} / {self.MAX_MESSAGE_LENGTH}"
        )
