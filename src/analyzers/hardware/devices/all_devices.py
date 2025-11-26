"""Per-kind hardware analyzers.

All FLOP/OP rates are in raw operations per second (not Tera units).
All *_bytes fields are raw bytes; all *_bytes_per_s fields are raw bytes/second.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from utils.validators import (
    require_int,
    require_positive_number,
)
from utils.converters import (
    apply_utilization as apply_util,
    gb_to_bytes,
    tflops_to_flops,
    tops_to_ops,
)
ValidationError = ValueError

DTYPE_MAP = {"fp32": 32, "fp16": 16, "bf16": 16, "int8": 8}


def _gpu_peak_from_sms(spec: Dict[str, Any]) -> float:
    num_sms = spec.get("num_sms")
    cores_per_sm = spec.get("cores_per_sm")
    base_clock_ghz = spec.get("base_clock_ghz")
    if num_sms is None or cores_per_sm is None or base_clock_ghz is None:
        raise ValidationError("GPU peak_fp32_tflops is missing and SM/core/clock info insufficient.")
    if not all(isinstance(x, (int, float)) and x > 0 for x in [num_sms, cores_per_sm, base_clock_ghz]):
        raise ValidationError("GPU SM/core/clock info must be positive numbers.")
    total_cores = num_sms * cores_per_sm
    flops_per_cycle_per_core = 2.0  # one FMA (mul+add)
    peak_fp32_flops_per_s = total_cores * base_clock_ghz * 1e9 * flops_per_cycle_per_core
    return peak_fp32_flops_per_s / 1e12


def analyze_cpu_node(spec: Dict[str, Any], utils: Dict[str, float]) -> Dict[str, Any]:
    num_sockets = require_int(spec, "num_sockets", positive=True)
    cores_per_socket = require_int(spec, "cores_per_socket", positive=True)
    threads_per_core = require_int(spec, "threads_per_core", positive=True)

    base_clock_ghz = require_positive_number(spec, "base_clock_ghz")
    vector_width_bits = require_positive_number(spec, "vector_width_bits")
    fma_units_per_core = require_positive_number(spec, "fma_units_per_core")

    peak_fp32_tflops = spec.get("peak_fp32_tflops")
    if peak_fp32_tflops is None:
        total_cores = num_sockets * cores_per_socket
        lanes = vector_width_bits / 32.0
        flops_per_cycle_per_core = lanes * fma_units_per_core * 2.0  # 2 FLOPs per FMA
        peak_fp32_flops_per_s = total_cores * base_clock_ghz * 1e9 * flops_per_cycle_per_core
        peak_fp32_tflops = peak_fp32_flops_per_s / 1e12
    peak_fp32_flops = tflops_to_flops(peak_fp32_tflops)

    ram_capacity_gb = require_positive_number(spec, "ram_capacity_gb")
    ram_capacity_bytes = gb_to_bytes(ram_capacity_gb)

    ram_bandwidth_gbps = spec.get("ram_bandwidth_gbps")
    if ram_bandwidth_gbps is None:
        mem_channels = spec.get("memory_channels")
        mem_speed = spec.get("memory_speed_mtps")
        bus_width = spec.get("memory_bus_width_bits", 64)
        if mem_channels and mem_speed:
            bytes_per_transfer = bus_width / 8.0
            bandwidth_bytes_per_s = mem_channels * mem_speed * 1e6 * bytes_per_transfer
            ram_bandwidth_gbps = bandwidth_bytes_per_s / 1e9
    ram_bandwidth_bytes = None if ram_bandwidth_gbps is None else ram_bandwidth_gbps * 1e9

    l3_cache_bytes = None
    if "l3_cache_mb" in spec and isinstance(spec["l3_cache_mb"], (int, float)) and spec["l3_cache_mb"] > 0:
        l3_cache_bytes = int(spec["l3_cache_mb"] * 1e6)
    elif "l3_cache_bytes" in spec and isinstance(spec["l3_cache_bytes"], (int, float)) and spec["l3_cache_bytes"] > 0:
        l3_cache_bytes = int(spec["l3_cache_bytes"])

    dram_latency_ns = spec.get("dram_latency_ns")
    if not isinstance(dram_latency_ns, (int, float)) or dram_latency_ns <= 0:
        dram_latency_ns = 100.0
    cache_latency_ns = spec.get("cache_latency_ns")
    if not isinstance(cache_latency_ns, (int, float)) or cache_latency_ns <= 0:
        cache_latency_ns = 5.0

    supports_fp16 = bool(spec.get("supports_fp16", False))
    supports_bf16 = bool(spec.get("supports_bf16", False))
    supports_int8 = bool(spec.get("supports_int8", False))

    peak_flops = {"fp32": peak_fp32_flops, "fp16": None, "bf16": None}
    peak_ops = {"int8": None}
    sustained_flops = {"fp32": apply_util(peak_flops["fp32"], utils["fp32"]), "fp16": None, "bf16": None}
    sustained_ops = {"int8": apply_util(peak_ops["int8"], utils["int8"])}

    total_threads = num_sockets * cores_per_socket * threads_per_core

    return {
        "dtype_support": {"fp32": True, "fp16": supports_fp16, "bf16": supports_bf16, "int8": supports_int8},
        "dtype_map": DTYPE_MAP,
        "utilization_assumptions": utils,
        "peak_flops_per_s": peak_flops,
        "peak_ops_per_s": peak_ops,
        "sustained_flops_per_s": sustained_flops,
        "sustained_ops_per_s": sustained_ops,
        "memory_capacity_bytes": {"ram": ram_capacity_bytes, "vram": None},
        "memory_bandwidth_bytes_per_s": {"ram": ram_bandwidth_bytes, "vram": None},
        "memory_model": "cpu_only",
        "host_device_bandwidth_bytes_per_s": None,
        "cpu_threads": total_threads,
        "num_gpus": None,
        "dram_latency_ns": dram_latency_ns,
        "cache_latency_ns": cache_latency_ns,
        "memory_latency_seconds": dram_latency_ns * 1e-9,
        "cache_latency_seconds": cache_latency_ns * 1e-9,
        "l3_cache_bytes": l3_cache_bytes,
    }


def analyze_gpu(spec: Dict[str, Any], utils: Dict[str, float]) -> Dict[str, Any]:
    peak_fp32_tflops = spec.get("peak_fp32_tflops")
    if peak_fp32_tflops is None:
        peak_fp32_tflops = _gpu_peak_from_sms(spec)
    peak_fp16_tflops = spec.get("peak_fp16_tflops")
    peak_bf16_tflops = spec.get("peak_bf16_tflops")
    peak_int8_tops = spec.get("peak_int8_tops")

    peak_flops = {
        "fp32": tflops_to_flops(peak_fp32_tflops),
        "fp16": tflops_to_flops(peak_fp16_tflops),
        "bf16": tflops_to_flops(peak_bf16_tflops),
    }
    peak_ops = {"int8": tops_to_ops(peak_int8_tops)}
    sustained_flops = {k: apply_util(v, utils[k]) for k, v in peak_flops.items()}
    sustained_ops = {"int8": apply_util(peak_ops["int8"], utils["int8"])}

    vram_capacity_gb = require_positive_number(spec, "vram_capacity_gb")
    vram_capacity_bytes = gb_to_bytes(vram_capacity_gb)
    vram_bandwidth_gbps = spec.get("vram_bandwidth_gbps")
    if vram_bandwidth_gbps is None:
        raise ValidationError("GPU vram_bandwidth_gbps is required.")
    vram_bandwidth_bytes = vram_bandwidth_gbps * 1e9

    dram_latency_ns = spec.get("dram_latency_ns")
    if not isinstance(dram_latency_ns, (int, float)) or dram_latency_ns <= 0:
        dram_latency_ns = 300.0
    cache_latency_ns = spec.get("cache_latency_ns")
    if not isinstance(cache_latency_ns, (int, float)) or cache_latency_ns <= 0:
        cache_latency_ns = 20.0

    supports_fp16 = bool(spec.get("supports_fp16", False))
    supports_bf16 = bool(spec.get("supports_bf16", False))
    supports_int8 = bool(spec.get("supports_int8", False))

    pcie_bw = spec.get("pcie_bandwidth_gbps")
    nvlink_bw = spec.get("nvlink_bandwidth_gbps")
    host_bw = None
    if nvlink_bw is not None:
        host_bw = nvlink_bw * 1e9
    elif pcie_bw is not None:
        host_bw = pcie_bw * 1e9

    return {
        "dtype_support": {"fp32": True, "fp16": supports_fp16, "bf16": supports_bf16, "int8": supports_int8},
        "dtype_map": DTYPE_MAP,
        "utilization_assumptions": utils,
        "peak_flops_per_s": peak_flops,
        "peak_ops_per_s": peak_ops,
        "sustained_flops_per_s": sustained_flops,
        "sustained_ops_per_s": sustained_ops,
        "memory_capacity_bytes": {"ram": None, "vram": vram_capacity_bytes},
        "memory_bandwidth_bytes_per_s": {"ram": None, "vram": vram_bandwidth_bytes},
        "memory_model": "separate",
        "host_device_bandwidth_bytes_per_s": host_bw,
        "cpu_threads": None,
        "num_gpus": 1,
        "dram_latency_ns": dram_latency_ns,
        "cache_latency_ns": cache_latency_ns,
        "memory_latency_seconds": dram_latency_ns * 1e-9,
        "cache_latency_seconds": cache_latency_ns * 1e-9,
        "l3_cache_bytes": None,
    }


def analyze_accelerator(spec: Dict[str, Any], utils: Dict[str, float]) -> Dict[str, Any]:
    peak_fp32_flops = tflops_to_flops(spec.get("peak_fp32_tflops"))
    peak_fp16_flops = tflops_to_flops(spec.get("peak_fp16_tflops"))
    peak_bf16_flops = tflops_to_flops(spec.get("peak_bf16_tflops"))
    peak_int8_ops = tops_to_ops(spec.get("peak_int8_tops"))
    if all(x is None for x in [peak_fp32_flops, peak_fp16_flops, peak_bf16_flops, peak_int8_ops]):
        raise ValidationError("Accelerator must provide at least one peak throughput value.")

    mem_capacity_gb = require_positive_number(spec, "memory_capacity_gb")
    mem_capacity_bytes = gb_to_bytes(mem_capacity_gb)
    mem_bandwidth_gbps = require_positive_number(spec, "memory_bandwidth_gbps")
    mem_bandwidth_bytes = mem_bandwidth_gbps * 1e9
    host_bw = None
    if "host_bandwidth_gbps" in spec and spec["host_bandwidth_gbps"] is not None:
        bw = spec["host_bandwidth_gbps"]
        if not isinstance(bw, (int, float)) or bw <= 0:
            raise ValidationError("host_bandwidth_gbps must be a positive number when provided.")
        host_bw = bw * 1e9

    dram_latency_ns = spec.get("dram_latency_ns")
    if not isinstance(dram_latency_ns, (int, float)) or dram_latency_ns <= 0:
        dram_latency_ns = 300.0
    cache_latency_ns = spec.get("cache_latency_ns")
    if not isinstance(cache_latency_ns, (int, float)) or cache_latency_ns <= 0:
        cache_latency_ns = 20.0

    dtype_support = {
        "fp32": peak_fp32_flops is not None,
        "fp16": bool(spec.get("supports_fp16", False)),
        "bf16": bool(spec.get("supports_bf16", False)),
        "int8": bool(spec.get("supports_int8", False)),
    }

    peak_flops = {"fp32": peak_fp32_flops, "fp16": peak_fp16_flops, "bf16": peak_bf16_flops}
    peak_ops = {"int8": peak_int8_ops}
    sustained_flops = {k: apply_util(v, utils[k]) for k, v in peak_flops.items()}
    sustained_ops = {"int8": apply_util(peak_ops["int8"], utils["int8"])}

    return {
        "dtype_support": dtype_support,
        "dtype_map": DTYPE_MAP,
        "utilization_assumptions": utils,
        "peak_flops_per_s": peak_flops,
        "peak_ops_per_s": peak_ops,
        "sustained_flops_per_s": sustained_flops,
        "sustained_ops_per_s": sustained_ops,
        "memory_capacity_bytes": {"ram": None, "vram": mem_capacity_bytes},
        "memory_bandwidth_bytes_per_s": {"ram": None, "vram": mem_bandwidth_bytes},
        "memory_model": "separate",
        "host_device_bandwidth_bytes_per_s": host_bw,
        "cpu_threads": None,
        "num_gpus": 1,
        "dram_latency_ns": dram_latency_ns,
        "cache_latency_ns": cache_latency_ns,
        "memory_latency_seconds": dram_latency_ns * 1e-9,
        "cache_latency_seconds": cache_latency_ns * 1e-9,
        "l3_cache_bytes": None,
    }


def merge_dtype_support(a: Dict[str, bool], b: Dict[str, bool]) -> Dict[str, bool]:
    return {k: bool(a.get(k, False) or b.get(k, False)) for k in ["fp32", "fp16", "bf16", "int8"]}


def sum_flops_dict(a: Dict[str, Optional[float]], b: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for k in ["fp32", "fp16", "bf16"]:
        av = a.get(k)
        bv = b.get(k)
        if av is None and bv is None:
            out[k] = None
        else:
            out[k] = (av or 0.0) + (bv or 0.0)
    return out


def sum_ops_dict(a: Dict[str, Optional[float]], b: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for k in ["int8"]:
        av = a.get(k)
        bv = b.get(k)
        if av is None and bv is None:
            out[k] = None
        else:
            out[k] = (av or 0.0) + (bv or 0.0)
    return out


def analyze_jetson(spec: Dict[str, Any], utils: Dict[str, float]) -> Dict[str, Any]:
    if "cpu" not in spec or "gpu" not in spec:
        raise ValidationError("Jetson/soc spec must include 'cpu' and 'gpu' blocks.")
    cpu_norm = analyze_cpu_node(spec["cpu"], utils)
    gpu_norm = analyze_gpu(spec["gpu"], utils)

    ram_capacity_gb = require_positive_number(spec, "ram_capacity_gb")
    ram_bytes = gb_to_bytes(ram_capacity_gb)

    # For SoC, prefer CPU cache latency if present, else GPU.
    dram_latency_ns = cpu_norm.get("dram_latency_ns") or gpu_norm.get("dram_latency_ns") or 300.0
    cache_latency_ns = cpu_norm.get("cache_latency_ns") or gpu_norm.get("cache_latency_ns") or 10.0
    l3_cache_bytes = cpu_norm.get("l3_cache_bytes") or None

    dtype_support = merge_dtype_support(cpu_norm["dtype_support"], gpu_norm["dtype_support"])
    peak_flops = sum_flops_dict(cpu_norm["peak_flops_per_s"], gpu_norm["peak_flops_per_s"])
    peak_ops = sum_ops_dict(cpu_norm["peak_ops_per_s"], gpu_norm["peak_ops_per_s"])
    sustained_flops = {k: apply_util(peak_flops[k], utils[k]) for k in ["fp32", "fp16", "bf16"]}
    sustained_ops = {"int8": apply_util(peak_ops["int8"], utils["int8"])}

    # Shared memory pool; represent as both ram and vram.
    return {
        "dtype_support": dtype_support,
        "dtype_map": DTYPE_MAP,
        "utilization_assumptions": utils,
        "peak_flops_per_s": peak_flops,
        "peak_ops_per_s": peak_ops,
        "sustained_flops_per_s": sustained_flops,
        "sustained_ops_per_s": sustained_ops,
        "memory_capacity_bytes": {"ram": ram_bytes, "vram": ram_bytes},
        "memory_bandwidth_bytes_per_s": {
            "ram": cpu_norm["memory_bandwidth_bytes_per_s"]["ram"],
            "vram": gpu_norm["memory_bandwidth_bytes_per_s"]["vram"],
        },
        "memory_model": "shared",
        "host_device_bandwidth_bytes_per_s": gpu_norm["host_device_bandwidth_bytes_per_s"],
        "cpu_threads": cpu_norm["cpu_threads"],
        "num_gpus": 1,
        "dram_latency_ns": dram_latency_ns,
        "cache_latency_ns": cache_latency_ns,
        "memory_latency_seconds": dram_latency_ns * 1e-9,
        "cache_latency_seconds": cache_latency_ns * 1e-9,
        "l3_cache_bytes": l3_cache_bytes,
    }

