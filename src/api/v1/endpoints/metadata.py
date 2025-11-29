"""Metadata extraction endpoints."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analyzers.model.core import analyze_model
from metadata_extractor.schemas import (
    MetadataExtractionRequest,
    MetadataExtractionResponse,
)
from metadata_extractor.service import extract_model_metadata
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/metadata", tags=["metadata"])

# Simple in-memory session store (per-process). Not durable across restarts/workers.
_sessions: dict[str, dict[str, object]] = {}


class MetadataAnalysisResponse(BaseModel):
    """Combined response for metadata extraction and optional analysis."""

    metadata: Dict[str, Any]
    next_question: Optional[str] = None
    is_complete: bool
    analysis: Optional[Dict[str, Any]] = None


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

        session_state = None
        if request.session_id:
            if request.reset:
                _sessions.pop(request.session_id, None)
            session_state = _sessions.get(request.session_id, {})

        effective_current = request.current_state
        effective_last_question = request.last_question
        if session_state:
            if effective_current is None:
                effective_current = session_state.get("current_state")
            if effective_last_question is None:
                effective_last_question = session_state.get("last_question")

        req_for_service = MetadataExtractionRequest(
            model_type=request.model_type,
            last_question=effective_last_question,
            user_input=request.user_input,
            current_state=effective_current,
        )

        response = await extract_model_metadata(req_for_service)

        print("\n\nReasspose:\n", response, "\n\n")
        if request.session_id:
            _sessions[request.session_id] = {
                "current_state": response.metadata,
                "last_question": response.next_question,
            }
        
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


@router.post("/extract-and-analyze", response_model=MetadataAnalysisResponse)
async def extract_and_analyze(
    request: MetadataExtractionRequest,
) -> MetadataAnalysisResponse:
    """Extract metadata and, when complete, run the model analyzer in one call."""
    try:
        extraction = await extract_metadata(request)

        analysis: Optional[Dict[str, Any]] = None
        if extraction.is_complete:
            try:
                analysis = json.loads(analyze_model(json.dumps(extraction.metadata)))
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Analysis failed after metadata extraction: {exc}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Analysis failed after metadata extraction: {str(exc)}",
                ) from exc

        return MetadataAnalysisResponse(
            metadata=extraction.metadata,
            next_question=extraction.next_question,
            is_complete=extraction.is_complete,
            analysis=analysis,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Failed to extract and analyze metadata: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Metadata extract-and-analyze failed: {str(exc)}"
        ) from exc
