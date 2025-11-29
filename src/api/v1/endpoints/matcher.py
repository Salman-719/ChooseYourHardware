"""Endpoints for running the matcher to pick the best device for a given model."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analyzers.hardware.core import analyze_hardware_spec
from analyzers.model.core import analyze_model
from config.settings import get_settings
from matchers.core import calculate_inference_metrics
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/matcher", tags=["matcher"])


class MatchRequest(BaseModel):
    """Request body for matcher endpoint."""

    model: Dict[str, Any]
    device_dir: Optional[str] = None
    decode_tokens: Optional[int] = None


class MatchResult(BaseModel):
    """Result for a single device evaluation."""

    device_file: str
    device: Dict[str, Any]
    latency_seconds: float
    bottleneck: str


class BestMatchResponse(BaseModel):
    """Response payload containing the best device and per-device breakdown."""

    best_device: Optional[Dict[str, Any]]
    best_latency_seconds: Optional[float]
    bottleneck: Optional[str]
    evaluated: List[MatchResult]


@router.post("/best", response_model=BestMatchResponse)
def choose_best_device(request: MatchRequest) -> BestMatchResponse:
    """Run matcher over all device JSONs in a directory and pick the best device."""
    settings = get_settings()
    device_dir = Path("/home/htermos/Desktop/proj490/ChooseYourHardware/device_data")
    if not device_dir.exists() or not device_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Device directory not found: {device_dir}")

    device_files = sorted(device_dir.glob("*.json"))
    if not device_files:
        raise HTTPException(status_code=400, detail=f"No device JSON files found in {device_dir}")

    try:
        # Analyze model once
        model_analysis = json.loads(analyze_model(json.dumps(request.model)))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to analyze model")
        raise HTTPException(status_code=400, detail=f"Model analysis failed: {exc}") from exc

    evaluated: List[MatchResult] = []
    best_latency = float("inf")
    best_device: Optional[Dict[str, Any]] = None
    best_bottleneck: Optional[str] = None

    for f in device_files:
        try:
            with open(f, "r") as fh:
                device_obj = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping device file %s: %s", f, exc)
            continue

        # Normalize hardware spec
        try:
            hw_analysis = analyze_hardware_spec({"hardware_list": [device_obj]})
            normalized = hw_analysis["hardware_analysis"][0]["normalized"]
            normalized["cost_usd"] = float(hw_analysis["hardware_analysis"][0].get("cost_usd").split()[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping device %s due to hardware analysis failure: %s", f, exc)
            continue

        latency, bottleneck = calculate_inference_metrics(
            model=model_analysis, hardware=normalized, decode_tokens=request.decode_tokens
        )

        if not math.isfinite(latency):
            logger.warning("Skipping device %s due to non-finite latency (%s)", f, latency)
            continue

        evaluated.append(
            MatchResult(
                device_file=str(f),
                device=device_obj,
                latency_seconds=latency,
                bottleneck=bottleneck,
            )
        )

        if latency < best_latency:
            best_latency = latency
            best_device = device_obj
            best_bottleneck = bottleneck

    if best_device is None:
        return {"results": "No suitable devices found."}

    return BestMatchResponse(
        best_device=best_device,
        best_latency_seconds=best_latency,
        bottleneck=best_bottleneck,
        evaluated=evaluated,
    )
