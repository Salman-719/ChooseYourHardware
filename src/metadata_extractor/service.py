"""Metadata extraction service using OpenAI LLM."""

from __future__ import annotations

import json
import copy
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
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        
        # Load prompts and templates
        prompts_dir = Path(__file__).parent / "prompts"
        
        with open(prompts_dir / "metadata_extractor_asker.txt") as f:
            self.asker_prompt = f.read()
        
        with open(prompts_dir / "metadata_extractor_updater.txt") as f:
            self.updater_prompt = f.read()
        
        with open(prompts_dir / "model_fields.json") as f:
            self.model_fields_templates = json.load(f)
        
        with open(prompts_dir / "layer_types.json") as f:
            # Single catalog of allowed layers; used for all model types.
            self.layer_types = json.load(f)

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
            classical_models = {"knn", "kmeans", "tree", "random_forest", "gradient_boosted_trees"}
            if request.model_type in classical_models:
                def ensure_base_state(template: Dict[str, Any], current: Dict[str, Any] | None) -> Dict[str, Any]:
                    state = copy.deepcopy(template)
                    if current:
                        # Overlay user-provided state
                        state.update(current)
                        if "inference_config" in current and isinstance(current["inference_config"], dict):
                            state.setdefault("inference_config", {})
                            state["inference_config"].update(current["inference_config"])
                        # Merge nested configs
                        for key in ("knn_config", "kmeans_config", "tree_config", "ensemble_config"):
                            if key in current and isinstance(current[key], dict):
                                state.setdefault(key, {})
                                state[key].update(current[key])
                    state["model_type"] = request.model_type
                    return state

                def missing_fields_knn(state: Dict[str, Any]) -> list[str]:
                    missing = []
                    for fld in ("precision",):
                        if not state.get(fld):
                            missing.append(fld)
                    if not (state.get("inference_config") or {}).get("batch_size"):
                        missing.append("batch_size")
                    cfg = state.get("knn_config") or {}
                    for fld in ("num_train_samples", "num_features", "k", "distance_metric", "include_sqrt", "selection_algorithm"):
                        if cfg.get(fld) in (None, ""):
                            missing.append(f"knn_config.{fld}")
                    return missing

                def missing_fields_kmeans(state: Dict[str, Any]) -> list[str]:
                    missing = []
                    if not state.get("precision"):
                        missing.append("precision")
                    if not (state.get("inference_config") or {}).get("batch_size"):
                        missing.append("batch_size")
                    cfg = state.get("kmeans_config") or {}
                    for fld in ("num_points", "num_features", "num_clusters", "cluster_sizes", "distance_metric", "include_sqrt", "num_iterations"):
                        if cfg.get(fld) in (None, ""):
                            missing.append(f"kmeans_config.{fld}")
                    return missing

                def missing_fields_tree(state: Dict[str, Any], tree_cfg: Dict[str, Any] | None = None) -> list[str]:
                    missing = []
                    if not state.get("precision"):
                        missing.append("precision")
                    if not (state.get("inference_config") or {}).get("batch_size"):
                        missing.append("batch_size")
                    cfg = tree_cfg if tree_cfg is not None else (state.get("tree_config") or {})
                    for fld in ("num_internal_nodes", "num_leaves", "output_dim", "average_path_length", "input_dim"):
                        if cfg.get(fld) in (None, ""):
                            missing.append(f"tree_config.{fld}")
                    return missing

                def missing_fields_ensemble(state: Dict[str, Any]) -> list[str]:
                    missing = []
                    if not state.get("precision"):
                        missing.append("precision")
                    if not (state.get("inference_config") or {}).get("batch_size"):
                        missing.append("batch_size")
                    cfg = state.get("ensemble_config") or {}
                    if cfg.get("num_trees") in (None, ""):
                        missing.append("ensemble_config.num_trees")
                    tree_cfg = cfg.get("tree_config") or {}
                    missing.extend(missing_fields_tree(state, tree_cfg=tree_cfg))
                    return missing

                # Build base template from prompts file (or minimal skeleton if missing)
                model_fields_template = self.model_fields_templates.get(request.model_type) or {}
                if not isinstance(model_fields_template, dict):
                    raise ValueError(f"Unsupported model_type '{request.model_type}' for metadata extraction.")
                base_state = ensure_base_state(model_fields_template, request.current_state)

                if request.model_type == "knn":
                    missing = missing_fields_knn(base_state)
                elif request.model_type == "kmeans":
                    missing = missing_fields_kmeans(base_state)
                elif request.model_type == "tree":
                    missing = missing_fields_tree(base_state)
                else:
                    missing = missing_fields_ensemble(base_state)

                if missing:
                    question = "Please provide the following fields: " + ", ".join(missing) + "."
                    base_state["filled"] = False
                    base_state["follow_up_question"] = question
                    return MetadataExtractionResponse(metadata=base_state, next_question=question, is_complete=False)

                base_state["filled"] = True
                base_state["follow_up_question"] = ""
                return MetadataExtractionResponse(metadata=base_state, next_question="", is_complete=True)

            # Get model fields template for the model type

            model_fields_template = self.model_fields_templates.get(request.model_type)
            if not isinstance(model_fields_template, dict):
                raise ValueError(f"Unsupported model_type '{request.model_type}' for metadata extraction.")
            model_fields = copy.deepcopy(model_fields_template)
            model_fields["filled"] = False
            model_fields["follow_up_question"] = "null"

            if request.model_type == "llm":
                # For LLM metadata style, require only the model_level + usage fields needed by the analyzer.
                required_fields = [
                    "precision",
                    "context_length",
                    "hidden_dim",
                    "num_heads",
                    "num_layers",
                    "ffn_size",
                    "max_sequence_length",
                    "vocab_size",
                    "include_embeddings",
                    "include_positional_embeddings",
                    "include_kv_cache",
                    "use_bias",
                    "use_layernorm",
                ]
                current_state = request.current_state or {}
                usage = current_state.get("usage_constraints") or {}
                model_level = current_state.get("model_level") or {}
                missing = []
                if not usage.get("batch_size"):
                    missing.append("usage_constraints.batch_size")
                for fld in required_fields:
                    if model_level.get(fld) in (None, ""):
                        missing.append(f"model_level.{fld}")
                if missing:
                    question = "Please provide the following fields: " + ", ".join(missing) + "."
                    current_state["filled"] = False
                    current_state["follow_up_question"] = question
                    return MetadataExtractionResponse(metadata=current_state, next_question=question, is_complete=False)
                current_state["filled"] = True
                current_state["follow_up_question"] = ""
                return MetadataExtractionResponse(metadata=current_state, next_question="", is_complete=True)

            # Get allowed layers for the model type
            allowed_layers = self.layer_types.get(request.model_type) or self.layer_types.get("all_layers") or []

            # Current state
            current_state = request.current_state or {}
            last_question = request.last_question or "null"
            user_input = request.user_input or "null"

            # Update step: incorporate user's response
            if user_input != "null":
                if self.client is None:
                    raise ValueError("OPENAI_API_KEY is required for metadata extraction.")
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

            if self.client is None:
                raise ValueError("OPENAI_API_KEY is required for metadata extraction.")

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
