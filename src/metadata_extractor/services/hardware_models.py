from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, model_validator


def _require_positive_numbers(spec: Dict[str, Any], keys: list[str], context: str) -> None:
    for key in keys:
        value = spec.get(key)
        if value is None:
            raise ValueError(f"{context}: missing required field '{key}'")
        try:
            if float(value) <= 0:
                raise ValueError
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{context}: '{key}' must be a positive number") from exc


def _require_positive_ints(spec: Dict[str, Any], keys: list[str], context: str) -> None:
    for key in keys:
        value = spec.get(key)
        if value is None:
            raise ValueError(f"{context}: missing required field '{key}'")
        try:
            if int(value) <= 0:
                raise ValueError
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{context}: '{key}' must be a positive integer") from exc


def _require_latencies(spec: Dict[str, Any], context: str) -> None:
    if not (spec.get("dram_latency_s") or spec.get("dram_latency_ns")):
        raise ValueError(f"{context}: one of dram_latency_s or dram_latency_ns is required")
    if not (spec.get("cache_latency_s") or spec.get("cache_latency_ns")):
        raise ValueError(f"{context}: one of cache_latency_s or cache_latency_ns is required")


def _validate_dtype_flags(spec: Dict[str, Any], context: str) -> None:
    flag_to_peak = {
        "supports_fp16": "peak_fp16_tflops",
        "supports_bf16": "peak_bf16_tflops",
        "supports_int8": "peak_int8_tops",
    }
    for flag, peak in flag_to_peak.items():
        if spec.get(flag):
            if spec.get(peak) is None:
                raise ValueError(f"{context}: '{flag}' requires '{peak}' to be provided")


def _validate_cpu_spec(spec: Dict[str, Any], context: str) -> None:
    _require_positive_ints(spec, ["num_sockets", "cores_per_socket", "threads_per_core"], context)
    _require_positive_numbers(spec, ["base_clock_ghz", "vector_width_bits", "fma_units_per_core"], context)

    # Memory requirements
    _require_positive_numbers(spec, ["ram_capacity_gb"], context)
    has_bandwidth = spec.get("ram_bandwidth_gbps") is not None
    has_channels_speed = spec.get("memory_channels") and spec.get("memory_speed_mtps")
    if not (has_bandwidth or has_channels_speed):
        raise ValueError(
            f"{context}: require ram_bandwidth_gbps OR memory_channels + memory_speed_mtps (optional memory_bus_width_bits)"
        )

    _require_latencies(spec, context)
    _validate_dtype_flags(spec, context)


def _validate_gpu_spec(spec: Dict[str, Any], context: str) -> None:
    # VRAM capacity is required, bandwidth is validated if present.
    _require_positive_numbers(spec, ["vram_capacity_gb"], context)
    if spec.get("vram_bandwidth_gbps") is not None:
        _require_positive_numbers(spec, ["vram_bandwidth_gbps"], context)

    has_peak_fp32 = spec.get("peak_fp32_tflops") is not None
    can_infer = spec.get("num_sms") and spec.get("cores_per_sm") and spec.get("base_clock_ghz")
    if not (has_peak_fp32 or can_infer):
        raise ValueError(
            f"{context}: require peak_fp32_tflops or (num_sms + cores_per_sm + base_clock_ghz) to infer it"
        )
    # Latencies are helpful but optional for ingestion; validate only if provided.
    if spec.get("dram_latency_s") is not None or spec.get("dram_latency_ns") is not None:
        _require_positive_numbers(spec, ["dram_latency_s"], context) if spec.get("dram_latency_s") is not None else None
    if spec.get("cache_latency_s") is not None or spec.get("cache_latency_ns") is not None:
        _require_positive_numbers(spec, ["cache_latency_s"], context) if spec.get("cache_latency_s") is not None else None
    _validate_dtype_flags(spec, context)


def _validate_accelerator_spec(spec: Dict[str, Any], context: str) -> None:
    has_any_peak = any(
        spec.get(key) is not None
        for key in ("peak_fp32_tflops", "peak_fp16_tflops", "peak_bf16_tflops", "peak_int8_tops")
    )
    if not has_any_peak:
        raise ValueError(f"{context}: at least one of peak_fp32/peak_fp16/peak_bf16/peak_int8 must be provided")
    _require_positive_numbers(spec, ["memory_capacity_gb", "memory_bandwidth_gbps"], context)
    _require_latencies(spec, context)
    _validate_dtype_flags(spec, context)


def _validate_soc_spec(spec: Dict[str, Any], context: str) -> None:
    cpu = spec.get("cpu")
    gpu = spec.get("gpu")
    if not isinstance(cpu, dict) or not isinstance(gpu, dict):
        raise ValueError(f"{context}: jetson/soc requires nested 'cpu' and 'gpu' specs")
    _require_positive_numbers(spec, ["ram_capacity_gb"], context)
    _validate_cpu_spec(cpu, f"{context}.cpu")
    _validate_gpu_spec(gpu, f"{context}.gpu")


class HardwareRecord(BaseModel):
    hardware_id: str
    kind: Literal["cpu_node", "gpu", "tpu", "accelerator", "jetson", "soc"]
    vendor: str
    model_name: str
    spec: Dict[str, Any]
    url: Optional[str] = None
    price: Optional[str] = None
    source: Optional[str] = None

    @model_validator(mode="after")
    def validate_spec(self) -> "HardwareRecord":
        if not self.hardware_id:
            raise ValueError("hardware_id must be non-empty")
        if not self.vendor:
            raise ValueError("vendor must be non-empty")
        if not self.model_name:
            raise ValueError("model_name must be non-empty")
        spec = self.spec or {}
        context = f"{self.hardware_id}"
        if self.kind == "cpu_node":
            _validate_cpu_spec(spec, context)
        elif self.kind == "gpu":
            _validate_gpu_spec(spec, context)
        elif self.kind in {"accelerator", "tpu"}:
            _validate_accelerator_spec(spec, context)
        elif self.kind in {"jetson", "soc"}:
            _validate_soc_spec(spec, context)
        else:
            raise ValueError(f"{context}: unsupported kind '{self.kind}'")
        return self
