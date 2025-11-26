"""Exact computations for transformer encoders."""

from __future__ import annotations

from typing import Any, Dict

from utils import dtype_bits_from_string, require_bool, require_dict, require_int

ValidationError = ValueError


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
    layernorm_params = 4 * hidden_size if use_layernorm else 0  # two LNs per layer
    param_per_layer = qkv_params + out_proj_params + ffn_params + layernorm_params
    param_count += num_layers * param_per_layer
    param_bytes_per_layer = param_per_layer * dtype_bytes

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
                "name": f"transformer_layer_{i}",
                "type": "TransformerEncoderLayer",
                "params": param_per_layer,
                "param_bytes": param_bytes_per_layer,
                "flops": flops_per_layer,
                "activation_elements": per_layer_activation_elems,
                "activation_bytes": activation_bytes_per_layer,
                "flops_per_byte": flops_per_byte_layer,
            }
        )

    activation_sum_bytes = activation_elements * dtype_bytes
    activation_peak_bytes = activation_peak_elements * dtype_bytes

    return {
        "model_type": "transformer",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_peak_bytes": activation_peak_bytes,
        "activation_sum_bytes": activation_sum_bytes,
        "activation_memory_bytes": activation_peak_bytes,
        "flops_per_inference": flops_total,
        "total_flops": flops_total,
        "total_stream_bytes": (param_count * dtype_bytes) + activation_sum_bytes,
        "total_jumps": 0,
        "extra": {
            "activation_elements_sum": activation_elements,
            "activation_peak_elements": activation_peak_elements,
            "activation_peak_bytes": activation_peak_bytes,
            "layers": layer_details,
        },
        "inference_scenario": {
            "batch_size": batch_size,
            "sequence_length": seq_length,
            "precision_bits": dtype_bits,
        },
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
