"""Base exceptions for the application."""

from __future__ import annotations

from typing import Any, Optional


class ChooseYourHardwareException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message
