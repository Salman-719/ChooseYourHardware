"""Model analysis API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from analyzers.model.core import analyze_model
from exceptions.model_exceptions import ModelValidationError
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ModelAnalysisRequest(BaseModel):
    """Request model for model analysis."""

    model_json: str = Field(..., description="JSON string containing model configuration")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_json": '{"model_type": "neural_network", "dtype_bits": 32, "inference_config": {"batch_size": 8}}'
            }
        }
    }


class ModelAnalysisResponse(BaseModel):
    """Response model for model analysis."""

    result: str = Field(..., description="JSON string containing analysis results")
    success: bool = Field(default=True, description="Whether analysis was successful")


@router.post(
    "/models/analyze",
    response_model=ModelAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze ML model",
    description="Analyze an ML model configuration and compute resource requirements",
)
async def analyze_ml_model(request: ModelAnalysisRequest) -> ModelAnalysisResponse:
    """Analyze an ML model configuration.

    Args:
        request: Model analysis request

    Returns:
        Analysis results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        result = analyze_model(request.model_json)
        return ModelAnalysisResponse(result=result, success=True)
    except ModelValidationError as exc:
        logger.error(f"Model validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model validation error: {str(exc)}",
        ) from exc
    except Exception as exc:
        logger.exception(f"Unexpected error analyzing model: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during model analysis",
        ) from exc
