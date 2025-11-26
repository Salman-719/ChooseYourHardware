"""Metadata extraction service using OpenAI LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from openai import AsyncOpenAI

from config.settings import get_settings
from utils.logging import get_logger

from .schemas import MetadataExtractionRequest, MetadataExtractionResponse

logger = get_logger(__name__)


class MetadataExtractor:
    """Service for extracting model metadata using LLM."""

    def __init__(self):
        """Initialize the metadata extractor."""
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
        # Load prompts and templates
        prompts_dir = Path(__file__).parent / "prompts"
        
        with open(prompts_dir / "metadata_extractor_asker.txt") as f:
            self.asker_prompt = f.read()
        
        with open(prompts_dir / "metadata_extractor_updater.txt") as f:
            self.updater_prompt = f.read()
        
        with open(prompts_dir / "model_fields.json") as f:
            self.model_fields_templates = json.load(f)
        
        with open(prompts_dir / "layer_types.json") as f:
            self.layer_types = {"cnn": json.load(f)}

    async def extract_metadata(
        self, request: MetadataExtractionRequest
    ) -> MetadataExtractionResponse:
        """Extract model metadata from user input.

        Args:
            request: Extraction request with user input and current state

        Returns:
            Extraction response with updated metadata and next question
        """
        try:
            # Get model fields template for the model type
            model_fields = self.model_fields_templates.get(
                request.model_type, self.model_fields_templates["cnn"]
            )
            model_fields["filled"] = False
            model_fields["follow_up_question"] = "null"

            # Get allowed layers for the model type
            allowed_layers = self.layer_types.get(
                request.model_type, self.layer_types["cnn"]
            )

            # Current state
            current_state = request.current_state or {}
            last_question = request.last_question or "null"
            user_input = request.user_input or "null"

            # Update step: incorporate user's response
            if user_input != "null":
                formatted_prompt = self.updater_prompt.format(
                    allowed_layers,
                    json.dumps(model_fields, indent=2),
                    json.dumps(current_state, indent=2),
                    last_question,
                    user_input
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": formatted_prompt}],
                    temperature=0.0
                )
                
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("Empty response from LLM in update step")
                current_state = json.loads(content)

            # Ask step: determine next question
            formatted_prompt = self.asker_prompt.format(
                json.dumps(model_fields, indent=2),
                json.dumps(current_state, indent=2)
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": formatted_prompt}],
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM in ask step")
            result = json.loads(content)

            return MetadataExtractionResponse(
                metadata=result,
                next_question=result.get("follow_up_question"),
                is_complete=result.get("filled", False)
            )

        except Exception as exc:
            logger.exception(f"Error extracting metadata: {exc}")
            raise


# Singleton instance
_extractor: MetadataExtractor | None = None


async def get_extractor() -> MetadataExtractor:
    """Get metadata extractor singleton.

    Returns:
        MetadataExtractor instance
    """
    global _extractor
    if _extractor is None:
        _extractor = MetadataExtractor()
    return _extractor


async def extract_model_metadata(
    request: MetadataExtractionRequest,
) -> MetadataExtractionResponse:
    """Extract model metadata from user input.

    Args:
        request: Extraction request

    Returns:
        Extraction response
    """
    extractor = await get_extractor()
    return await extractor.extract_metadata(request)
