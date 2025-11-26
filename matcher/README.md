# Matcher

Bandwidth-aware matcher that consumes:
- `model`: full output of `model_analyzer.analyze_model`
- `hardware_analysis`: list/object from `hardware_analyzer.analyze_hardware_spec`
- `requirements`: worst-case scenario and constraints

## Input schema
```json
{
  "model": { ... },                 // analyzer output
  "hardware_analysis": [ ... ],     // analyzer output list
  "requirements": {
    "worst_case": {
      "batch_size": 1,
      "sequence_length": 128,
      "qps": 5.0,
      "latency_seconds": 0.1
    },
    "constraints": {
      "max_hourly_cost_usd": 5.0,
      "allowed_regions": ["us-east-1"],
      "disallow_kinds": ["cluster"]
    }
  }
}
```

## Behavior
- Validates that `model.inference_scenario` matches `requirements.worst_case` (batch_size and sequence_length when applicable).
- Dtype mapping: 32→fp32; 16→fp16→bf16→fp32; 8→int8→fp16→fp32.
- Effective throughput = min(sustained compute, bandwidth * model intensity), using VRAM BW for separate memory models, otherwise RAM BW.
- Memory fit: uses VRAM for separate, RAM for cpu_only/shared.
- SLA: passes only if memory fits and both latency and QPS bounds (based on effective throughput) meet worst_case.
- Constraints: filters by cost, region, and disallowed kinds.
- Output candidates include latency/QPS bounds, cost, region, and complexity_score, sorted by latency.
