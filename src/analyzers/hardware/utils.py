"""Shared validation and conversion utilities."""

from __future__ import annotations

from typing import Any, Dict


class ValidationError(Exception):
    """Raised when inputs are missing or invalid."""


def require_positive_number(obj: Dict[str, Any], key: str) -> float:
    if key not in obj:
        raise ValidationError(f"Missing required field '{key}'.")
    val = obj[key]
    if not isinstance(val, (int, float)) or val <= 0:
        raise ValidationError(f"Field '{key}' must be a positive number.")
    return float(val)


def require_int(obj: Dict[str, Any], key: str, *, positive: bool = False) -> int:
    if key not in obj:
        raise ValidationError(f"Missing required field '{key}'.")
    val = obj[key]
    if not isinstance(val, int):
        raise ValidationError(f"Field '{key}' must be an integer.")
    if positive and val <= 0:
        raise ValidationError(f"Field '{key}' must be positive.")
    return val


def require_bool(obj: Dict[str, Any], key: str, default: bool | None = None) -> bool:
    if key not in obj:
        if default is None:
            raise ValidationError(f"Missing required field '{key}'.")
        return default
    val = obj[key]
    if not isinstance(val, bool):
        raise ValidationError(f"Field '{key}' must be a boolean.")
    return val


def gb_to_bytes(gb: float) -> int:
    return int(gb * 1e9)


def tflops_to_flops(tflops: float | None) -> float | None:
    if tflops is None:
        return None
    return float(tflops) * 1e12


def tops_to_ops(tops: float | None) -> float | None:
    if tops is None:
        return None
    return float(tops) * 1e12


def apply_util(peak: float | None, frac: float) -> float | None:
    if peak is None:
        return None
    return peak * frac


def validate_util_fraction(val: Any, name: str) -> float:
    if not isinstance(val, (int, float)) or not (0 <= val <= 1):
        raise ValidationError(f"{name} must be between 0 and 1.")
    return float(val)


def resolve_utils(defaults: Dict[str, Any] | None) -> Dict[str, float]:
    """Resolve utilization fractions; all four must be provided explicitly."""
    if defaults is None:
        raise ValidationError("defaults must include utilization fractions for fp32/fp16/bf16/int8.")
    mapping = {
        "sustained_utilization_fraction_fp32": "fp32",
        "sustained_utilization_fraction_fp16": "fp16",
        "sustained_utilization_fraction_bf16": "bf16",
        "sustained_utilization_fraction_int8": "int8",
    }
    util: Dict[str, float] = {}
    missing = []
    for key, target in mapping.items():
        if key not in defaults:
            missing.append(key)
            continue
        util[target] = validate_util_fraction(defaults[key], key)
    if missing:
        raise ValidationError(f"Missing utilization fractions: {', '.join(missing)}.")
    return util


def normalize_latency_seconds(spec: Dict[str, Any], kind: str) -> float:
    """Normalize a latency field to seconds. Accepts *_ns or *_s; requires one."""
    ns_key = f"{kind}_latency_ns"
    s_key = f"{kind}_latency_s"
    if s_key in spec:
        val = spec[s_key]
        if not isinstance(val, (int, float)) or val <= 0:
            raise ValidationError(f"{s_key} must be a positive number when provided.")
        return float(val)
    if ns_key in spec:
        val = spec[ns_key]
        if not isinstance(val, (int, float)) or val <= 0:
            raise ValidationError(f"{ns_key} must be a positive number when provided.")
        return float(val) * 1e-9
    raise ValidationError(f"Missing required latency field: provide {s_key} or {ns_key}.")
