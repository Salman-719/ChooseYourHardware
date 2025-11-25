"""Exact computations for LLM decoder models."""

from __future__ import annotations

from typing import Any, Dict

from .transformers import _dense_flops, _layernorm_flops
from .utils import ValidationError, require_bool, require_dict, require_int


def analyze_llm_decoder(
    config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int, seq_length: int
) -> Dict[str, Any]:
    llm_cfg = require_dict(config.get("llm_config"), "llm_config")
    num_layers = require_int(llm_cfg, "num_layers", positive=True)
    hidden_size = require_int(llm_cfg, "hidden_size", positive=True)
    ffn_size = require_int(llm_cfg, "ffn_size", positive=True)
    num_heads = require_int(llm_cfg, "num_heads", positive=True)
    if hidden_size % num_heads != 0:
        raise ValidationError("hidden_size must be divisible by num_heads.")
    vocab_size = require_int(llm_cfg, "vocab_size", positive=True)
    max_seq_len = require_int(llm_cfg, "max_sequence_length", positive=True)
    use_bias = require_bool(llm_cfg, "use_bias")
    use_layernorm = require_bool(llm_cfg, "use_layernorm")
    include_embeddings = require_bool(llm_cfg, "include_embeddings")
    include_pos_embeddings = require_bool(llm_cfg, "include_positional_embeddings")
    include_kv_cache = require_bool(llm_cfg, "include_kv_cache")

    d_head = hidden_size // num_heads
    param_count = 0
    activation_elements = 0

    if include_embeddings:
        param_count += vocab_size * hidden_size
        activation_elements += batch_size * seq_length * hidden_size
    if include_pos_embeddings:
        param_count += max_seq_len * hidden_size

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
    activation_elements += num_layers * batch_size * seq_length * hidden_size

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
    if include_kv_cache:
        kv_elements = 2 * num_layers * batch_size * seq_length * hidden_size
        kv_cache_bytes = kv_elements * dtype_bytes

    return {
        "model_type": "llm_decoder",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops_total,
        "extra": {
            "flops_per_token_decode": flops_per_token_decode,
            "kv_cache_bytes": kv_cache_bytes,
        },
    }
