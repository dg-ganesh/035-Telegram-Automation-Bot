
"""
Project : Telegram Automation Bot
Project ID : 035

Application Configuration
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Telegram Automation Bot"
APP_VERSION = "1.0.0"
PROJECT_ID = "035"

TOKEN_ENVIRONMENT_VARIABLE = "TELEGRAM_BOT_TOKEN"


def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Store application-wide configuration settings."""

    project_root: Path
    application_name: str = APP_NAME
    application_version: str = APP_VERSION
    project_id: str = PROJECT_ID

    logs_directory: Path | None = None
    execution_report_path: Path | None = None

    telegram_token: str | None = None
    request_timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        """Resolve standard paths when they are not supplied."""
        logs_directory = self.logs_directory

        if logs_directory is None:
            logs_directory = self.project_root / "logs"

        report_path = self.execution_report_path

        if report_path is None:
            report_path = logs_directory / "execution_report.txt"

        object.__setattr__(
            self,
            "logs_directory",
            Path(logs_directory),
        )
        object.__setattr__(
            self,
            "execution_report_path",
            Path(report_path),
        )

        object.__setattr__(
            self,
            "project_root",
            Path(self.project_root),
        )

        if self.telegram_token is not None:
            object.__setattr__(
                self,
                "telegram_token",
                self.telegram_token.strip(),
            )


def load_config(
    token_override: str | None = None,
) -> AppConfig:
    """
    Load application settings.

    A supplied token takes precedence over the environment variable.
    An absent token is permitted so that the GUI can start before
    the user configures Telegram connectivity.
    """
    project_root = get_project_root()

    if token_override is not None:
        telegram_token = token_override.strip()
    else:
        telegram_token = os.environ.get(
            TOKEN_ENVIRONMENT_VARIABLE,
            "",
        ).strip()

    return AppConfig(
        project_root=project_root,
        telegram_token=telegram_token or None,
    )


def validate_config(config: AppConfig) -> list[str]:
    """
    Validate application configuration.

    Return an empty list when all configured values are valid.
    A missing Telegram token is allowed during initial GUI startup.
    """
    errors: list[str] = []

    if not config.project_root.is_absolute():
        errors.append("The project root must be an absolute path.")

    if not config.application_name.strip():
        errors.append("The application name cannot be empty.")

    if not config.application_version.strip():
        errors.append("The application version cannot be empty.")

    if not config.project_id.strip():
        errors.append("The project ID cannot be empty.")

    if config.request_timeout_seconds <= 0:
        errors.append(
            "The request timeout must be greater than zero."
        )

    if config.telegram_token:
        token_error = validate_telegram_token(
            config.telegram_token
        )

        if token_error:
            errors.append(token_error)

    return errors


def validate_telegram_token(token: str) -> str | None:
    """
    Validate the basic structure of a Telegram bot token.

    This checks syntax only. Telegram must verify the token
    through the Bot API to establish whether it is valid.
    """
    candidate = token.strip()

    if not candidate:
        return "The Telegram bot token cannot be empty."

    if len(candidate) > 256:
        return "The Telegram bot token is too long."

    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", candidate):
        return "The Telegram bot token format is invalid."

    return None


# Public methods:
# - get_project_root() -> Path
# - load_config(token_override: str | None = None) -> AppConfig
# - validate_config(config: AppConfig) -> list[str]
# - validate_telegram_token(token: str) -> str | None
#
# Public signals:
# - None (this is a configuration module, not a UI module).
#
# Dependencies:
# - Python standard library: os, re, dataclasses, pathlib.
