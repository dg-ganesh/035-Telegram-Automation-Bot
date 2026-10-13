"""
Project : Telegram Automation Bot
Project ID : 035

Module Name : Configuration Unit Tests

Purpose:
Test configuration loading, project metadata, optional Telegram token
handling, token format validation, and configuration validation.
"""

import os
import unittest
from unittest.mock import patch

from src.config import (
    AppConfig,
    load_config,
    validate_config,
    validate_telegram_token,
)


class TestConfiguration(unittest.TestCase):
    """Test application configuration and validation."""

    def test_load_config_returns_app_config(self):
        """Configuration loading returns an AppConfig instance."""
        config = load_config()

        self.assertIsInstance(config, AppConfig)

    def test_config_has_expected_project_details(self):
        """Configuration contains the expected project metadata."""
        config = load_config()

        self.assertEqual(
            config.application_name,
            "Telegram Automation Bot",
        )
        self.assertEqual(config.project_id, "035")
        self.assertEqual(config.application_version, "1.0.0")

    def test_config_has_project_root(self):
        """The project root exists and is a directory."""
        config = load_config()

        self.assertTrue(config.project_root.exists())
        self.assertTrue(config.project_root.is_dir())

    def test_missing_token_is_allowed(self):
        """The application can start without a Telegram token."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": ""},
        ):
            config = load_config()

        self.assertIsNone(config.telegram_token)

    def test_valid_token_format(self):
        """A syntactically valid token returns no validation error."""
        token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"

        self.assertIsNone(validate_telegram_token(token))

    def test_invalid_token_formats_are_rejected(self):
        """Malformed or empty tokens return validation errors."""
        invalid_tokens = [
            "",
            " ",
            "invalid-token",
            "123456789",
            ":ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            "123456789:",
            "abc123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
        ]

        for token in invalid_tokens:
            with self.subTest(token=token):
                self.assertIsNotNone(
                    validate_telegram_token(token)
                )

    def test_validate_config_accepts_default_configuration(self):
        """A valid default configuration returns no errors."""
        config = load_config()

        self.assertEqual(validate_config(config), [])


if __name__ == "__main__":
    unittest.main()