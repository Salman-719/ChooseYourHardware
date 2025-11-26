"""K-Nearest Neighbors model analysis."""

from __future__ import annotations

import math
from typing import Any

from ....config import DISTANCE_METRICS, SELECTION_ALGORITHMS
from ....exceptions import ModelValidationError
from ....utils import require_bool, require_dict, require_int


def analyze_knn(
    config: dict[str, Any],
    dtype_bits: int,
    dtype_bytes: int,
    batch_size: int
) -> dict[str, Any]:
    """Analyze K-Nearest Neighbors model computational requirements.

    Args:
        config: Model configuration dictionary
        dtype_bits: Data type bit width (8, 16, or 32)
        dtype_bytes: Data type size in bytes
        batch_size: Inference batch size

    Returns:
        Dictionary containing analysis results with keys:
        - model_type: "knn"
        - dtype_bits: Data type bit width
        - param_count: Number of parameters (training samples × features)
        - param_memory_bytes: Memory required for parameters
        - activation_memory_bytes: Memory required for activations
        - flops_per_inference: Total FLOPs per inference
        - extra: Additional details (k, distance/selection FLOPs)

    Raises:
        ModelValidationError: If configuration is invalid
    """
    knn_cfg = require_dict(config.get("knn_config"), "knn_config")

    # Extract and validate parameters
    num_train = require_int(knn_cfg, "num_train_samples", positive=True)
    num_features = require_int(knn_cfg, "num_features", positive=True)
    k = require_int(knn_cfg, "k", positive=True)

    distance_metric = knn_cfg.get("distance_metric")
    if distance_metric not in DISTANCE_METRICS:
        raise ModelValidationError(
            f"distance_metric must be one of {DISTANCE_METRICS}",
            field="distance_metric",
            value=distance_metric
        )

    include_sqrt = require_bool(knn_cfg, "include_sqrt")

    selection_algorithm = knn_cfg.get("selection_algorithm")
    if selection_algorithm not in SELECTION_ALGORITHMS:
        raise ModelValidationError(
            f"selection_algorithm must be one of {SELECTION_ALGORITHMS}",
            field="selection_algorithm",
            value=selection_algorithm
        )

    # Calculate FLOPs for distance computation
    if distance_metric == "euclidean":
        # Squared differences + sum + optional sqrt
        flops_per_distance = 3 * num_features + (1 if include_sqrt else 0)
    else:  # manhattan
        # Absolute differences + sum
        flops_per_distance = 3 * num_features

    flops_distance = batch_size * num_train * flops_per_distance

    # Calculate FLOPs for k-nearest selection
    if selection_algorithm == "none":
        flops_selection = 0
    else:  # full_sort
        # O(n log n) comparison-based sort
        flops_selection = batch_size * num_train * math.ceil(math.log2(num_train))

    # Calculate memory requirements
    param_count = num_train * num_features  # Stored training data
    activation_elements = batch_size * num_features + batch_size * num_train  # Query vectors + distance matrix

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
