"""Core orchestrator for model analysis."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import knn, kmeans, llm, nn, transformers, trees
from .utils import ValidationError, dtype_bits_from_string, load_json, require_dict, require_int


def analyze_model(model_json: str) -> str:
    """Public API: analyze a model configuration JSON string."""
    raw = load_json(model_json)
    result = _dispatch(raw)
    import json

    return json.dumps(result, indent=2, sort_keys=True)


def _dispatch(raw: Dict[str, Any]) -> Dict[str, Any]:
    if "model_type" in raw:
        return _dispatch_standard(raw)
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
    if seq_length is not None:
        if not isinstance(seq_length, int) or seq_length <= 0:
            raise ValidationError("sequence_length must be a positive integer when provided.")

    if model_type == "knn":
        return knn.analyze_knn(raw, dtype_bits, dtype_bytes, batch_size)
    if model_type == "kmeans":
        return kmeans.analyze_kmeans(raw, dtype_bits, dtype_bytes, batch_size)
    if model_type == "tree":
        return trees.analyze_tree(raw, dtype_bits, dtype_bytes, batch_size)
    if model_type in {"random_forest", "gradient_boosted_trees"}:
        return trees.analyze_ensemble(raw, dtype_bits, dtype_bytes, batch_size)
    if model_type == "neural_network":
        nn_root = require_dict(raw.get("nn_config"), "nn_config")
        return nn.analyze_neural_summary(nn_root)
    if model_type == "transformer":
        if seq_length is None:
            raise ValidationError("sequence_length is required for transformer models.")
        return transformers.analyze_transformer(raw, dtype_bits, dtype_bytes, batch_size, seq_length)
    if model_type == "llm_decoder":
        if seq_length is None:
            raise ValidationError("sequence_length is required for llm_decoder models.")
        return llm.analyze_llm_decoder(raw, dtype_bits, dtype_bytes, batch_size, seq_length)

    raise ValidationError(f"Unhandled model_type '{model_type}'.")
