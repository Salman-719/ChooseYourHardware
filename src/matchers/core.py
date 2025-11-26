"""Universal matcher to estimate end-to-end latency across model types.

The matcher considers three potential bottlenecks:
- Compute roof: total FLOPs / sustained FLOPs.
- Bandwidth roof: total streamed bytes / memory bandwidth.
- Latency roof: pointer-chase count * (cache or DRAM latency).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _pick_dtype_key(model: Dict[str, Any]) -> str:
    """Pick dtype key for FLOP lookup based on model precision."""
    scenario = model.get("inference_scenario", {})
    bits = scenario.get("precision_bits")
    if bits == 16:
        return "fp16"
    if bits == 8:
        return "int8"
    return "fp32"


def _sustained_flops(hardware: Dict[str, Any], dtype_key: str) -> Optional[float]:
    sustained = hardware.get("sustained_flops_per_s") or {}
    val = sustained.get(dtype_key)
    if val is None:
        # Fallback to any available dtype
        for k in ("fp32", "fp16", "bf16"):
            if sustained.get(k) is not None:
                return sustained[k]
    return val


def _memory_bandwidth_bytes_per_s(hardware: Dict[str, Any]) -> Optional[float]:
    bw = hardware.get("memory_bandwidth_bytes_per_s") or {}
    # Prefer on-device bandwidth when present, otherwise fall back to RAM.
    return bw.get("vram") or bw.get("ram")


def estimate_latency(model: Dict[str, Any], hardware: Dict[str, Any]) -> float:
    """Estimate end-to-end latency (seconds) by selecting the dominant bottleneck."""
    latency, _ = calculate_inference_metrics(model, hardware)
    return latency


def calculate_inference_metrics(model: Dict[str, Any], hardware: Dict[str, Any]) -> Tuple[float, str]:
    """Return (estimated_latency_seconds, bottleneck_label)."""
    total_flops = model.get("total_flops") or model.get("flops_per_inference") or 0.0
    total_stream_bytes = model.get("total_stream_bytes") or model.get("param_memory_bytes") or 0.0
    total_jumps = model.get("total_jumps", 0) or 0

    dtype_key = _pick_dtype_key(model)
    peak_flops = _sustained_flops(hardware, dtype_key)
    bandwidth = _memory_bandwidth_bytes_per_s(hardware)

    # Compute roof: FLOPs / sustained throughput.
    t_compute = (total_flops / peak_flops) if peak_flops and total_flops else 0.0

    # Bandwidth roof: streamed bytes / memory bandwidth.
    t_bandwidth = (total_stream_bytes / bandwidth) if bandwidth and total_stream_bytes else 0.0

    l3_cache_bytes = hardware.get("l3_cache_bytes") or 0
    cache_latency_ns = hardware.get("cache_latency_ns") or 5.0
    dram_latency_ns = hardware.get("dram_latency_ns") or 100.0
    # Allow seconds inputs when provided.
    cache_latency_seconds = hardware.get("cache_latency_seconds")
    dram_latency_seconds = hardware.get("memory_latency_seconds")
    if isinstance(cache_latency_seconds, (int, float)) and cache_latency_seconds > 0:
        cache_latency_ns = cache_latency_seconds * 1e9
    if isinstance(dram_latency_seconds, (int, float)) and dram_latency_seconds > 0:
        dram_latency_ns = dram_latency_seconds * 1e9
    is_in_cache = bool(l3_cache_bytes and model.get("param_memory_bytes", 0) < l3_cache_bytes)
    latency_per_jump_s = (cache_latency_ns if is_in_cache else dram_latency_ns) * 1e-9
    t_latency = total_jumps * latency_per_jump_s

    estimated = max(t_compute, t_bandwidth, t_latency)
    if estimated == t_compute:
        bottleneck = "COMPUTE"
    elif estimated == t_bandwidth:
        bottleneck = "MEMORY_BANDWIDTH"
    else:
        bottleneck = "MEMORY_LATENCY"
    return estimated, bottleneck
