"""Validation utilities."""

from __future__ import annotations

import json
from typing import Any

from config.constants import DTYPE_BITS


def load_json(model_json: str) -> dict[str, Any]:
    """Load and parse JSON string.

    Args:
        model_json: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If JSON is invalid
    """
    try:
        return json.loads(model_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def require_dict(obj: Any, name: str) -> dict[str, Any]:
    """Require object to be a dictionary.

    Args:
        obj: Object to validate
        name: Field name for error message

    Returns:
        The validated dictionary

    Raises:
        ValueError: If obj is not a dictionary
    """
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be an object")
    return obj


def require_int(obj: dict[str, Any], key: str, *, positive: bool = False) -> int:
    """Require field to be an integer.

    Args:
        obj: Dictionary containing the field
        key: Field name
        positive: If True, require value to be positive

    Returns:
        The validated integer

    Raises:
        ValueError: If validation fails
    """
    if key not in obj:
        raise ValueError(f"Missing required field '{key}'")

    val = obj[key]
    if not isinstance(val, int):
        raise ValueError(f"Field '{key}' must be an integer")

    if positive and val <= 0:
        raise ValueError(f"Field '{key}' must be positive")

    return val


def require_bool(obj: dict[str, Any], key: str) -> bool:
    """Require field to be a boolean.

    Args:
        obj: Dictionary containing the field
        key: Field name

    Returns:
        The validated boolean

    Raises:
        ValueError: If validation fails
    """
    if key not in obj:
        raise ValueError(f"Missing required field '{key}'")

    val = obj[key]
    if not isinstance(val, bool):
        raise ValueError(f"Field '{key}' must be a boolean")

    return val


def require_positive_number(obj: dict[str, Any], key: str) -> float:
    """Require field to be a positive number (int or float).

    Args:
        obj: Dictionary containing the field
        key: Field name

    Returns:
        The validated number as float

    Raises:
        ValueError: If validation fails
    """
    if key not in obj:
        raise ValueError(f"Missing required field '{key}'")

    val = obj[key]
    if not isinstance(val, (int, float)) or val <= 0:
        raise ValueError(f"Field '{key}' must be a positive number")

    return float(val)


def dtype_bits_from_string(precision: str) -> int:
    """Convert precision string to bit width.

    Args:
        precision: Precision string (e.g., 'fp32', 'fp16')

    Returns:
        Bit width (8, 16, or 32)

    Raises:
        ValueError: If precision string is invalid
    """
    bits = DTYPE_BITS.get(precision.lower())
    if bits is None:
        raise ValueError(f"Unsupported precision string '{precision}'")
    return bits


def shape_elements(shape: list[int | None], *, allow_none_leading: bool = True) -> int:
    """Calculate total elements in a shape.

    Args:
        shape: List of dimensions
        allow_none_leading: If True, skip leading None dimension

    Returns:
        Product of all dimensions

    Raises:
        ValueError: If dimensions are invalid
    """
    dims = shape
    if allow_none_leading and shape and shape[0] is None:
        dims = shape[1:]

    total = 1
    for dim in dims:
        if not isinstance(dim, int) or dim <= 0:
            raise ValueError("All concrete dimensions must be positive integers")
        total *= dim

    return total
