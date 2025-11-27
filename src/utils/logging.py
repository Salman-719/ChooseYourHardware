"""Logging configuration."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO", format_type: str = "text") -> logging.Logger:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("text" or "json")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("choose_your_hardware")
    logger.setLevel(level.upper())

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level.upper())

    # Format
    if format_type == "json":
        # For production - structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # For development - human-readable
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"choose_your_hardware.{name}")
