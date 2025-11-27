"""Exact computations for LLM decoder models."""

from __future__ import annotations

from typing import Any, Dict

from .transformers import _dense_flops, _layernorm_flops
from utils import require_bool, require_dict, require_int

ValidationError = ValueError


def analyze_llm_decoder(
    config: Dict[str, Any] | None,
    dtype_bits: int,
    dtype_bytes: int,
    batch_size: int,
    seq_length: int,
    llm_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    # Prefer explicit metadata; fall back to llm_config/model_level within config.
    llm_cfg_raw = None
    if llm_metadata is not None:
        llm_cfg_raw = llm_metadata
    elif config is not None:
        llm_cfg_raw = config.get("llm_config") or config.get("model_level")

    if llm_cfg_raw is None:
        raise ValidationError("llm_decoder requires llm_metadata or llm_config/model_level.")

    llm_cfg = require_dict(llm_cfg_raw, "llm_metadata")

    def _require_int_fallback(cfg: Dict[str, Any], primary: str, fallback: str | None = None) -> int:
        if primary in cfg:
            return require_int(cfg, primary, positive=True)
        if fallback and fallback in cfg:
            return require_int(cfg, fallback, positive=True)
        raise ValidationError(f"Missing required field: {primary}" + (f" or {fallback}" if fallback else ""))

    num_layers = _require_int_fallback(llm_cfg, "num_layers")
    hidden_size = _require_int_fallback(llm_cfg, "hidden_size", "hidden_dim")
    ffn_size = _require_int_fallback(llm_cfg, "ffn_size")
    num_heads = _require_int_fallback(llm_cfg, "num_heads")
    if hidden_size % num_heads != 0:
        raise ValidationError("hidden_size must be divisible by num_heads.")
    vocab_size = _require_int_fallback(llm_cfg, "vocab_size")
    if "max_context_tokens" in llm_cfg:
        max_seq_len = require_int(llm_cfg, "max_context_tokens", positive=True)
    elif "max_sequence_length" in llm_cfg:
        max_seq_len = require_int(llm_cfg, "max_sequence_length", positive=True)
    else:
        raise ValidationError("llm_decoder must specify max_context_tokens or max_sequence_length.")
    use_bias = require_bool(llm_cfg, "use_bias") if "use_bias" in llm_cfg else False
    use_layernorm = require_bool(llm_cfg, "use_layernorm") if "use_layernorm" in llm_cfg else True
    include_embeddings = require_bool(llm_cfg, "include_embeddings") if "include_embeddings" in llm_cfg else True
    include_pos_embeddings = require_bool(llm_cfg, "include_positional_embeddings") if "include_positional_embeddings" in llm_cfg else True
    kv_flag = llm_cfg.get("uses_kv_cache") if "uses_kv_cache" in llm_cfg else llm_cfg.get("include_kv_cache")
    if kv_flag is None:
        raise ValidationError("llm_decoder must specify uses_kv_cache/include_kv_cache.")
    if not isinstance(kv_flag, bool):
        raise ValidationError("uses_kv_cache/include_kv_cache must be boolean.")
    include_kv_cache = kv_flag
    if seq_length > max_seq_len:
        raise ValidationError("sequence_length must be <= max_context_tokens for llm_decoder.")

    d_head = hidden_size // num_heads
    param_count = 0
    activation_elements = 0
    activation_peak_elements = 0
    layer_details = []

    if include_embeddings:
        param_count += vocab_size * hidden_size
        elems = batch_size * seq_length * hidden_size
        activation_elements += elems
        activation_peak_elements = max(activation_peak_elements, elems)
        layer_details.append(
            {
                "name": "token_embeddings",
                "type": "Embedding",
                "params": vocab_size * hidden_size,
                "param_bytes": (vocab_size * hidden_size) * dtype_bytes,
                "flops": 0,
                "activation_elements": elems,
                "activation_bytes": elems * dtype_bytes,
                "flops_per_byte": 0.0,
            }
        )
    if include_pos_embeddings:
        param_count += max_seq_len * hidden_size
        layer_details.append(
            {
                "name": "positional_embeddings",
                "type": "PositionalEmbedding",
                "params": max_seq_len * hidden_size,
                "param_bytes": (max_seq_len * hidden_size) * dtype_bytes,
                "flops": 0,
                "activation_elements": 0,
                "activation_bytes": 0,
                "flops_per_byte": 0.0,
            }
        )

    qkv_params = 3 * (hidden_size * hidden_size + (hidden_size if use_bias else 0))
    out_proj_params = hidden_size * hidden_size + (hidden_size if use_bias else 0)
    ffn_params = (
        hidden_size * ffn_size
        + (ffn_size if use_bias else 0)
        + ffn_size * hidden_size
        + (hidden_size if use_bias else 0)
    )
    layernorm_params = 4 * hidden_size if use_layernorm else 0
    param_per_layer = qkv_params + out_proj_params + ffn_params + layernorm_params
    param_count += num_layers * param_per_layer
    param_bytes_per_layer = param_per_layer * dtype_bytes

    bt = batch_size * seq_length
    flops_per_layer = 0
    flops_per_layer += 3 * _dense_flops(bt, hidden_size, hidden_size, use_bias)
    flops_per_layer += 2 * batch_size * num_heads * seq_length * seq_length * d_head  # QK^T
    flops_per_layer += batch_size * num_heads * seq_length * (3 * seq_length - 1)  # softmax
    flops_per_layer += 2 * batch_size * num_heads * seq_length * seq_length * d_head  # Attn * V
    flops_per_layer += _dense_flops(bt, hidden_size, hidden_size, use_bias)
    flops_per_layer += 2 * bt * hidden_size  # residuals
    flops_per_layer += _dense_flops(bt, hidden_size, ffn_size, use_bias)
    flops_per_layer += bt * ffn_size
    flops_per_layer += _dense_flops(bt, ffn_size, hidden_size, use_bias)
    if use_layernorm:
        flops_per_layer += 2 * _layernorm_flops(batch_size, seq_length, hidden_size)
    mask_flops = batch_size * num_heads * (seq_length * (seq_length - 1) // 2)
    flops_per_layer += mask_flops

    flops_total = num_layers * flops_per_layer
    per_layer_activation_elems = batch_size * seq_length * hidden_size
    activation_elements += num_layers * per_layer_activation_elems
    activation_peak_elements = max(activation_peak_elements, per_layer_activation_elems)

    activation_bytes_per_layer = per_layer_activation_elems * dtype_bytes
    flops_per_byte_layer = (
        flops_per_layer / (param_bytes_per_layer + activation_bytes_per_layer)
        if (param_bytes_per_layer + activation_bytes_per_layer) > 0
        else 0.0
    )
    for i in range(num_layers):
        layer_details.append(
            {
                "name": f"decoder_layer_{i}",
                "type": "TransformerDecoderLayer",
                "params": param_per_layer,
                "param_bytes": param_bytes_per_layer,
                "flops": flops_per_layer,
                "activation_elements": per_layer_activation_elems,
                "activation_bytes": activation_bytes_per_layer,
                "flops_per_byte": flops_per_byte_layer,
            }
        )

    flops_decode_layer = 0
    flops_decode_layer += 3 * _dense_flops(batch_size, hidden_size, hidden_size, use_bias)
    flops_decode_layer += 2 * batch_size * seq_length * hidden_size
    flops_decode_layer += batch_size * num_heads * (3 * seq_length - 1)
    flops_decode_layer += 2 * batch_size * seq_length * hidden_size
    flops_decode_layer += _dense_flops(batch_size, hidden_size, hidden_size, use_bias)
    flops_decode_layer += 2 * batch_size * hidden_size
    flops_decode_layer += _dense_flops(batch_size, hidden_size, ffn_size, use_bias)
    flops_decode_layer += batch_size * ffn_size
    flops_decode_layer += _dense_flops(batch_size, ffn_size, hidden_size, use_bias)
    if use_layernorm:
        flops_decode_layer += 2 * _layernorm_flops(batch_size, 1, hidden_size)
    flops_per_token_decode = num_layers * flops_decode_layer

    kv_cache_bytes = 0
    has_kv_cache = include_kv_cache
    if include_kv_cache:
        kv_elements = 2 * num_layers * batch_size * seq_length * hidden_size
        kv_cache_bytes = kv_elements * dtype_bytes

    activation_sum_bytes = activation_elements * dtype_bytes
    activation_peak_bytes = activation_peak_elements * dtype_bytes
    activation_memory_bytes = max(activation_peak_bytes, kv_cache_bytes) if has_kv_cache else activation_peak_bytes

    return {
        "model_type": "llm_decoder",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_peak_bytes": activation_peak_bytes,
        "activation_sum_bytes": activation_sum_bytes,
        "activation_memory_bytes": activation_memory_bytes,
        "activation_memory_is_exact": True,
        "flops_per_inference": flops_total,
        "total_flops": flops_total,
        "flops_prefill": flops_total,
        "flops_per_token_decode": flops_per_token_decode,
        "total_stream_bytes": (param_count * dtype_bytes) + activation_sum_bytes,
        "total_jumps": 0,
        "extra": {
            "flops_per_token_decode": flops_per_token_decode,
            "kv_cache_bytes": kv_cache_bytes,
            "activation_elements_sum": activation_elements,
            "activation_peak_elements": activation_peak_elements,
            "activation_peak_bytes": activation_peak_bytes,
        },
        "kv_cache_bytes": kv_cache_bytes,
        "has_kv_cache": has_kv_cache,
        "inference_scenario": {
            "batch_size": batch_size,
            "sequence_length": seq_length,
            "precision_bits": dtype_bits,
            "scenario_kind": "full_sequence+decode",
        },
    }
