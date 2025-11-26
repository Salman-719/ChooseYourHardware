"""Pydantic schemas for metadata extraction."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetadataExtractionRequest(BaseModel):
    """Request model for metadata extraction."""

    model_type: str = Field(default="cnn", description="Type of ML model (e.g., cnn, transformer)")
    session_id: Optional[str] = Field(
        default=None, description="Optional session identifier to let the backend persist state between turns"
    )
    reset: bool = Field(default=False, description="When true with session_id, clears stored state before processing")
    last_question: Optional[str] = Field(None, description="Last question asked to user")
    user_input: Optional[str] = Field(None, description="User's response to the question")
    current_state: Optional[Dict[str, Any]] = Field(None, description="Current extraction state")


class MetadataExtractionResponse(BaseModel):
    """Response model for metadata extraction."""

    metadata: Dict[str, Any] = Field(..., description="Extracted model metadata")
    next_question: Optional[str] = Field(None, description="Next question to ask user")
    is_complete: bool = Field(default=False, description="Whether extraction is complete")
