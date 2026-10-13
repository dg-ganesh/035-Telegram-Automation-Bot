"""
Project : Telegram Automation Bot
Project ID : 035

Module Name : Application Bootstrap

Purpose:
Initialize the application configuration and logging service,
launch the desktop GUI, and record execution status.
"""

import tkinter as tk

from src.config import load_config, validate_config
from src.services.logging_service import LoggingService
from src.ui.main_window import MainWindow


def main() -> int:
    """Initialize and run the desktop application."""
    config = load_config()

    config_errors = validate_config(config)
    if config_errors:
        for error in config_errors:
            print(f"Configuration error: {error}")
        return 1

    logging_service = LoggingService(config)
    logging_service.initialize()

    root = None

    try:
        logging_service.record_checkpoint(
            "Configuration loaded",
            True,
            "Application configuration initialized successfully.",
        )

        root = tk.Tk()

        MainWindow(
            root=root,
            config=config,
            logging_service=logging_service,
        )

        logging_service.record_checkpoint(
            "GUI initialized",
            True,
            "Main application window initialized successfully.",
        )

        root.mainloop()
        return 0

    except Exception as error:
        logging_service.record_error(
            error,
            "Application startup or runtime",
        )

        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass

        return 1

    finally:
        logging_service.finalize("PASS" if root is not None else "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())