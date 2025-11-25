"""Exact computations for transformer encoders."""

from __future__ import annotations

from typing import Any, Dict

from .utils import ValidationError, require_bool, require_dict, require_int
from .utils import dtype_bits_from_string  # only used for neural style configs if needed


def analyze_transformer(
    config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int, seq_length: int
) -> Dict[str, Any]:
    tr_cfg = require_dict(config.get("transformer_config"), "transformer_config")
    num_layers = require_int(tr_cfg, "num_layers", positive=True)
    hidden_size = require_int(tr_cfg, "hidden_size", positive=True)
    ffn_size = require_int(tr_cfg, "ffn_size", positive=True)
    num_heads = require_int(tr_cfg, "num_heads", positive=True)
    if hidden_size % num_heads != 0:
        raise ValidationError("hidden_size must be divisible by num_heads.")
    max_seq_len = require_int(tr_cfg, "max_sequence_length", positive=True)
    use_bias = require_bool(tr_cfg, "use_bias")
    use_layernorm = require_bool(tr_cfg, "use_layernorm")
    vocab_size = require_int(tr_cfg, "vocab_size", positive=True)
    include_embeddings = require_bool(tr_cfg, "include_embeddings")
    include_pos_embeddings = require_bool(tr_cfg, "include_positional_embeddings")

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
    layernorm_params = 4 * hidden_size if use_layernorm else 0  # two LNs per layer
    param_per_layer = qkv_params + out_proj_params + ffn_params + layernorm_params
    param_count += num_layers * param_per_layer

    bt = batch_size * seq_length
    flops_per_layer = 0
    flops_per_layer += 3 * _dense_flops(bt, hidden_size, hidden_size, use_bias)  # Q,K,V
    flops_per_layer += 2 * batch_size * num_heads * seq_length * seq_length * d_head  # QK^T
    flops_per_layer += batch_size * num_heads * seq_length * (3 * seq_length - 1)  # softmax
    flops_per_layer += 2 * batch_size * num_heads * seq_length * seq_length * d_head  # Attn * V
    flops_per_layer += _dense_flops(bt, hidden_size, hidden_size, use_bias)  # output projection
    flops_per_layer += 2 * bt * hidden_size  # residual adds
    flops_per_layer += _dense_flops(bt, hidden_size, ffn_size, use_bias)  # FFN1
    flops_per_layer += bt * ffn_size  # activation
    flops_per_layer += _dense_flops(bt, ffn_size, hidden_size, use_bias)  # FFN2
    if use_layernorm:
        flops_per_layer += 2 * _layernorm_flops(batch_size, seq_length, hidden_size)

    flops_total = num_layers * flops_per_layer
    activation_elements += num_layers * batch_size * seq_length * hidden_size

    return {
        "model_type": "transformer",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops_total,
        "extra": {},
    }


def _dense_flops(batch_elems: int, input_features: int, output_features: int, bias: bool) -> int:
    flops = 2 * batch_elems * input_features * output_features
    if bias:
        flops += batch_elems * output_features
    return flops


def _layernorm_flops(batch_size: int, seq_len: int, hidden_size: int) -> int:
    mean_flops = (hidden_size - 1) + 1
    variance_flops = 2 * hidden_size + (hidden_size - 1) + 1
    normalize_affine = 2 * hidden_size
    per_ln = mean_flops + variance_flops + normalize_affine
    return batch_size * seq_len * per_ln
