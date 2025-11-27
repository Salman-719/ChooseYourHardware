"""Core orchestrator for model analysis."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import SCENARIO_KINDS
from .classical import knn, kmeans, trees
from .neural import layers, llm, transformers
from utils import dtype_bits_from_string, load_json, require_dict, require_int

ValidationError = ValueError


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

    # Metadata-extractor style: top-level usage/model/layers (plus filled/follow_up_question).
    if {"usage_constraints", "model_level", "layer_summary"}.issubset(raw.keys()):
        return _dispatch_metadata_style(raw)

    # Neural network summary style input: expect a single key like "cnn" or "neural_network".
    nn_keys = [k for k in raw.keys()]
    if len(nn_keys) == 1:
        result = layers.analyze_neural_summary(require_dict(raw[nn_keys[0]], nn_keys[0]))
        scenario = _build_scenario(
            result["inference_scenario"]["batch_size"],
            result["inference_scenario"]["sequence_length"],
            result["inference_scenario"]["precision_bits"],
            "single_pass",
        )
        result["inference_scenario"] = scenario
        return result
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
        result = knn.analyze_knn(raw, dtype_bits, dtype_bytes, batch_size)
        scenario_kind = "single_pass"
    elif model_type == "kmeans":
        result = kmeans.analyze_kmeans(raw, dtype_bits, dtype_bytes, batch_size)
        scenario_kind = "per_iteration"
    elif model_type == "tree":
        result = trees.analyze_tree(raw, dtype_bits, dtype_bytes, batch_size)
        scenario_kind = "single_pass"
    elif model_type in {"random_forest", "gradient_boosted_trees"}:
        result = trees.analyze_ensemble(raw, dtype_bits, dtype_bytes, batch_size)
        scenario_kind = "single_pass"
    elif model_type == "neural_network":
        nn_root = require_dict(raw.get("nn_config"), "nn_config")
        result = layers.analyze_neural_summary(nn_root)
        scenario_kind = "single_pass"
    elif model_type == "transformer":
        if seq_length is None:
            raise ValidationError("sequence_length is required for transformer models.")
        result = transformers.analyze_transformer(raw, dtype_bits, dtype_bytes, batch_size, seq_length)
        scenario_kind = "full_sequence"
    elif model_type == "llm_decoder":
        if seq_length is None:
            raise ValidationError("sequence_length is required for llm_decoder models.")
        result = llm.analyze_llm_decoder(raw, dtype_bits, dtype_bytes, batch_size, seq_length)
        scenario_kind = "full_sequence+decode"
    else:
        raise ValidationError(f"Unhandled model_type '{model_type}'.")

    # Attach scenario and activation clarity for hardware matching.
    scenario = _build_scenario(batch_size, seq_length, dtype_bits, scenario_kind)
    result["inference_scenario"] = scenario
    if "activation_memory_bytes" in result:
        act_bytes = result["activation_memory_bytes"]
        result.setdefault("activation_sum_bytes", act_bytes)
        result.setdefault("activation_peak_bytes", act_bytes)
        result["activation_memory_bytes"] = result.get("activation_memory_bytes", act_bytes)
    # Optional XLA flag for TPU-compiled models
    is_xla = raw.get("is_XLA", False)
    if not isinstance(is_xla, bool):
        raise ValidationError("is_XLA must be a boolean when provided.")
    result["is_XLA"] = is_xla

    # Optional cost and power constraints
    max_cost = raw.get("max_cost_usd")
    if max_cost is not None and (not isinstance(max_cost, (int, float)) or max_cost <= 0):
        raise ValidationError("max_cost_usd must be a positive number when provided.")
    max_power = raw.get("max_power_w")
    if max_power is not None and (not isinstance(max_power, (int, float)) or max_power <= 0):
        raise ValidationError("max_power_w must be a positive number when provided.")
    # result["max_cost_usd"] = max_cost
    # result["max_power_w"] = max_power

    # Expose usage constraints for downstream matcher
    result["usage_constraints"] = {
        "batch_size": batch_size,
        "max_cost_usd": max_cost,
        "max_power_w": max_power,
    }
    return result


def _unwrap_metadata_container(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Handle API responses that wrap the extracted state in a 'metadata' key."""
    if "metadata" in raw:
        return require_dict(raw["metadata"], "metadata")
    return raw


def _dispatch_metadata_style(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Handle metadata-extractor style payloads that include usage/model/layers."""
    model_level = require_dict(raw.get("model_level"), "model_level")
    model_type = model_level.get("model_type")
    is_xla = _get_bool_with_default(model_level, "is_XLA", False)
    usage = require_dict(raw.get("usage_constraints"), "usage_constraints")
    max_cost = usage.get("max_cost_usd")
    if max_cost is not None and (not isinstance(max_cost, (int, float)) or max_cost <= 0):
        raise ValidationError("usage_constraints.max_cost_usd must be a positive number when provided.")
    max_power = usage.get("max_power_w")
    if max_power is not None and (not isinstance(max_power, (int, float)) or max_power <= 0):
        raise ValidationError("usage_constraints.max_power_w must be a positive number when provided.")
    if model_type in {"transformer", "transformer_encoder"}:
        result = _analyze_transformer_from_metadata(raw)
        scenario_kind = "full_sequence"
    elif model_type in {"llm", "llm_decoder"}:
        result = _analyze_llm_from_metadata(raw)
        scenario_kind = "full_sequence+decode"
    else:
        result = layers.analyze_neural_summary(raw)
        scenario_kind = "single_pass"
    scenario = _build_scenario(
        result["inference_scenario"]["batch_size"],
        result["inference_scenario"]["sequence_length"],
        result["inference_scenario"]["precision_bits"],
        scenario_kind,
    )
    result["inference_scenario"] = scenario
    result["is_XLA"] = is_xla
    # result["max_cost_usd"] = max_cost
    # result["max_power_w"] = max_power
    result["usage_constraints"] = {
        "batch_size": usage.get("batch_size"),
        "target_latency_s": usage.get("target_latency_s"),
        "max_cost_usd": max_cost,
        "max_power_w": max_power,
    }
    return result


def _analyze_transformer_from_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    usage = require_dict(raw.get("usage_constraints"), "usage_constraints")
    model_level = require_dict(raw.get("model_level"), "model_level")
    batch_size = require_int(usage, "batch_size", positive=True)

    precision = model_level.get("precision")
    if not isinstance(precision, str):
        raise ValidationError("model_level.precision must be provided for transformer models.")
    dtype_bits = dtype_bits_from_string(precision)
    dtype_bytes = dtype_bits // 8

    seq_length = model_level.get("sequence_length")
    if not isinstance(seq_length, int) or seq_length <= 0:
        raise ValidationError("model_level.sequence_length must be a positive integer for transformer models.")

    hidden = model_level.get("hidden_size", model_level.get("hidden_dim"))
    if not isinstance(hidden, int) or hidden <= 0:
        raise ValidationError("model_level.hidden_size (or hidden_dim) must be a positive integer.")
    num_heads = require_int(model_level, "num_heads", positive=True)
    num_layers = require_int(model_level, "num_layers", positive=True)
    ffn_size = model_level.get("ffn_size", 4 * hidden)
    if not isinstance(ffn_size, int) or ffn_size <= 0:
        raise ValidationError("model_level.ffn_size must be a positive integer.")

    max_seq_len = model_level.get("max_sequence_length", seq_length)
    if not isinstance(max_seq_len, int) or max_seq_len <= 0:
        raise ValidationError("model_level.max_sequence_length must be a positive integer.")

    vocab_size = require_int(model_level, "vocab_size", positive=True)
    use_bias = _get_bool_with_default(model_level, "use_bias", True)
    use_layernorm = _get_bool_with_default(model_level, "use_layernorm", True)
    include_embeddings = _get_bool_with_default(model_level, "include_embeddings", True)
    include_pos_embeddings = _get_bool_with_default(model_level, "include_positional_embeddings", True)

    config = {
        "model_type": "transformer",
        "precision": precision,
        "inference_config": {"batch_size": batch_size, "sequence_length": seq_length},
        "transformer_config": {
            "num_layers": num_layers,
            "hidden_size": hidden,
            "ffn_size": ffn_size,
            "num_heads": num_heads,
            "max_sequence_length": max_seq_len,
            "use_bias": use_bias,
            "use_layernorm": use_layernorm,
            "vocab_size": vocab_size,
            "include_embeddings": include_embeddings,
            "include_positional_embeddings": include_pos_embeddings,
        },
    }
    return transformers.analyze_transformer(config, dtype_bits, dtype_bytes, batch_size, seq_length)


def _analyze_llm_from_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    usage = require_dict(raw.get("usage_constraints"), "usage_constraints")
    model_level = require_dict(raw.get("model_level"), "model_level")
    batch_size = require_int(usage, "batch_size", positive=True)

    precision = model_level.get("precision")
    if not isinstance(precision, str):
        raise ValidationError("model_level.precision must be provided for LLM models.")
    dtype_bits = dtype_bits_from_string(precision)
    dtype_bytes = dtype_bits // 8

    seq_length = model_level.get("context_length", model_level.get("sequence_length"))
    if not isinstance(seq_length, int) or seq_length <= 0:
        raise ValidationError("model_level.context_length must be a positive integer for LLM models.")

    hidden = model_level.get("hidden_size", model_level.get("hidden_dim"))
    if not isinstance(hidden, int) or hidden <= 0:
        raise ValidationError("model_level.hidden_size (or hidden_dim) must be a positive integer.")
    num_heads = require_int(model_level, "num_heads", positive=True)
    num_layers = require_int(model_level, "num_layers", positive=True)
    ffn_size = model_level.get("ffn_size", 4 * hidden)
    if not isinstance(ffn_size, int) or ffn_size <= 0:
        raise ValidationError("model_level.ffn_size must be a positive integer.")

    max_seq_len = model_level.get("max_sequence_length", seq_length)
    if not isinstance(max_seq_len, int) or max_seq_len <= 0:
        raise ValidationError("model_level.max_sequence_length must be a positive integer.")

    vocab_size = require_int(model_level, "vocab_size", positive=True)
    use_bias = _get_bool_with_default(model_level, "use_bias", True)
    use_layernorm = _get_bool_with_default(model_level, "use_layernorm", True)
    include_embeddings = _get_bool_with_default(model_level, "include_embeddings", True)
    include_pos_embeddings = _get_bool_with_default(model_level, "include_positional_embeddings", True)
    include_kv_cache = _get_bool_with_default(model_level, "include_kv_cache", True)

    config = {
        "model_type": "llm_decoder",
        "precision": precision,
        "inference_config": {"batch_size": batch_size, "sequence_length": seq_length},
        "llm_config": {
            "num_layers": num_layers,
            "hidden_size": hidden,
            "ffn_size": ffn_size,
            "num_heads": num_heads,
            "vocab_size": vocab_size,
            "max_sequence_length": max_seq_len,
            "use_bias": use_bias,
            "use_layernorm": use_layernorm,
            "include_embeddings": include_embeddings,
            "include_positional_embeddings": include_pos_embeddings,
            "include_kv_cache": include_kv_cache,
        },
    }
    return llm.analyze_llm_decoder(config, dtype_bits, dtype_bytes, batch_size, seq_length)


def _get_bool_with_default(obj: Dict[str, Any], key: str, default: bool) -> bool:
    val = obj.get(key, default)
    if not isinstance(val, bool):
        raise ValidationError(f"{key} must be a boolean when provided.")
    return val


def _build_scenario(batch_size: int, seq_length: Optional[int], dtype_bits: int, scenario_kind: str) -> Dict[str, Any]:
    if scenario_kind not in SCENARIO_KINDS:
        raise ValidationError(f"scenario_kind must be one of {SCENARIO_KINDS} (got {scenario_kind}).")
    return {
        "batch_size": batch_size,
        "sequence_length": seq_length if seq_length is not None else None,
        "precision_bits": dtype_bits,
        "scenario_kind": scenario_kind,
    }
