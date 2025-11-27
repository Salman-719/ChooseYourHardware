# Mathematical Operations & Input/Output Specifications

## Overview

This document details all mathematical computations performed by ChooseYourHardware and the expected input/output formats for each component.

---

## Table of Contents

1. [Model Analyzers](#model-analyzers)
   - [Neural Networks (CNNs)](#neural-networks-cnns)
   - [Transformers](#transformers)
   - [LLM Decoders](#llm-decoders)
   - [K-Nearest Neighbors (KNN)](#k-nearest-neighbors-knn)
   - [K-Means](#k-means)
   - [Decision Trees](#decision-trees)
2. [Hardware Analyzers](#hardware-analyzers)
3. [Universal Matcher](#universal-matcher)
4. [Metadata Extractor](#metadata-extractor)

---

## Model Analyzers

### Neural Networks (CNNs)

**File**: `src/analyzers/model/neural/layers.py`

#### Mathematical Operations

For each layer type, the analyzer computes:

##### 1. **Convolutional Layers (Conv1D/2D/3D)**

**Parameters**:
```
params = C_out × (C_in / groups) × kernel_size + (C_out if use_bias else 0)
```

**FLOPs per output element**:
```
FLOPs_per_elem = 2 × (C_in / groups) × kernel_size + (1 if use_bias else 0)
```
- Factor of 2 accounts for multiply-accumulate (MAC) operations
- Each MAC = 1 multiply + 1 add = 2 FLOPs

**Total FLOPs**:
```
Total_FLOPs = output_elements × FLOPs_per_elem
where output_elements = batch_size × C_out × H_out × W_out (for Conv2D)
```

##### 2. **Dense/Linear Layers**

**Parameters**:
```
params = in_features × units + (units if use_bias else 0)
```

**FLOPs**:
```
FLOPs = 2 × batch_size × in_features × units + (batch_size × units if use_bias else 0)
```
- 2× for matrix multiplication (MAC operations)
- Additional adds for bias

##### 3. **Batch Normalization**

**Parameters**:
```
params ∈ {C, 2×C, 4×C}
```
- C: scale only
- 2C: scale + shift (γ, β)
- 4C: includes running mean/variance (stored but not trainable)

**FLOPs**:
```
FLOPs = output_elements × 4
```
- Per element: (x - mean) / √(var + ε) × γ + β
- Approximated as 4 operations per element

##### 4. **Activation Functions**

**Parameters**: 0 (no trainable parameters)

**FLOPs**:
```
FLOPs = output_elements
```
- 1 operation per element (ReLU, sigmoid, etc.)

#### Aggregate Metrics

**Total Parameters**:
```
param_count = Σ(params_i) for all layers i
```

**Parameter Memory**:
```
param_memory_bytes = param_count × dtype_bytes
where dtype_bytes = dtype_bits / 8
```

**Activation Memory**:
```
activation_sum_bytes = Σ(output_elements_i × dtype_bytes) for all layers
activation_peak_bytes = max(output_elements_i × dtype_bytes) for all layers
```

**Total FLOPs**:
```
flops_per_inference = Σ(FLOPs_i) for all layers
```

**Arithmetic Intensity** (per layer):
```
flops_per_byte = FLOPs / (param_bytes + activation_bytes)
```

#### Input Format

```json
{
  "usage_constraints": {
    "batch_size": 4
  },
  "model_level": {
    "input_shape": [3, 224, 224],
    "precision": "fp32",
    "total_params": 25557032  // optional, validated against sum
  },
  "layer_summary": [
    {
      "name": "conv1",
      "type": "Conv2d",
      "output_shape": [null, 64, 112, 112],  // null = batch dimension
      "params": 9408,
      "groups": 1,         // optional, default 1
      "use_bias": true     // optional, inferred if not provided
    },
    {
      "name": "bn1",
      "type": "BatchNorm2d",
      "output_shape": [null, 64, 112, 112],
      "params": 128
    }
  ]
}
```

#### Output Format

```json
{
  "model_type": "neural_network",
  "dtype_bits": 32,
  "param_count": 25557032,
  "param_memory_bytes": 102228128,
  "activation_peak_bytes": 50331648,
  "activation_sum_bytes": 201326592,
  "activation_memory_bytes": 50331648,
  "flops_per_inference": 4089184256,
  "extra": {
    "activation_elements_sum": 50331648,
    "activation_peak_elements": 12582912,
    "layers": [
      {
        "name": "conv1",
        "type": "Conv2d",
        "input_shape": [4, 3, 224, 224],
        "output_shape": [4, 64, 112, 112],
        "params": 9408,
        "param_bytes": 37632,
        "flops": 115605504,
        "activation_elements": 3211264,
        "activation_bytes": 12845056,
        "flops_per_byte": 9.0
      }
    ]
  },
  "inference_scenario": {
    "batch_size": 4,
    "sequence_length": null,
    "precision_bits": 32
  }
}
```

---

### Transformers

**File**: `src/analyzers/model/neural/transformers.py`

#### Mathematical Operations

##### Per-Layer Computations

For each transformer encoder layer:

**1. Multi-Head Self-Attention**:
```
# QKV projections (3 linear layers)
FLOPs_QKV = 3 × (2 × BT × d_model × d_model + (BT × d_model if use_bias else 0))
where BT = batch_size × seq_length

# Attention scores: Q @ K^T
FLOPs_scores = 2 × batch_size × num_heads × seq_length × seq_length × d_head
where d_head = d_model / num_heads

# Softmax
FLOPs_softmax = batch_size × num_heads × seq_length × (3 × seq_length - 1)
  # exp + sum + divide per position

# Attention output: Scores @ V
FLOPs_attn_out = 2 × batch_size × num_heads × seq_length × seq_length × d_head

# Output projection
FLOPs_out_proj = 2 × BT × d_model × d_model + (BT × d_model if use_bias else 0)
```

**2. Feed-Forward Network**:
```
# First linear layer
FLOPs_FFN1 = 2 × BT × d_model × d_ffn + (BT × d_ffn if use_bias else 0)

# Activation (GELU/ReLU)
FLOPs_act = BT × d_ffn

# Second linear layer
FLOPs_FFN2 = 2 × BT × d_ffn × d_model + (BT × d_model if use_bias else 0)
```

**3. Layer Normalization** (if enabled):
```
FLOPs_LN = 2 × BT × d_model × 7
  # 2 LayerNorms per layer
  # Each LN: mean, variance, normalize, scale, shift ≈ 7 ops per element
```

**4. Residual Connections**:
```
FLOPs_residual = 2 × BT × d_model
  # Two add operations per layer
```

**Total per layer**:
```
FLOPs_layer = FLOPs_QKV + FLOPs_scores + FLOPs_softmax + FLOPs_attn_out 
            + FLOPs_out_proj + FLOPs_FFN1 + FLOPs_act + FLOPs_FFN2 
            + FLOPs_residual + FLOPs_LN
```

##### Parameters per Layer

```
# QKV projections
params_QKV = 3 × (d_model × d_model + (d_model if use_bias else 0))

# Output projection
params_out = d_model × d_model + (d_model if use_bias else 0)

# FFN
params_FFN = (d_model × d_ffn + (d_ffn if use_bias else 0)) 
           + (d_ffn × d_model + (d_model if use_bias else 0))

# LayerNorm (2 per layer)
params_LN = 4 × d_model if use_layernorm else 0

# Total per layer
params_layer = params_QKV + params_out + params_FFN + params_LN
```

##### Embeddings

**Token Embeddings**:
```
params_embed = vocab_size × d_model
```

**Positional Embeddings** (if included):
```
params_pos = max_seq_length × d_model
```

#### Input Format

```json
{
  "model_type": "transformer",
  "dtype_bits": 32,
  "inference_config": {
    "batch_size": 8,
    "sequence_length": 512
  },
  "transformer_config": {
    "num_layers": 12,
    "hidden_size": 768,
    "ffn_size": 3072,
    "num_heads": 12,
    "max_sequence_length": 512,
    "use_bias": true,
    "use_layernorm": true,
    "vocab_size": 30522,
    "include_embeddings": true,
    "include_positional_embeddings": true
  }
}
```

#### Output Format

```json
{
  "model_type": "transformer",
  "dtype_bits": 32,
  "param_count": 109482240,
  "param_memory_bytes": 437928960,
  "activation_peak_bytes": 12582912,
  "activation_sum_bytes": 150994944,
  "activation_memory_bytes": 12582912,
  "flops_per_inference": 89478346752,
  "extra": {
    "activation_elements_sum": 37748736,
    "activation_peak_elements": 3145728,
    "layers": [...]
  },
  "inference_scenario": {
    "batch_size": 8,
    "sequence_length": 512,
    "precision_bits": 32
  }
}
```

---

### LLM Decoders

**File**: `src/analyzers/model/neural/llm.py`

#### Mathematical Operations

Similar to transformers but with:

**1. Causal Masking**:
```
FLOPs_mask = batch_size × num_heads × (seq_length × (seq_length - 1) / 2)
```
- Triangular mask for autoregressive attention

**2. KV Cache Support**:

During **prefill** (first forward pass):
```
FLOPs_prefill = num_layers × FLOPs_layer
```

During **decode** (per token generation):
```
FLOPs_decode_layer = 3 × (2 × B × d_model × d_model)  # QKV (but KV cached)
                   + 2 × B × seq_length × d_model      # Q @ K^T (K from cache)
                   + B × num_heads × (3 × seq_length - 1)  # softmax
                   + 2 × B × seq_length × d_model      # Attn @ V (V from cache)
                   + (2 × B × d_model × d_model)       # output projection
                   + FFN_flops
                   + LayerNorm_flops
```

**KV Cache Memory**:
```
kv_cache_bytes = 2 × num_layers × batch_size × seq_length × d_model × dtype_bytes
```
- 2× for both K and V
- Stored per layer

#### Input Format

```json
{
  "model_type": "llm_decoder",
  "dtype_bits": 16,
  "inference_config": {
    "batch_size": 1,
    "sequence_length": 2048
  },
  "llm_config": {
    "num_layers": 32,
    "hidden_size": 4096,
    "ffn_size": 11008,
    "num_heads": 32,
    "vocab_size": 32000,
    "max_sequence_length": 2048,
    "use_bias": false,
    "use_layernorm": true,
    "include_embeddings": true,
    "include_positional_embeddings": false,
    "include_kv_cache": true
  }
}
```

#### Output Format

```json
{
  "model_type": "llm_decoder",
  "dtype_bits": 16,
  "param_count": 6738415616,
  "param_memory_bytes": 13476831232,
  "activation_peak_bytes": 16777216,
  "activation_sum_bytes": 536870912,
  "activation_memory_bytes": 16777216,
  "flops_per_inference": 12345678901234,
  "extra": {
    "kv_cache_bytes": 1073741824,
    "flops_per_token_decode": 67108864,
    "layers": [...]
  },
  "inference_scenario": {
    "batch_size": 1,
    "sequence_length": 2048,
    "precision_bits": 16
  }
}
```

---

### K-Nearest Neighbors (KNN)

**File**: `src/analyzers/model/classical/knn.py`

#### Mathematical Operations

**Distance Computation**:

For **Euclidean** distance:
```
per_distance_FLOPs = 3 × num_features + (1 if include_sqrt else 0)
```
- 3× per feature: subtract, square, accumulate
- +1 for square root (if enabled)

For **Manhattan** distance:
```
per_distance_FLOPs = 3 × num_features
```
- 3× per feature: subtract, abs, accumulate

**Total Distance FLOPs**:
```
FLOPs_distance = batch_size × num_train_samples × per_distance_FLOPs
```

**K-Nearest Selection**:

For **full_sort**:
```
FLOPs_selection = batch_size × num_train_samples × ceil(log₂(num_train_samples))
```
- O(n log n) sorting algorithm

For **none** (no selection):
```
FLOPs_selection = 0
```

**Total FLOPs**:
```
Total_FLOPs = FLOPs_distance + FLOPs_selection
```

**Memory**:
```
param_count = num_train_samples × num_features
activation_elements = batch_size × num_features + batch_size × num_train_samples
  # Query vectors + distance matrix
```

#### Input Format

```json
{
  "model_type": "knn",
  "dtype_bits": 32,
  "inference_config": {
    "batch_size": 100
  },
  "knn_config": {
    "num_train_samples": 50000,
    "num_features": 128,
    "k": 5,
    "distance_metric": "euclidean",
    "include_sqrt": true,
    "selection_algorithm": "full_sort"
  }
}
```

#### Output Format

```json
{
  "model_type": "knn",
  "dtype_bits": 32,
  "param_count": 6400000,
  "param_memory_bytes": 25600000,
  "activation_memory_bytes": 20051200,
  "flops_per_inference": 38512800,
  "extra": {
    "k": 5,
    "flops_distance_only": 38400000,
    "flops_selection": 112800
  }
}
```

---

### K-Means

**File**: `src/analyzers/model/classical/kmeans.py`

#### Mathematical Operations

**Distance Computation** (per iteration):
```
FLOPs_distance = batch_size × num_clusters × 3 × num_features
```
- Euclidean distance (no sqrt needed for comparison)

**Cluster Assignment**:
```
FLOPs_assignment = batch_size × num_clusters
```
- Find minimum distance per sample

**Centroid Update** (during training):
```
FLOPs_centroid_update = num_clusters × num_features
```

**Total per iteration**:
```
FLOPs_iteration = FLOPs_distance + FLOPs_assignment + FLOPs_centroid_update
```

**Total (with iterations)**:
```
Total_FLOPs = num_iterations × FLOPs_iteration
```

---

### Decision Trees

**File**: `src/analyzers/model/classical/trees.py`

#### Mathematical Operations

**Single Tree**:
```
FLOPs_tree = batch_size × tree_depth × num_features
```
- Each node: 1 comparison per feature (worst case)

**Random Forest / Gradient Boosted Trees**:
```
Total_FLOPs = num_estimators × FLOPs_tree
```

**Memory**:
```
param_count = num_estimators × num_nodes_per_tree
```

---

## Hardware Analyzers

**File**: `src/analyzers/hardware/devices/all_devices.py`

### GPU Analysis

#### Peak FLOPs Calculation

If `peak_fp32_tflops` not provided, calculated from SM specs:
```
total_cores = num_sms × cores_per_sm
peak_fp32_flops = total_cores × base_clock_ghz × 1e9 × 2.0
peak_fp32_tflops = peak_fp32_flops / 1e12
```
- 2.0 = FMA operations (1 multiply + 1 add per cycle)

#### Sustained FLOPs

For each precision:
```
sustained_flops[dtype] = peak_flops[dtype] × utilization[dtype]
```

Default utilizations:
- FP32: 0.5 (50%)
- FP16: 0.5 (50%)
- BF16: 0.5 (50%)
- INT8: 0.5 (50%)

#### Memory Bandwidth

```
vram_bandwidth_bytes_per_s = vram_bandwidth_gbps × 1e9
```

### CPU Analysis

#### Peak FLOPs Calculation

```
total_cores = num_sockets × cores_per_socket
lanes = vector_width_bits / 32.0
flops_per_cycle_per_core = lanes × fma_units_per_core × 2.0
peak_fp32_flops = total_cores × base_clock_ghz × 1e9 × flops_per_cycle_per_core
```

#### RAM Bandwidth

If not directly provided:
```
bytes_per_transfer = memory_bus_width_bits / 8.0
bandwidth_bytes_per_s = memory_channels × memory_speed_mtps × 1e6 × bytes_per_transfer
ram_bandwidth_gbps = bandwidth_bytes_per_s / 1e9
```

### Input Format

```json
{
  "hardware_list": [
    {
      "hardware_id": "rtx4090",
      "kind": "gpu",
      "vendor": "NVIDIA",
      "model_name": "RTX 4090",
      "spec": {
        "num_sms": 128,
        "cores_per_sm": 128,
        "base_clock_ghz": 2.52,
        "peak_fp32_tflops": 82.6,
        "peak_fp16_tflops": 165.2,
        "peak_int8_tops": 660.6,
        "vram_capacity_gb": 24,
        "vram_bandwidth_gbps": 1008,
        "supports_fp16": true,
        "supports_int8": true,
        "pcie_bandwidth_gbps": 64
      }
    }
  ],
  "defaults": {
    "utilization_fp32": 0.7,
    "utilization_fp16": 0.7,
    "utilization_int8": 0.7
  }
}
```

### Output Format

```json
{
  "hardware_analysis": [
    {
      "hardware_id": "rtx4090",
      "kind": "gpu",
      "vendor": "NVIDIA",
      "model_name": "RTX 4090",
      "normalized": {
        "dtype_support": {
          "fp32": true,
          "fp16": true,
          "bf16": false,
          "int8": true
        },
        "dtype_map": {"fp32": 32, "fp16": 16, "bf16": 16, "int8": 8},
        "utilization_assumptions": {
          "fp32": 0.7,
          "fp16": 0.7,
          "bf16": 0.5,
          "int8": 0.7
        },
        "peak_flops_per_s": {
          "fp32": 82600000000000,
          "fp16": 165200000000000,
          "bf16": null
        },
        "peak_ops_per_s": {
          "int8": 660600000000000
        },
        "sustained_flops_per_s": {
          "fp32": 57820000000000,
          "fp16": 115640000000000,
          "bf16": null
        },
        "sustained_ops_per_s": {
          "int8": 462420000000000
        },
        "memory_capacity_bytes": {
          "ram": null,
          "vram": 25769803776
        },
        "memory_bandwidth_bytes_per_s": {
          "ram": null,
          "vram": 1008000000000
        },
        "memory_model": "separate",
        "host_device_bandwidth_bytes_per_s": 64000000000,
        "cpu_threads": null,
        "num_gpus": 1
      }
    }
  ]
}
```

---

## Universal Matcher

**File**: `src/matchers/core.py`

### Latency Estimation

The matcher identifies the dominant bottleneck among three roofs:

#### 1. Compute Roof

```
t_compute = total_flops / sustained_flops_per_s
```

#### 2. Memory Bandwidth Roof

```
t_bandwidth = total_stream_bytes / memory_bandwidth_bytes_per_s
```
- `total_stream_bytes` typically equals parameter memory

#### 3. Memory Latency Roof

```
latency_per_jump = cache_latency_ns if fits_in_cache else dram_latency_ns
t_latency = total_jumps × latency_per_jump × 1e-9
```

Where:
```
fits_in_cache = param_memory_bytes < l3_cache_bytes
```

**Final Estimate**:
```
estimated_latency = max(t_compute, t_bandwidth, t_latency)
bottleneck = argmax([t_compute, t_bandwidth, t_latency])
```

### Input Format

```python
model = {
    "flops_per_inference": 4089184256,
    "param_memory_bytes": 102228128,
    "total_jumps": 1000000,  # for memory-latency-sensitive models
    "inference_scenario": {
        "precision_bits": 32
    }
}

hardware = {
    "sustained_flops_per_s": {
        "fp32": 57820000000000,
        "fp16": 115640000000000
    },
    "memory_bandwidth_bytes_per_s": {
        "vram": 1008000000000
    },
    "l3_cache_bytes": 134217728,
    "cache_latency_ns": 5.0,
    "dram_latency_ns": 100.0
}
```

### Output

```python
latency, bottleneck = calculate_inference_metrics(model, hardware)
# Returns: (0.000071, "COMPUTE")
# or: (0.000102, "MEMORY_BANDWIDTH")
# or: (0.000050, "MEMORY_LATENCY")
```

---

## Metadata Extractor

**File**: `src/metadata_extractor/service.py`

### LLM-Based Extraction

Uses a two-step process:

#### 1. Update Step

```
Input: current_state, last_question, user_input
LLM: metadata_extractor_updater.txt
Output: updated_state
```

Incorporates user's response into the metadata.

#### 2. Ask Step

```
Input: updated_state, model_fields template
LLM: metadata_extractor_asker.txt
Output: {metadata, follow_up_question, filled}
```

Determines next question to ask.

### Input Format

```json
{
  "model_type": "cnn",
  "user_input": "ResNet-50 for image classification",
  "current_state": {},
  "last_question": null
}
```

### Output Format

```json
{
  "metadata": {
    "usage_constraints": {
      "batch_size": 4
    },
    "model_level": {
      "input_shape": [3, 224, 224],
      "precision": "fp32"
    },
    "layer_summary": [...]
  },
  "next_question": "How many convolutional layers does your model have?",
  "is_complete": false
}
```

---

## Summary Table

| Component | Input | Math Operations | Output |
|-----------|-------|-----------------|--------|
| **CNN Analyzer** | Layer specs | FLOPs = 2×ops per layer | Params, memory, FLOPs |
| **Transformer** | Config | Attention + FFN FLOPs | Params, memory, FLOPs |
| **LLM** | Config | Decoder + KV cache | Params, memory, FLOPs, cache |
| **KNN** | Train size, features | Distance × selections | FLOPs, memory |
| **K-Means** | Clusters, iterations | Distance × iterations | FLOPs, memory |
| **Trees** | Depth, estimators | Comparisons × trees | FLOPs, memory |
| **GPU Analyzer** | SM specs | SM×cores×clock×2 | Peak/sustained FLOPs |
| **CPU Analyzer** | Core specs | Cores×SIMD×FMA×clock | Peak/sustained FLOPs |
| **Matcher** | Model + HW | max(compute, BW, latency) | Latency, bottleneck |

---

## Key Formulas Reference

### FLOPs Calculations
- **MAC (Multiply-Accumulate)**: 2 FLOPs
- **Matrix Multiplication** (M×N @ N×P): `2×M×N×P` FLOPs
- **Convolution**: `2×kernel_size×C_in×output_elements` FLOPs
- **Attention**: `2×B×H×L²×d_head` FLOPs for QK^T and Attn@V

### Memory Calculations
- **Parameters**: `count × dtype_bytes`
- **Activations**: `elements × dtype_bytes`
- **KV Cache**: `2×layers×B×L×d_model×dtype_bytes`

### Hardware Metrics
- **Peak FLOPs**: `cores × clock × ops_per_cycle`
- **Sustained FLOPs**: `peak × utilization`
- **Bandwidth**: `channels × speed × bus_width`

### Latency Estimation
- **Compute-bound**: `FLOPs / FLOPS`
- **Bandwidth-bound**: `bytes / BW`
- **Latency-bound**: `jumps × latency`

---

*This specification is maintained alongside the codebase. For implementation details, refer to the source files listed in each section.*
