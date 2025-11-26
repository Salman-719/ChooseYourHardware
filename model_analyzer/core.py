"""Core orchestrator for model analysis."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import knn, kmeans, llm, nn, transformers, trees
from .utils import ValidationError, dtype_bits_from_string, load_json, require_bool, require_dict, require_int


def analyze_model(model_json: str) -> str:
    """Public API: analyze a model configuration JSON string."""
    raw = load_json(model_json)
    result = _dispatch(raw)
    import json

    return json.dumps(result, indent=2, sort_keys=True)


def _dispatch(raw: Dict[str, Any]) -> Dict[str, Any]:
    raw = _unwrap_metadata_container(raw)

    if "model_type" in raw:
        return _dispatch_standard(raw)

    # Metadata-extractor style: top-level usage/model/layers (plus filled/follow_up_question), or
    # inference_config/model_level/layer_summary.
    if ({"usage_constraints", "model_level", "layer_summary"}.issubset(raw.keys())
            or ({"inference_config", "model_level", "layer_summary"}.issubset(raw.keys()))):
        return nn.analyze_neural_summary(raw)

    # Neural network summary style input: expect a single key like "cnn" or "neural_network".
    nn_keys = [k for k in raw.keys()]
    if len(nn_keys) == 1:
        return nn.analyze_neural_summary(require_dict(raw[nn_keys[0]], nn_keys[0]))
    raise ValidationError("Unable to determine model_type; provide 'model_type' or a single neural network root key.")


def _dispatch_standard(raw: Dict[str, Any]) -> Dict[str, Any]:
    model_type = raw.get("model_type")
    if model_type not in {
        "knn",
        "kmeans",
        "tree",
        "random_forest",
        "gradient_boosted_trees",
        "neural_network",
        "transformer",
        "llm_decoder",
    }:
        raise ValidationError(f"Invalid or missing model_type: {model_type}")

    dtype_bits = raw.get("dtype_bits")
    if isinstance(dtype_bits, int):
        if dtype_bits <= 0 or dtype_bits % 8 != 0:
            raise ValidationError("dtype_bits must be a positive multiple of 8.")
    else:
        precision = raw.get("precision")
        if not isinstance(precision, str):
            raise ValidationError("Either dtype_bits (int) or precision (string) must be provided.")
        dtype_bits = dtype_bits_from_string(precision)
    dtype_bytes = dtype_bits // 8

    inference_cfg = require_dict(raw.get("inference_config"), "inference_config")
    batch_size = require_int(inference_cfg, "batch_size", positive=True)
    seq_length = inference_cfg.get("sequence_length")
    if model_type in {"transformer", "llm_decoder"}:
        if seq_length is None or not isinstance(seq_length, int) or seq_length <= 0:
            raise ValidationError("sequence_length must be a positive integer for transformer/llm_decoder.")
    elif seq_length is not None:
        if not isinstance(seq_length, int) or seq_length <= 0:
            raise ValidationError("sequence_length must be a positive integer when provided.")

    if model_type == "knn":
        result = knn.analyze_knn(raw, dtype_bits, dtype_bytes, batch_size)
    elif model_type == "kmeans":
        result = kmeans.analyze_kmeans(raw, dtype_bits, dtype_bytes, batch_size)
    elif model_type == "tree":
        result = trees.analyze_tree(raw, dtype_bits, dtype_bytes, batch_size)
    elif model_type in {"random_forest", "gradient_boosted_trees"}:
        result = trees.analyze_ensemble(raw, dtype_bits, dtype_bytes, batch_size)
    elif model_type == "neural_network":
        nn_root = require_dict(raw.get("nn_config"), "nn_config")
        result = nn.analyze_neural_summary(nn_root)
    elif model_type == "transformer":
        if seq_length is None:
            raise ValidationError("sequence_length is required for transformer models.")
        result = transformers.analyze_transformer(raw, dtype_bits, dtype_bytes, batch_size, seq_length)
    elif model_type == "llm_decoder":
        if seq_length is None:
            raise ValidationError("sequence_length is required for llm_decoder models.")
        llm_meta = require_dict(raw.get("llm_metadata"), "llm_metadata")
        num_layers = require_int(llm_meta, "num_layers", positive=True)
        hidden_size = require_int(llm_meta, "hidden_size", positive=True)
        ffn_size = require_int(llm_meta, "ffn_size", positive=True)
        num_heads = require_int(llm_meta, "num_heads", positive=True)
        if hidden_size % num_heads != 0:
            raise ValidationError("hidden_size must be divisible by num_heads.")
        max_ctx = require_int(llm_meta, "max_context_tokens", positive=True)
        if seq_length > max_ctx:
            raise ValidationError("sequence_length must be <= max_context_tokens.")
        vocab_size = require_int(llm_meta, "vocab_size", positive=True)
        uses_kv_cache = require_bool(llm_meta, "uses_kv_cache")
        result = llm.analyze_llm_decoder(
            raw,
            dtype_bits,
            dtype_bytes,
            batch_size,
            seq_length,
            llm_metadata={
                "num_layers": num_layers,
                "hidden_size": hidden_size,
                "ffn_size": ffn_size,
                "num_heads": num_heads,
                "max_context_tokens": max_ctx,
                "vocab_size": vocab_size,
                "uses_kv_cache": uses_kv_cache,
            },
        )
    else:
        raise ValidationError(f"Unhandled model_type '{model_type}'.")

    # Attach scenario and activation clarity for hardware matching.
    if "inference_scenario" not in result:
        result["inference_scenario"] = {
            "batch_size": batch_size,
            "sequence_length": seq_length if seq_length is not None else None,
            "precision_bits": dtype_bits,
        }
    if "activation_memory_bytes" in result:
        act_bytes = result["activation_memory_bytes"]
        result.setdefault("activation_sum_bytes", act_bytes)
        result.setdefault("activation_peak_bytes", act_bytes)
        # Prefer peak as the canonical activation_memory_bytes.
        result["activation_memory_bytes"] = result["activation_peak_bytes"]

    expected_scenario = {
        "batch_size": batch_size,
        "sequence_length": seq_length if seq_length is not None else None,
        "precision_bits": dtype_bits,
    }
    if result.get("inference_scenario") != expected_scenario:
        raise ValidationError("Model inference_scenario must match inference_config (batch_size, sequence_length, precision_bits).")
    return result


def _unwrap_metadata_container(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Handle API responses that wrap the extracted state in a 'metadata' key."""
    if "metadata" in raw:
        return require_dict(raw["metadata"], "metadata")
    return raw
