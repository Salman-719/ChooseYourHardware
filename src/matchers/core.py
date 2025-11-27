"""Matcher that estimates latency per device using model and hardware analyzer outputs."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from config import SCENARIO_KINDS


def _scenario_flops(model: Dict[str, Any], decode_tokens: Optional[int] = None) -> float:
    scenario = model.get("inference_scenario") or {}
    scenario_kind = scenario.get("scenario_kind") or "single_pass"
    if scenario_kind not in SCENARIO_KINDS:
        raise ValueError(f"scenario_kind must be one of {SCENARIO_KINDS} (got {scenario_kind}).")

    extra = model.get("extra") or {}
    total_flops_field = model.get("total_flops")
    flops_per_inference = model.get("flops_per_inference")

    if scenario_kind in {"single_pass", "full_sequence"}:
        return float(total_flops_field or flops_per_inference or 0.0)

    if scenario_kind == "per_iteration":
        flops_iter = extra.get("flops_per_iteration")
        num_iter = extra.get("num_iterations")
        if flops_iter is None or num_iter is None:
            raise ValueError("per_iteration scenario requires extra.flops_per_iteration and extra.num_iterations.")
        return float(flops_iter) * float(num_iter)

    if scenario_kind == "full_sequence+decode":
        flops_prefill = model.get("flops_prefill")
        flops_decode = model.get("flops_per_token_decode")
        if flops_prefill is None or flops_decode is None:
            raise ValueError("full_sequence+decode scenario requires flops_prefill and flops_per_token_decode.")
        tokens = decode_tokens if decode_tokens is not None else (extra.get("decode_tokens") or 0)
        return float(flops_prefill) + float(tokens) * float(flops_decode)

    if scenario_kind == "per_token":
        if flops_per_inference is None:
            raise ValueError("per_token scenario requires flops_per_inference.")
        return float(flops_per_inference)

    raise ValueError(f"Unhandled scenario_kind {scenario_kind}")


def _choose_dtype(model: Dict[str, Any], hardware: Dict[str, Any]) -> Optional[str]:
    scenario = model.get("inference_scenario") or {}
    bits = scenario.get("precision_bits")
    precision = scenario.get("precision")
    desired: Optional[str]
    if precision in {"fp16", "bf16", "fp32"}:
        desired = precision
    elif bits == 8:
        desired = "int8"
    elif bits == 16:
        desired = "fp16"
    else:
        desired = "fp32"

    sustained_flops = hardware.get("sustained_flops_per_s") or {}
    sustained_ops = hardware.get("sustained_ops_per_s") or {}

    if desired == "int8":
        return "int8" if sustained_ops.get("int8") else None
    return desired if sustained_flops.get(desired) else None


def _memory_profile(model: Dict[str, Any], hardware: Dict[str, Any]) -> Tuple[bool, float, float]:
    """Return (feasible, stream_bytes, bandwidth_bytes_per_s)."""
    mem_model = hardware.get("memory_model")
    mem_cap = hardware.get("memory_capacity_bytes") or {}
    mem_bw = hardware.get("memory_bandwidth_bytes_per_s") or {}

    params_bytes = float(model.get("param_memory_bytes") or 0.0)
    act_bytes = float(model.get("activation_memory_bytes") or 0.0)
    kv_bytes = float(model.get("kv_cache_bytes") or 0.0)
    stream_bytes = float(model.get("total_stream_bytes") or (params_bytes + act_bytes))
    working_set = params_bytes + act_bytes + kv_bytes

    if mem_model == "separate":
        cap = float(mem_cap.get("vram") or 0.0)
        bw = float(mem_bw.get("vram") or 0.0)
    elif mem_model in {"cpu_only", "shared"}:
        cap = float(mem_cap.get("ram") or 0.0)
        bw = float(mem_bw.get("ram") or 0.0)
    else:
        return False, stream_bytes, 0.0

    feasible = working_set <= cap if cap > 0 else False
    return feasible, stream_bytes, bw


def _latency_overhead(model: Dict[str, Any], hardware: Dict[str, Any]) -> float:
    dram_lat = hardware.get("dram_latency_s")
    cache_lat = hardware.get("cache_latency_s")
    l3 = hardware.get("l3_cache_bytes") or 0
    dram_lat = dram_lat if isinstance(dram_lat, (int, float)) and dram_lat > 0 else None
    cache_lat = cache_lat if isinstance(cache_lat, (int, float)) and cache_lat > 0 else None
    if dram_lat is None or cache_lat is None:
        return 0.0
    act_bytes = float(model.get("activation_memory_bytes") or 0.0)
    if l3 and act_bytes <= l3:
        return float(cache_lat)
    return float(dram_lat)


def estimate_latency(model: Dict[str, Any], hardware: Dict[str, Any], *, decode_tokens: Optional[int] = None) -> float:
    """Estimate end-to-end latency (seconds) by selecting the dominant bottleneck."""
    latency, _ = calculate_inference_metrics(model, hardware, decode_tokens=decode_tokens)
    return latency


def calculate_inference_metrics(
    model: Dict[str, Any],
    hardware: Dict[str, Any],
    *,
    decode_tokens: Optional[int] = None,
) -> Tuple[float, str]:
    """Return (estimated_latency_seconds, bottleneck_label) or (inf, 'UNSUPPORTED') if infeasible."""
    try:
        dtype = _choose_dtype(model, hardware)
        if dtype is None:
            return float("inf"), "UNSUPPORTED"

        flops = _scenario_flops(model, decode_tokens=decode_tokens)
        if dtype == "int8":
            perf_map = hardware.get("sustained_ops_per_s") or {}
            peak_map = hardware.get("peak_ops_per_s") or {}
        else:
            perf_map = hardware.get("sustained_flops_per_s") or {}
            peak_map = hardware.get("peak_flops_per_s") or {}

        # Prefer sustained numbers; fall back to peak if utilization was omitted.
        base_perf = perf_map.get(dtype) or peak_map.get(dtype)
        if not base_perf or base_perf <= 0:
            return float("inf"), "UNSUPPORTED"

        feasible_mem, stream_bytes, bw = _memory_profile(model, hardware)
        if not feasible_mem:
            return float("inf"), "OUT_OF_MEMORY"
        t_bw = stream_bytes / bw if bw and stream_bytes else 0.0

        # Roofline: compute time is whichever is larger, pure compute or bandwidth-bound.
        t_compute_peak = flops / base_perf
        t_compute = max(t_compute_peak, t_bw)
        t_lat = _latency_overhead(model, hardware)

        t_total = t_compute + t_lat
        parts = {"COMPUTE": t_compute_peak, "MEMORY_BANDWIDTH": t_bw, "MEMORY_LATENCY": t_lat}
        bottleneck = max(parts.items(), key=lambda kv: kv[1])[0]
        return t_total, bottleneck
    except Exception:
        return float("inf"), "UNSUPPORTED"
