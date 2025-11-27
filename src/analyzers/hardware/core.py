"""Core orchestration for hardware analysis."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .devices import all_devices as analyzers
from .utils import resolve_utils

ValidationError = ValueError


ALLOWED_KINDS = {"cpu_node", "gpu", "tpu", "accelerator", "jetson", "soc"}


def _analyze_single_hardware(hardware: Dict[str, Any], utils: Dict[str, float]) -> Dict[str, Any]:
    hardware_id = hardware.get("hardware_id")
    if not hardware_id or not isinstance(hardware_id, str):
        raise ValidationError("hardware_id must be a non-empty string.")
    kind = hardware.get("kind")
    if kind not in ALLOWED_KINDS:
        raise ValidationError(f"Unsupported kind '{kind}'.")
    vendor = hardware.get("vendor")
    model_name = hardware.get("model_name")
    if not isinstance(vendor, str) or not isinstance(model_name, str):
        raise ValidationError("vendor and model_name must be strings.")
    spec = hardware.get("spec")
    if not isinstance(spec, dict):
        raise ValidationError("spec must be an object.")

    if kind == "cpu_node":
        normalized = analyzers.analyze_cpu_node(spec, utils)
    elif kind == "gpu":
        normalized = analyzers.analyze_gpu(spec, utils)
    elif kind in {"tpu", "accelerator"}:
        normalized = analyzers.analyze_accelerator(spec, utils)
    elif kind in {"jetson", "soc"}:
        normalized = analyzers.analyze_jetson(spec, utils)
    else:
        raise ValidationError(f"Unhandled kind '{kind}'.")

    return {
        "hardware_id": hardware_id,
        "kind": kind,
        "vendor": vendor,
        "model_name": model_name,
        "normalized": normalized,
    }


def analyze_hardware_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValidationError("Top-level spec must be an object.")
    if "hardware_list" not in spec or not isinstance(spec["hardware_list"], list) or not spec["hardware_list"]:
        raise ValidationError("hardware_list must be a non-empty list.")

    utils = resolve_utils(spec.get("defaults"))

    analyses: List[Dict[str, Any]] = []
    for hw in spec["hardware_list"]:
        if not isinstance(hw, dict):
            raise ValidationError("Each hardware entry must be an object.")
        analyses.append(_analyze_single_hardware(hw, utils))

    return {"hardware_analysis": analyses}


def analyze_hardware_spec_json(json_str: str) -> Dict[str, Any]:
    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc
    return analyze_hardware_spec(obj)
