"""Exact computations for KNN models."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from .utils import ValidationError, require_bool, require_dict, require_int


def analyze_knn(config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int) -> Dict[str, Any]:
    knn_cfg = require_dict(config.get("knn_config"), "knn_config")
    num_train = require_int(knn_cfg, "num_train_samples", positive=True)
    num_features = require_int(knn_cfg, "num_features", positive=True)
    k = require_int(knn_cfg, "k", positive=True)
    distance_metric = knn_cfg.get("distance_metric")
    if distance_metric not in {"euclidean", "manhattan"}:
        raise ValidationError("distance_metric must be 'euclidean' or 'manhattan'.")
    include_sqrt = require_bool(knn_cfg, "include_sqrt")
    selection_algorithm = knn_cfg.get("selection_algorithm")
    if selection_algorithm not in {"none", "full_sort"}:
        raise ValidationError("selection_algorithm must be 'none' or 'full_sort'.")

    if distance_metric == "euclidean":
        flops_per_distance = 3 * num_features + (1 if include_sqrt else 0)
    else:
        flops_per_distance = 3 * num_features

    flops_distance = batch_size * num_train * flops_per_distance
    if selection_algorithm == "none":
        flops_selection = 0
    else:
        flops_selection = batch_size * num_train * math.ceil(math.log2(num_train))

    param_count = num_train * num_features
    activation_elements = batch_size * num_features + batch_size * num_train
    return {
        "model_type": "knn",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops_distance + flops_selection,
        "extra": {
            "k": k,
            "flops_distance_only": flops_distance,
            "flops_selection": flops_selection,
        },
    }
