"""Model-related exceptions."""

from __future__ import annotations

from typing import Any, Optional

from .base import ChooseYourHardwareException


class ModelValidationError(ChooseYourHardwareException):
    """Raised when model specification is invalid."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """Initialize model validation error.

        Args:
            message: Error message
            field: Field that caused the error
            value: Invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, details)


class ModelAnalysisError(ChooseYourHardwareException):
    """Raised when model analysis fails."""

    pass
