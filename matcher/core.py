"""Bandwidth-aware model-to-hardware matcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class MatcherError(ValueError):
    """Raised when inputs are missing or inconsistent."""


@dataclass
class WorstCase:
    batch_size: int
    sequence_length: Optional[int]
    qps: float
    latency_seconds: float


def _require_dict(obj: Any, name: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise MatcherError(f"{name} must be an object.")
    return obj


def _require_positive_int(val: Any, name: str) -> int:
    if not isinstance(val, int) or val <= 0:
        raise MatcherError(f"{name} must be a positive integer.")
    return val


def _require_positive_number(val: Any, name: str) -> float:
    if not isinstance(val, (int, float)) or val <= 0:
        raise MatcherError(f"{name} must be a positive number.")
    return float(val)


def _normalize_hw_list(hardware_report: Any) -> List[Dict[str, Any]]:
    if isinstance(hardware_report, dict) and "hardware_analysis" in hardware_report:
        return hardware_report["hardware_analysis"]
    if isinstance(hardware_report, list):
        return hardware_report
    raise MatcherError("hardware_analysis must be a list or an object with hardware_analysis.")


def _select_dtype(model_bits: int, support: Dict[str, bool]) -> str:
    if model_bits == 32:
        return "fp32"
    if model_bits == 16:
        if support.get("fp16"):
            return "fp16"
        if support.get("bf16"):
            return "bf16"
        return "fp32"
    if model_bits == 8:
        if support.get("int8"):
            return "int8"
        if support.get("fp16"):
            return "fp16"
        return "fp32"
    raise MatcherError("Unsupported dtype_bits.")


def _sustained_rate(hw_norm: Dict[str, Any], dtype: str) -> Optional[float]:
    if dtype == "int8":
        return hw_norm.get("sustained_ops_per_s", {}).get("int8")
    return hw_norm.get("sustained_flops_per_s", {}).get(dtype)


def _memory_capacity_for_model(hw_norm: Dict[str, Any]) -> Optional[int]:
    mem_model = hw_norm.get("memory_model")
    mem_caps = hw_norm.get("memory_capacity_bytes", {})
    if mem_model == "separate":
        return mem_caps.get("vram")
    if mem_model == "shared":
        return mem_caps.get("ram")
    return mem_caps.get("ram")


def _bandwidth_for_model(hw_norm: Dict[str, Any]) -> Optional[float]:
    mem_model = hw_norm.get("memory_model")
    bandwidths = hw_norm.get("memory_bandwidth_bytes_per_s", {})
    if mem_model == "separate":
        return bandwidths.get("vram") or bandwidths.get("ram")
    return bandwidths.get("ram")


def _validate_worst_case(model: Dict[str, Any], requirements: Dict[str, Any]) -> WorstCase:
    inf = model.get("inference_scenario", {})
    wc = _require_dict(requirements.get("worst_case"), "requirements.worst_case")
    bs = _require_positive_int(wc.get("batch_size"), "requirements.worst_case.batch_size")
    seq = wc.get("sequence_length")
    if seq is not None:
        seq = _require_positive_int(seq, "requirements.worst_case.sequence_length")
    qps = _require_positive_number(wc.get("qps"), "requirements.worst_case.qps")
    lat = _require_positive_number(wc.get("latency_seconds"), "requirements.worst_case.latency_seconds")

    ms_seq = inf.get("sequence_length")
    if inf.get("batch_size") != bs:
        raise MatcherError("Model inference_scenario must match requirements.worst_case (batch_size, sequence_length).")
    if ms_seq is None and seq is not None:
        raise MatcherError("Model inference_scenario must match requirements.worst_case (batch_size, sequence_length).")
    if ms_seq is not None and seq != ms_seq:
        raise MatcherError("Model inference_scenario must match requirements.worst_case (batch_size, sequence_length).")
    return WorstCase(batch_size=bs, sequence_length=seq, qps=qps, latency_seconds=lat)


def match_model_to_hardware(matcher_input: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate hardware candidates given matcher input schema."""
    model = _require_dict(matcher_input.get("model"), "model")
    hardware_report = matcher_input.get("hardware_analysis")
    requirements = _require_dict(matcher_input.get("requirements"), "requirements")

    hw_list = _normalize_hw_list(hardware_report)
    wc = _validate_worst_case(model, requirements)

    constraints = _require_dict(requirements.get("constraints"), "requirements.constraints")
    max_cost = constraints.get("max_hourly_cost_usd")
    allowed_regions = constraints.get("allowed_regions", [])
    disallow_kinds = constraints.get("disallow_kinds", [])

    dtype_bits = model.get("dtype_bits") or model.get("inference_scenario", {}).get("precision_bits")
    if dtype_bits not in (8, 16, 32):
        raise MatcherError("Model dtype_bits must be 8, 16, or 32.")
    intensity = model.get("intensity", {}).get("avg_flops_per_byte")
    if intensity is None:
        raise MatcherError("Model intensity.avg_flops_per_byte is required.")
    param_bytes = model.get("param_memory_bytes")
    act_bytes = model.get("activation_memory_bytes")
    kv_bytes = model.get("kv_cache_bytes", 0)
    if param_bytes is None or act_bytes is None:
        raise MatcherError("Model must include param_memory_bytes and activation_memory_bytes.")
    model_total_bytes = int(param_bytes) + int(act_bytes) + int(kv_bytes)
    flops_per_inference = float(model.get("flops_per_inference") or 0.0)

    candidates: List[Dict[str, Any]] = []
    for hw in hw_list:
        norm = hw.get("normalized", hw)
        kind = hw.get("kind")

        if kind in disallow_kinds:
            continue

        cost = norm.get("cost_usd_per_hour")
        if max_cost is not None and cost is not None and cost > max_cost:
            continue

        region = norm.get("region")
        if allowed_regions:
            if region is None or region not in allowed_regions:
                continue

        dtype = _select_dtype(dtype_bits, norm.get("dtype_support", {}))
        compute_rate = _sustained_rate(norm, dtype)
        if compute_rate is None or compute_rate <= 0:
            continue

        bw = _bandwidth_for_model(norm)
        if bw is not None and intensity > 0:
            memory_rate = bw * intensity
            effective_rate = min(compute_rate, memory_rate)
        else:
            effective_rate = compute_rate
        if effective_rate is None or effective_rate <= 0:
            continue

        fits_memory = False
        cap = _memory_capacity_for_model(norm)
        if cap is not None and model_total_bytes <= cap:
            fits_memory = True
        if not fits_memory:
            continue

        latency_bound = flops_per_inference / effective_rate if effective_rate else None
        if latency_bound is None:
            continue
        ok_latency = latency_bound <= wc.latency_seconds
        qps_capacity = 1.0 / latency_bound if latency_bound > 0 else 0.0
        ok_qps = qps_capacity >= wc.qps
        if not (ok_latency and ok_qps):
            continue

        candidates.append(
            {
                "hardware_id": hw.get("hardware_id"),
                "kind": kind,
                "vendor": hw.get("vendor"),
                "model_name": hw.get("model_name"),
                "fits_memory": fits_memory,
                "latency_seconds_bound": latency_bound,
                "qps_capacity_bound": qps_capacity,
                "cost_usd_per_hour": cost,
                "region": region,
                "complexity_score": norm.get("complexity_score"),
            }
        )

    candidates.sort(key=lambda c: c["latency_seconds_bound"])

    return {
        "model": model,
        "requirements": requirements,
        "candidates": candidates,
    }
