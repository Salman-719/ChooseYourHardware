"""Unit conversion utilities."""

from __future__ import annotations

from typing import Optional

from ..config import GB_TO_BYTES, TFLOPS_TO_FLOPS, TOPS_TO_OPS


def gb_to_bytes(gb: float) -> int:
    """Convert gigabytes to bytes.

    Args:
        gb: Value in gigabytes

    Returns:
        Value in bytes
    """
    return int(gb * GB_TO_BYTES)


def tflops_to_flops(tflops: Optional[float]) -> Optional[float]:
    """Convert teraFLOPS to FLOPS.

    Args:
        tflops: Value in teraFLOPS (can be None)

    Returns:
        Value in FLOPS or None
    """
    if tflops is None:
        return None
    return float(tflops) * TFLOPS_TO_FLOPS


def tops_to_ops(tops: Optional[float]) -> Optional[float]:
    """Convert teraOPS to OPS.

    Args:
        tops: Value in teraOPS (can be None)

    Returns:
        Value in OPS or None
    """
    if tops is None:
        return None
    return float(tops) * TOPS_TO_OPS


def apply_utilization(peak: Optional[float], fraction: float) -> Optional[float]:
    """Apply utilization fraction to peak performance.

    Args:
        peak: Peak performance value
        fraction: Utilization fraction (0.0 to 1.0)

    Returns:
        Sustained performance or None
    """
    if peak is None:
        return None
    return peak * fraction
