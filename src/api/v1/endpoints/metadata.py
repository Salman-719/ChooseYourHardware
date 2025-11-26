"""Metadata extraction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from metadata_extractor.schemas import (
    MetadataExtractionRequest,
    MetadataExtractionResponse,
)
from metadata_extractor.service import extract_model_metadata
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.post("/extract", response_model=MetadataExtractionResponse)
async def extract_metadata(
    request: MetadataExtractionRequest,
) -> MetadataExtractionResponse:
    """Extract model metadata from user input using LLM.

    This endpoint uses an interactive conversation flow to extract
    structured metadata about a deep learning model. It asks follow-up
    questions to gather all necessary information.

    Args:
        request: Metadata extraction request containing:
            - model_type: Type of model (e.g., "cnn", "rnn")
            - user_input: User's response to the last question
            - current_state: Current extracted metadata state
            - last_question: The last question that was asked

    Returns:
        MetadataExtractionResponse containing:
            - metadata: Updated metadata dictionary
            - next_question: Next question to ask the user
            - is_complete: Whether extraction is complete

    Raises:
        HTTPException: If extraction fails
    """
    try:
        logger.info(f"Extracting metadata for model type: {request.model_type}")
        response = await extract_model_metadata(request)
        
        if response.is_complete:
            logger.info("Metadata extraction completed successfully")
        else:
            logger.info(f"Next question: {response.next_question}")
        
        return response

    except Exception as exc:
        logger.exception(f"Failed to extract metadata: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Metadata extraction failed: {str(exc)}"
        ) from exc
