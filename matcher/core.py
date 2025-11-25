"""Model-to-hardware matcher built on analyzer outputs.

The matcher consumes:
- A model cost report (output of model_analyzer.analyze_model parsed to dict).
- A hardware normalization report (output of hardware_analyzer.analyze_hardware_spec).

It applies simple policies:
- Map model dtype_bits to hardware dtype keys (fp32, fp16, bf16, int8) with fallbacks.
- Check memory fit against the correct pool depending on hardware kind.
- Use sustained (not peak) throughput to estimate latency/QPS.
- Optionally allow intra-node sharding (multi-GPU) and cross-node distributed use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class MatcherError(ValueError):
    """Raised when inputs are missing or inconsistent."""


@dataclass
class ModelRequirements:
    dtype_bits: int
    dtype_key_preference: List[str]
    param_bytes: int
    activation_peak_bytes: int
    kv_cache_bytes: int
    total_bytes: int
    flops_per_inference: float


@dataclass
class MemoryAssessment:
    status: str  # fit_vram, fit_ram, fit_shared, fit_sharded_vram, offload, insufficient, requires_distributed
    detail: str
    pool: Optional[str]  # vram, ram, shared, cluster_vram, cluster_ram, offload, none


def _get_model_dtype_bits(model: Dict[str, Any]) -> int:
    bits = model.get("dtype_bits")
    if bits is None:
        bits = model.get("inference_scenario", {}).get("precision_bits")
    if not isinstance(bits, int) or bits not in (8, 16, 32):
        raise MatcherError("Model dtype_bits must be 8, 16, or 32.")
    return bits


def _preferred_dtype_keys(model_bits: int) -> List[str]:
    if model_bits == 32:
        return ["fp32"]
    if model_bits == 16:
        return ["fp16", "bf16", "fp32"]
    if model_bits == 8:
        return ["int8", "fp16", "bf16", "fp32"]
    raise MatcherError(f"Unsupported dtype_bits {model_bits}.")


def _bytes_from_count(count: Optional[int], dtype_bits: int) -> int:
    if count is None:
        return 0
    dtype_bytes = dtype_bits // 8
    return int(count) * dtype_bytes


def _model_requirements(model: Dict[str, Any]) -> ModelRequirements:
    dtype_bits = _get_model_dtype_bits(model)
    pref_keys = _preferred_dtype_keys(dtype_bits)

    param_bytes = model.get("param_memory_bytes")
    if param_bytes is None:
        param_bytes = _bytes_from_count(model.get("param_count"), dtype_bits)
    activation_peak_bytes = (
        model.get("activation_memory_bytes")
        or model.get("activation_peak_bytes")
        or 0
    )
    kv_cache_bytes = model.get("kv_cache_bytes") or 0
    total_bytes = int(param_bytes or 0) + int(activation_peak_bytes or 0) + int(kv_cache_bytes or 0)

    flops_per_inference = float(model.get("flops_per_inference") or 0.0)

    return ModelRequirements(
        dtype_bits=dtype_bits,
        dtype_key_preference=pref_keys,
        param_bytes=int(param_bytes or 0),
        activation_peak_bytes=int(activation_peak_bytes or 0),
        kv_cache_bytes=int(kv_cache_bytes or 0),
        total_bytes=total_bytes,
        flops_per_inference=flops_per_inference,
    )


def _select_dtype(hw_support: Dict[str, bool], preferred: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return chosen dtype key and fallback note (if any)."""
    for idx, key in enumerate(preferred):
        if hw_support.get(key):
            if idx == 0:
                return key, None
            return key, f"fell back to {key} (missing {preferred[0]})"
    return None, "no supported dtype"


def _sustained_rate(hw: Dict[str, Any], dtype_key: str) -> Optional[float]:
    if dtype_key == "int8":
        return hw.get("sustained_ops_per_s", {}).get("int8")
    return hw.get("sustained_flops_per_s", {}).get(dtype_key)


def _fits(capacity: Optional[int], needed: int) -> bool:
    return capacity is not None and capacity > 0 and needed <= capacity


def _assess_memory(
    hw: Dict[str, Any],
    needed_bytes: int,
    allow_multi_gpu_shard: bool,
    allow_cross_node: bool,
) -> MemoryAssessment:
    kind = hw.get("kind")
    mem = hw.get("memory_capacity_bytes", {})
    ram = mem.get("ram")
    vram = mem.get("vram")
    num_gpus = hw.get("num_gpus")

    if needed_bytes == 0:
        return MemoryAssessment(status="fit_ram", detail="No model memory required", pool="ram")

    if kind == "cpu_node":
        if _fits(ram, needed_bytes):
            return MemoryAssessment(status="fit_ram", detail="Fits in system RAM", pool="ram")
        return MemoryAssessment(status="insufficient", detail="Not enough system RAM", pool=None)

    if kind in {"gpu", "accelerator", "tpu"}:
        if _fits(vram, needed_bytes):
            return MemoryAssessment(status="fit_vram", detail="Fits in device VRAM", pool="vram")
        if _fits(ram, needed_bytes):
            return MemoryAssessment(
                status="offload",
                detail="Does not fit in VRAM; would require CPU RAM/offload",
                pool="ram",
            )
        return MemoryAssessment(status="insufficient", detail="Not enough VRAM or RAM", pool=None)

    if kind in {"jetson", "soc"}:
        shared_cap = vram if vram is not None else ram
        if _fits(shared_cap, needed_bytes):
            return MemoryAssessment(status="fit_shared", detail="Fits in shared memory pool", pool="shared")
        return MemoryAssessment(status="insufficient", detail="Not enough shared RAM/VRAM", pool=None)

    if kind == "multi_gpu_node":
        if allow_multi_gpu_shard:
            if _fits(vram, needed_bytes):
                return MemoryAssessment(status="fit_sharded_vram", detail="Fits across GPUs (sharded)", pool="vram")
        else:
            per_gpu = vram / num_gpus if num_gpus and vram else None
            if _fits(per_gpu, needed_bytes):
                return MemoryAssessment(status="fit_vram", detail="Fits within a single GPU's VRAM (estimated)", pool="vram")
        if _fits(ram, needed_bytes):
            return MemoryAssessment(
                status="offload",
                detail="VRAM insufficient; fits in system RAM (would need CPU/offload)",
                pool="ram",
            )
        return MemoryAssessment(status="insufficient", detail="Not enough VRAM or RAM on node", pool=None)

    if kind == "cluster":
        if not allow_cross_node:
            return MemoryAssessment(status="requires_distributed", detail="Cross-node parallelism disabled", pool=None)
        if _fits(vram, needed_bytes):
            return MemoryAssessment(status="fit_cluster_vram", detail="Fits in aggregated cluster VRAM", pool="cluster_vram")
        if _fits(ram, needed_bytes):
            return MemoryAssessment(status="fit_cluster_ram", detail="Fits in aggregated cluster RAM", pool="cluster_ram")
        return MemoryAssessment(status="insufficient", detail="Not enough aggregated cluster memory", pool=None)

    return MemoryAssessment(status="insufficient", detail="Unsupported hardware kind", pool=None)


def _normalize_hw_list(hardware_report: Dict[str, Any] | List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(hardware_report, dict) and "hardware_analysis" in hardware_report:
        return hardware_report["hardware_analysis"]
    if isinstance(hardware_report, list):
        return hardware_report
    raise MatcherError("hardware_report must be hardware_analyzer output or a list of hardware entries.")


def match_model_to_hardware(
    model: Dict[str, Any],
    hardware_report: Dict[str, Any] | List[Dict[str, Any]],
    *,
    allow_multi_gpu_shard: bool = False,
    allow_cross_node: bool = False,
) -> Dict[str, Any]:
    """Evaluate hardware candidates for a given model report."""
    requirements = _model_requirements(model)
    hw_list = _normalize_hw_list(hardware_report)

    candidates: List[Dict[str, Any]] = []
    for hw in hw_list:
        dtype_key, dtype_note = _select_dtype(hw.get("dtype_support", {}), requirements.dtype_key_preference)
        if dtype_key is None:
            candidates.append(
                {
                    "hardware_id": hw.get("hardware_id"),
                    "kind": hw.get("kind"),
                    "feasible": False,
                    "reason": dtype_note,
                }
            )
            continue

        mem = _assess_memory(hw, requirements.total_bytes, allow_multi_gpu_shard, allow_cross_node)
        rate = _sustained_rate(hw, dtype_key)

        feasible = rate is not None and mem.status not in {"insufficient", "requires_distributed"}
        latency_s = requirements.flops_per_inference / rate if feasible and rate else None
        qps = (1.0 / latency_s) if latency_s and latency_s > 0 else None

        candidates.append(
            {
                "hardware_id": hw.get("hardware_id"),
                "kind": hw.get("kind"),
                "dtype_selected": dtype_key,
                "dtype_note": dtype_note,
                "memory": {
                    "status": mem.status,
                    "detail": mem.detail,
                    "pool": mem.pool,
                    "required_bytes": requirements.total_bytes,
                    "ram_bytes": hw.get("memory_capacity_bytes", {}).get("ram"),
                    "vram_bytes": hw.get("memory_capacity_bytes", {}).get("vram"),
                },
                "sustained_rate_per_s": rate,
                "estimated_latency_s": latency_s,
                "estimated_qps": qps,
                "feasible": feasible,
            }
        )

    candidates.sort(
        key=lambda c: (
            not c["feasible"],
            float("inf") if c.get("estimated_latency_s") in (None, 0) else c["estimated_latency_s"],
        )
    )

    return {
        "model_dtype_bits": requirements.dtype_bits,
        "total_model_bytes": requirements.total_bytes,
        "candidates": candidates,
        "assumptions": {
            "allow_multi_gpu_shard": allow_multi_gpu_shard,
            "allow_cross_node": allow_cross_node,
            "dtype_preferences": requirements.dtype_key_preference,
        },
    }
