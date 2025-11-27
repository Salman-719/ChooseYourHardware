"""Universal matcher to estimate end-to-end latency across model types.

The matcher considers three potential bottlenecks:
- Compute roof: total FLOPs / sustained FLOPs.
- Bandwidth roof: total streamed bytes / memory bandwidth.
- Latency roof: pointer-chase count * (cache or DRAM latency).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from config import SCENARIO_KINDS


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


def _scenario_flops(model: Dict[str, Any]) -> float:
    scenario = model.get("inference_scenario") or {}
    scenario_kind = scenario.get("scenario_kind")
    if scenario_kind not in SCENARIO_KINDS:
        raise ValueError(f"scenario_kind must be one of {SCENARIO_KINDS} (got {scenario_kind}).")

    extra = model.get("extra") or {}
    total_flops_field = model.get("total_flops")
    flops_per_inference = model.get("flops_per_inference")

    if scenario_kind == "single_pass":
        if total_flops_field is None and flops_per_inference is None:
            raise ValueError("single_pass scenario requires total_flops or flops_per_inference.")
        return float(total_flops_field or flops_per_inference or 0.0)

    if scenario_kind == "per_iteration":
        flops_iter = extra.get("flops_per_iteration")
        num_iter = extra.get("num_iterations")
        if flops_iter is None or num_iter is None:
            raise ValueError("per_iteration scenario requires extra.flops_per_iteration and extra.num_iterations.")
        return float(flops_iter) * float(num_iter)

    if scenario_kind == "full_sequence":
        if total_flops_field is None and flops_per_inference is None:
            raise ValueError("full_sequence scenario requires total_flops or flops_per_inference.")
        return float(total_flops_field or flops_per_inference or 0.0)

    if scenario_kind == "full_sequence+decode":
        flops_prefill = model.get("flops_prefill")
        flops_decode = model.get("flops_per_token_decode")
        if flops_prefill is None or flops_decode is None:
            raise ValueError("full_sequence+decode scenario requires flops_prefill and flops_per_token_decode.")
        decode_tokens = extra.get("decode_tokens")
        if decode_tokens is not None:
            return float(flops_prefill) + float(decode_tokens) * float(flops_decode)
        return float(flops_prefill)

    if scenario_kind == "per_token":
        if flops_per_inference is None:
            raise ValueError("per_token scenario requires flops_per_inference.")
        return float(flops_per_inference)

    raise ValueError(f"Unhandled scenario_kind {scenario_kind}")


def estimate_latency(model: Dict[str, Any], hardware: Dict[str, Any]) -> float:
    """Estimate end-to-end latency (seconds) by selecting the dominant bottleneck."""
    latency, _ = calculate_inference_metrics(model, hardware)
    return latency


def calculate_inference_metrics(model: Dict[str, Any], hardware: Dict[str, Any]) -> Tuple[float, str]:
    """Return (estimated_latency_seconds, bottleneck_label)."""
    total_flops = _scenario_flops(model)
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
    cache_latency_s = hardware.get("cache_latency_s")
    dram_latency_s = hardware.get("dram_latency_s")
    cache_latency_s = cache_latency_s if isinstance(cache_latency_s, (int, float)) and cache_latency_s > 0 else None
    dram_latency_s = dram_latency_s if isinstance(dram_latency_s, (int, float)) and dram_latency_s > 0 else None
    latency_per_jump_s = 0.0
    if dram_latency_s is not None and cache_latency_s is not None:
        is_in_cache = bool(l3_cache_bytes and model.get("param_memory_bytes", 0) < l3_cache_bytes)
        latency_per_jump_s = cache_latency_s if is_in_cache else dram_latency_s
    t_latency = total_jumps * latency_per_jump_s

    estimated = max(t_compute, t_bandwidth, t_latency)
    if estimated == t_compute:
        bottleneck = "COMPUTE"
    elif estimated == t_bandwidth:
        bottleneck = "MEMORY_BANDWIDTH"
    else:
        bottleneck = "MEMORY_LATENCY"
    return estimated, bottleneck
