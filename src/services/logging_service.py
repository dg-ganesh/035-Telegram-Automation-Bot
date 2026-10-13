
"""
Project : Telegram Automation Bot
Project ID : 035

Runtime Logging and Execution Report
"""

import logging
import time
import traceback
from datetime import datetime
from pathlib import Path

from src.config import AppConfig


class LoggingService:
    """Manage application logging and execution reports."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = logging.getLogger("telegram_automation_bot")
        self.report_path = config.execution_report_path
        self.start_time: datetime | None = None
        self.start_monotonic: float | None = None
        self.last_successful_checkpoint = "None"
        self.checkpoints: list[dict[str, str]] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize log directories, logging, and the execution report."""
        self.config.logs_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s"
            )

            file_handler = logging.FileHandler(
                self.config.logs_directory / "application.log",
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        self.start_time = datetime.now().astimezone()
        self.start_monotonic = time.monotonic()
        self.last_successful_checkpoint = "None"
        self.checkpoints.clear()
        self._initialized = True

        self.logger.info(
            "Starting %s version %s",
            self.config.application_name,
            self.config.application_version,
        )

        self._write_report(
            status="RUNNING",
            error_information="None",
        )

    def record_checkpoint(
        self,
        checkpoint_name: str,
        passed: bool,
        details: str = "",
    ) -> None:
        """Record a PASS or FAIL checkpoint and update the report."""
        self._ensure_initialized()

        status = "PASS" if passed else "FAIL"
        safe_details = self._sanitize(details)

        checkpoint = {
            "name": checkpoint_name,
            "status": status,
            "details": safe_details,
            "timestamp": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
        }
        self.checkpoints.append(checkpoint)

        if passed:
            self.last_successful_checkpoint = checkpoint_name
            self.logger.info(
                "CHECKPOINT PASS: %s | %s",
                checkpoint_name,
                safe_details,
            )
        else:
            self.logger.error(
                "CHECKPOINT FAIL: %s | %s",
                checkpoint_name,
                safe_details,
            )

        self._write_report(
            status="RUNNING" if passed else "FAIL",
            error_information=(
                safe_details if not passed else "None"
            ),
        )

    def record_error(
        self,
        error: BaseException,
        checkpoint_name: str = "Unhandled error",
    ) -> None:
        """Record an exception and its traceback."""
        self._ensure_initialized()

        error_details = (
            f"{type(error).__name__}: {error}\n"
            f"{traceback.format_exc()}"
        )

        self.logger.exception(
            "Application error at checkpoint: %s",
            checkpoint_name,
        )

        self.checkpoints.append(
            {
                "name": checkpoint_name,
                "status": "FAIL",
                "details": self._sanitize(error_details),
                "timestamp": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
            }
        )

        self._write_report(
            status="FAIL",
            error_information=self._sanitize(error_details),
        )

    def finalize(self, status: str = "PASS") -> None:
        """Finalize the report with the overall execution result."""
        self._ensure_initialized()

        normalized_status = status.strip().upper()

        if normalized_status not in {"PASS", "FAIL", "STOPPED"}:
            raise ValueError(
                "Final status must be PASS, FAIL, or STOPPED."
            )

        if any(
            checkpoint["status"] == "FAIL"
            for checkpoint in self.checkpoints
        ):
            normalized_status = "FAIL"

        self._write_report(
            status=normalized_status,
            error_information="None",
        )

        self.logger.info(
            "Execution finished with status %s",
            normalized_status,
        )

    def get_logger(self) -> logging.Logger:
        """Return the configured application logger."""
        return self.logger

    def _write_report(
        self,
        status: str,
        error_information: str,
    ) -> None:
        """Write the complete current execution report."""
        if self.start_time is None or self.start_monotonic is None:
            raise RuntimeError(
                "Logging service has not been initialized."
            )

        duration = time.monotonic() - self.start_monotonic
        end_time = datetime.now().astimezone()

        lines = [
            "=" * 72,
            self.config.application_name,
            "Project ID: " + self.config.project_id,
            "Application version: "
            + self.config.application_version,
            "=" * 72,
            f"Execution start time: {self.start_time.isoformat()}",
            f"Report updated: {end_time.isoformat()}",
            f"Execution duration (seconds): {duration:.3f}",
            f"Overall status: {status}",
            "Last successful checkpoint: "
            + self.last_successful_checkpoint,
            "",
            "EXECUTION CHECKPOINTS",
            "-" * 72,
        ]

        if not self.checkpoints:
            lines.append("No checkpoints recorded.")

        for index, checkpoint in enumerate(self.checkpoints, start=1):
            lines.extend(
                [
                    (
                        f"{index}. [{checkpoint['status']}] "
                        f"{checkpoint['name']}"
                    ),
                    f"   Timestamp: {checkpoint['timestamp']}",
                    f"   Details: {checkpoint['details'] or 'None'}",
                ]
            )

        lines.extend(
            [
                "",
                "ERROR INFORMATION",
                "-" * 72,
                self._sanitize(error_information) or "None",
                "",
            ]
        )

        self.report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.report_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    @staticmethod
    def _sanitize(value: str) -> str:
        """Prevent accidental token disclosure in log messages."""
        return value.replace("\r", " ").strip()

    def _ensure_initialized(self) -> None:
        """Reject operations before initialization."""
        if not self._initialized:
            raise RuntimeError(
                "Call initialize() before using the logging service."
            )


# Public methods:
# - initialize() -> None
# - record_checkpoint(checkpoint_name, passed, details="") -> None
# - record_error(error, checkpoint_name="Unhandled error") -> None
# - finalize(status="PASS") -> None
# - get_logger() -> logging.Logger
#
# Public signals:
# - None (this is a service module, not a UI module).
#
# Dependencies:
# - Python standard library: logging, time, traceback, datetime, pathlib.
# - Internal dependency: src.config.AppConfig.
