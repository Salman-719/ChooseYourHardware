"""Hardware analysis API endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ....analyzers.hardware import analyze_hardware_spec
from ....exceptions import HardwareValidationError
from ....utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HardwareAnalysisRequest(BaseModel):
    """Request model for hardware analysis."""

    hardware_spec: Dict[str, Any] = Field(..., description="Hardware specification dictionary")

    model_config = {
        "json_schema_extra": {
            "example": {
                "hardware_spec": {
                    "hardware": [
                        {
                            "hardware_id": "gpu1",
                            "kind": "gpu",
                            "vendor": "NVIDIA",
                            "model_name": "RTX 4090",
                            "spec": {
                                "compute_tflops_fp32": 82.58,
                                "memory_gb": 24,
                                "memory_bandwidth_gbps": 1008
                            }
                        }
                    ],
                    "defaults": {
                        "utilization_fp32": 0.8
                    }
                }
            }
        }
    }


class HardwareAnalysisResponse(BaseModel):
    """Response model for hardware analysis."""

    result: Dict[str, Any] = Field(..., description="Hardware analysis results")
    success: bool = Field(default=True, description="Whether analysis was successful")


@router.post(
    "/hardware/analyze",
    response_model=HardwareAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze hardware specification",
    description="Normalize hardware capabilities and compute throughput metrics",
)
async def analyze_hw_spec(request: HardwareAnalysisRequest) -> HardwareAnalysisResponse:
    """Analyze a hardware specification.

    Args:
        request: Hardware analysis request

    Returns:
        Analysis results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        result = analyze_hardware_spec(request.hardware_spec)
        return HardwareAnalysisResponse(result=result, success=True)
    except HardwareValidationError as exc:
        logger.error(f"Hardware validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hardware validation error: {str(exc)}",
        ) from exc
    except Exception as exc:
        logger.exception(f"Unexpected error analyzing hardware: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during hardware analysis",
        ) from exc
