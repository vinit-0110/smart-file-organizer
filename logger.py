"""
Smart File Organizer - Centralized Logger Module
Provides structured file logging and optional GUI streaming callbacks.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Callable


class QueueLogHandler(logging.Handler):
    """Custom logging handler that routes log records to a callback function for UI streaming."""
    
    def __init__(self, callback: Callable[[str, str], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            level = record.levelname
            if self.callback:
                self.callback(msg, level)
        except Exception:
            self.handleError(record)


def setup_logger(log_dir: Optional[str] = None, ui_callback: Optional[Callable[[str, str], None]] = None) -> logging.Logger:
    """
    Sets up and configures the main application logger.
    
    Args:
        log_dir: Directory path where app.log will be stored. Defaults to ./logs.
        ui_callback: Optional callback function receiving (log_message, level_name).
        
    Returns:
        Configured logging.Logger instance.
    """
    if log_dir is None:
        base_dir = Path(__file__).resolve().parent
        log_dir = str(base_dir / "logs")

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("SmartFileOrganizer")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File Handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logger: {e}", file=sys.stderr)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # UI Handler if provided
    if ui_callback:
        ui_handler = QueueLogHandler(ui_callback)
        ui_handler.setLevel(logging.INFO)
        ui_handler.setFormatter(formatter)
        logger.addHandler(ui_handler)

    return logger


# Default logger instance
logger = setup_logger()
