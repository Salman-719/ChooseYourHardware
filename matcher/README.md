# Matcher

Lightweight matcher that takes a model cost report (output of `model_analyzer`) and a hardware normalization report (output of `hardware_analyzer`), then ranks hardware candidates.

## Usage

```python
from model_analyzer import analyze_model
from hardware_analyzer import core as hw_core
from matcher import match_model_to_hardware

model_report = json.loads(analyze_model(model_json_str))
hardware_report = hw_core.analyze_hardware_spec(hardware_spec_dict)

matches = match_model_to_hardware(
    model_report,
    hardware_report,
    allow_multi_gpu_shard=False,  # set True to allow VRAM sharding across GPUs in a node
    allow_cross_node=False,       # set True to allow clusters as distributed targets
)
```

`matches["candidates"]` is sorted by feasibility and estimated latency (lower first) using sustained throughput.

## Policies implemented

- Dtype mapping with fallback: 32→fp32; 16→fp16→bf16→fp32; 8→int8→fp16→bf16→fp32.
- Memory checks use the correct pool by hardware kind:
  - `cpu_node`: compare against RAM.
  - `gpu`/`accelerator`/`tpu`: prefer VRAM; if it only fits in RAM, mark as offload.
  - `jetson`/`soc`: shared RAM/VRAM pool.
  - `multi_gpu_node`: if sharding allowed, compare to total VRAM; otherwise estimate per-GPU VRAM.
  - `cluster`: only if cross-node parallel is allowed.
- Latency/QPS estimates always use sustained (not peak) throughput.
