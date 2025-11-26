"""Configuration package."""

from .constants import (
    DISTANCE_METRICS,
    DTYPE_BITS,
    GB_TO_BYTES,
    HARDWARE_KINDS,
    MODEL_TYPES,
    SELECTION_ALGORITHMS,
    SCENARIO_KINDS,
    TFLOPS_TO_FLOPS,
    TOPS_TO_OPS,
)
from .settings import Settings, get_settings, settings

__all__ = [
    "settings",
    "Settings",
    "get_settings",
    "DTYPE_BITS",
    "HARDWARE_KINDS",
    "MODEL_TYPES",
    "GB_TO_BYTES",
    "TFLOPS_TO_FLOPS",
    "TOPS_TO_OPS",
    "DISTANCE_METRICS",
    "SELECTION_ALGORITHMS",
    "SCENARIO_KINDS",
]
