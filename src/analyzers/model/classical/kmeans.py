"""Exact computations for k-means models."""

from __future__ import annotations

from typing import Any, Dict

from utils import require_bool, require_dict, require_int

ValidationError = ValueError


def analyze_kmeans(config: Dict[str, Any], dtype_bits: int, dtype_bytes: int, batch_size: int) -> Dict[str, Any]:
    km_cfg = require_dict(config.get("kmeans_config"), "kmeans_config")
    num_points = require_int(km_cfg, "num_points", positive=True)
    num_features = require_int(km_cfg, "num_features", positive=True)
    num_clusters = require_int(km_cfg, "num_clusters", positive=True)
    cluster_sizes = km_cfg.get("cluster_sizes")
    if not (isinstance(cluster_sizes, list) and len(cluster_sizes) == num_clusters):
        raise ValidationError("cluster_sizes must be a list with length num_clusters.")
    for idx, size in enumerate(cluster_sizes):
        if not isinstance(size, int) or size <= 0:
            raise ValidationError(f"cluster_sizes[{idx}] must be a positive integer.")
    if sum(cluster_sizes) != num_points:
        raise ValidationError("Sum of cluster_sizes must equal num_points.")
    distance_metric = km_cfg.get("distance_metric")
    if distance_metric not in {"euclidean", "manhattan"}:
        raise ValidationError("distance_metric must be 'euclidean' or 'manhattan'.")
    include_sqrt = require_bool(km_cfg, "include_sqrt")

    if distance_metric == "euclidean":
        flops_per_distance = 3 * num_features + (1 if include_sqrt else 0)
    else:
        flops_per_distance = 3 * num_features

    flops_distances = num_points * num_clusters * flops_per_distance
    flops_assignment = num_points * (num_clusters - 1)
    flops_m_step = num_features * (num_points + num_clusters)
    flops_iteration = flops_distances + flops_assignment + flops_m_step

    param_count = num_clusters * num_features
    activation_elements = num_points * num_features + num_points * num_clusters
    return {
        "model_type": "kmeans",
        "dtype_bits": dtype_bits,
        "param_count": param_count,
        "param_memory_bytes": param_count * dtype_bytes,
        "activation_memory_bytes": activation_elements * dtype_bytes,
        "flops_per_inference": flops_iteration,
        "total_flops": flops_iteration,
        "total_stream_bytes": (num_points * num_features * dtype_bytes) + (param_count * dtype_bytes),
        "total_jumps": 0,
        "extra": {
            "flops_per_iteration": flops_iteration,
        },
    }
