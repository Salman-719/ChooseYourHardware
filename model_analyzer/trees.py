"""Exact computations for trees and ensembles."""

from __future__ import annotations

from typing import Any, Dict

from .utils import ValidationError, require_dict, require_int


def analyze_tree(config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int) -> Dict[str, Any]:
    tree_cfg = require_dict(config.get("tree_config"), "tree_config")
    num_internal = require_int(tree_cfg, "num_internal_nodes", positive=True)
    num_leaves = require_int(tree_cfg, "num_leaves", positive=True)
    output_dim = require_int(tree_cfg, "output_dim", positive=True)
    avg_path = tree_cfg.get("average_path_length")
    if not isinstance(avg_path, (int, float)) or avg_path <= 0:
        raise ValidationError("average_path_length must be a positive number.")
    input_dim = tree_cfg.get("input_dim")
    if input_dim is not None:
        if not isinstance(input_dim, int) or input_dim <= 0:
            raise ValidationError("input_dim must be a positive integer when provided.")
        activation_elements = batch_size * input_dim + batch_size * output_dim
    else:
        activation_elements = batch_size * output_dim

    param_count = num_internal + num_leaves * output_dim
    flops = batch_size * avg_path
    return {
        "model_type": "tree",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops,
        "extra": {},
    }


def analyze_ensemble(config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int) -> Dict[str, Any]:
    ensemble_cfg = require_dict(config.get("ensemble_config"), "ensemble_config")
    num_trees = require_int(ensemble_cfg, "num_trees", positive=True)
    tree_cfg = require_dict(ensemble_cfg.get("tree_config"), "tree_config")
    num_internal = require_int(tree_cfg, "num_internal_nodes", positive=True)
    num_leaves = require_int(tree_cfg, "num_leaves", positive=True)
    output_dim = require_int(tree_cfg, "output_dim", positive=True)
    avg_path = tree_cfg.get("average_path_length")
    if not isinstance(avg_path, (int, float)) or avg_path <= 0:
        raise ValidationError("average_path_length must be a positive number.")
    input_dim = require_int(tree_cfg, "input_dim", positive=True)

    param_per_tree = num_internal + num_leaves * output_dim
    param_count = num_trees * param_per_tree
    flops = batch_size * num_trees * avg_path
    activation_elements = batch_size * input_dim + batch_size * output_dim

    return {
        "model_type": config["model_type"],
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops,
        "extra": {},
    }
