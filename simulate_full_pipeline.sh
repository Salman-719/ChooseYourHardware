#!/usr/bin/env bash
# Simulate end-to-end: hardware analysis, model analysis, then matcher latency.
# No external services are needed; uses local analyzers and matcher.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${PYTHONPATH:-${SCRIPT_DIR}/src}"

HW_JSON=$(cat <<'EOF'
{
  "hardware_list": [
    {
      "hardware_id": "gpu1",
      "kind": "gpu",
      "vendor": "NVIDIA",
      "model_name": "A100 80GB",
      "spec": {
        "vram_capacity_gb": 80,
        "vram_bandwidth_gbps": 2039,
        "peak_fp32_tflops": 19.5,
        "peak_fp16_tflops": 78.0,
        "peak_bf16_tflops": 78.0,
        "peak_int8_tops": 624,
        "pcie_bandwidth_gbps": 64,
        "dram_latency_ns": 300,
        "cache_latency_ns": 20
      }
    }
  ]
}
EOF
)
export HW_JSON

MODEL_JSON=$(cat <<'EOF'
{
  "model_type": "transformer",
  "precision": "fp16",
  "inference_config": {"batch_size": 4, "sequence_length": 512},
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
EOF
)
export MODEL_JSON

python - <<'PY'
import json
import os
from analyzers.hardware.core import analyze_hardware_spec
from analyzers.model.core import analyze_model
from matchers.core import calculate_inference_metrics

hw = json.loads(os.environ["HW_JSON"])
model_raw = os.environ["MODEL_JSON"]

hw_out = analyze_hardware_spec(hw)["hardware_analysis"]
model_out = json.loads(analyze_model(model_raw))

# Use the first hardware entry
hw_norm = hw_out[0]["normalized"]
latency, bottleneck = calculate_inference_metrics(model_out, hw_norm)

print("=== Hardware (normalized) ===")
print(json.dumps(hw_out, indent=2))
print("\n=== Model Analysis ===")
print(json.dumps(model_out, indent=2))
print("\n=== Matcher Result ===")
print(json.dumps({"latency_s": latency, "bottleneck": bottleneck}, indent=2))
PY
