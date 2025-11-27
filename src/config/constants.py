"""Application constants."""

# Data type bit mappings
DTYPE_BITS = {
    "fp32": 32,
    "float32": 32,
    "fp16": 16,
    "float16": 16,
    "bf16": 16,
    "bfloat16": 16,
    "int8": 8,
    "int4": 4,
}

# Hardware kinds
HARDWARE_KINDS = {
    "cpu_node",
    "gpu",
    "tpu",
    "accelerator",
    "jetson",
    "soc",
}

# Model types
MODEL_TYPES = {
    "knn",
    "kmeans",
    "tree",
    "random_forest",
    "gradient_boosted_trees",
    "neural_network",
    "transformer",
    "llm_decoder",
}

# Unit conversions
GB_TO_BYTES = 1e9
TFLOPS_TO_FLOPS = 1e12
TOPS_TO_OPS = 1e12

# Distance metrics
DISTANCE_METRICS = {"euclidean", "manhattan"}

# Selection algorithms
SELECTION_ALGORITHMS = {"none", "full_sort"}

# Model scenario kinds
SCENARIO_KINDS = {
    "single_pass",
    "per_iteration",
    "full_sequence",
    "full_sequence+decode",
    "per_token",
}
