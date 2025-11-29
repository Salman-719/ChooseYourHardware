#!/usr/bin/env bash
# Simulate the hardware analyzer on a sample GPU spec.
# Outputs the normalized hardware document the matcher consumes.

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

python - <<'PY'
import json
import os
from analyzers.hardware.core import analyze_hardware_spec

hw = json.loads(os.environ["HW_JSON"])
result = analyze_hardware_spec(hw)
print(json.dumps(result, indent=2))
PY
