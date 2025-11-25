"""Utility helpers for model analyzer."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Sequence


PRECISION_TO_BITS = {
    "fp32": 32,
    "float32": 32,
    "fp16": 16,
    "float16": 16,
    "bf16": 16,
    "bfloat16": 16,
    "int8": 8,
    "int4": 4,
}


class ValidationError(ValueError):
    """Raised when inputs are missing or inconsistent."""


def load_json(model_json: str) -> Dict[str, Any]:
    try:
        return json.loads(model_json)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc


def require_dict(obj: Any, name: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValidationError(f"{name} must be an object.")
    return obj


def require_int(obj: Dict[str, Any], key: str, *, positive: bool = False) -> int:
    if key not in obj:
        raise ValidationError(f"Missing required field '{key}'.")
    val = obj[key]
    if not isinstance(val, int):
        raise ValidationError(f"Field '{key}' must be an integer.")
    if positive and val <= 0:
        raise ValidationError(f"Field '{key}' must be positive.")
    return val


def require_bool(obj: Dict[str, Any], key: str) -> bool:
    if key not in obj:
        raise ValidationError(f"Missing required field '{key}'.")
    val = obj[key]
    if not isinstance(val, bool):
        raise ValidationError(f"Field '{key}' must be a boolean.")
    return val


def dtype_bits_from_string(precision: str) -> int:
    bits = PRECISION_TO_BITS.get(precision.lower())
    if bits is None:
        raise ValidationError(f"Unsupported precision string '{precision}'.")
    return bits


def shape_elements(shape: Sequence[Any], *, allow_none_leading: bool = True) -> int:
    """Return product of dimensions; if first dim is None and allow_none_leading, skip it."""
    dims: Iterable[Any]
    if allow_none_leading and shape and shape[0] is None:
        dims = shape[1:]
    else:
        dims = shape
    total = 1
    for dim in dims:
        if not isinstance(dim, int) or dim <= 0:
            raise ValidationError("All concrete dimensions must be positive integers.")
        total *= dim
    return total
