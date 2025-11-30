

- **Schema-first ingestion:** Rely on the validated schema in `metadata_extractor/services/hardware_models.py` to reject malformed records early. Each kind (gpu/tpu/accelerator/etc.) enforces required fields, keeping downstream features consistent.

- **Unit normalization:** Standardize all numeric fields before storage: capacities in GB, bandwidth in Gbps, power in watts, latencies in ns (or s). The crawler prompt should emit these canonical units, and any new extractor should convert page values into them to avoid mixed units.
  - Conversions are centralized (`utils/converters.py`): `gb_to_bytes`, `tflops_to_flops`, `tops_to_ops`, and `normalize_latency_seconds` (accepts `*_ns` or `*_s` and returns seconds). Keep features in raw bytes/FLOPs for math; render human units only at the UI layer.

- **Latencies with safe defaults:** The hardware store injects defaults when both `dram_latency_ns/_s` and `cache_latency_ns/_s` are missing (`dram_latency_ns=200.0`, `cache_latency_ns=10.0`). Keep this as a safety net so latency-sensitive features aren’t undefined; real page values should override the defaults.

- **Power keying:** Normalize all wattage signals into `power_consumption_w` (the crawler already remaps tdp/board power variants). Avoid parallel power keys so models learn from a single, consistent field.

- **Feature derivations for matching:** From the normalized spec, derive informative ratios and capacities:
  - Flops-per-watt (using the best available peak: fp32/fp16/bf16/int8).
  - Memory-to-parameter and bandwidth-to-activation ratios (align to the target model’s size/sequence/batch).
  - Interconnect/IO headroom (PCIe/NVLink/host bandwidth vs. model IO demands).
  - Capacity and power headroom (VRAM vs. expected activation/checkpoint footprint; power vs. budget).

- **Missing data strategy:** Keep `null` for fields not present on the page (e.g., price, some latencies). Only apply defaults where necessary (latencies). Downstream, either impute with domain priors or include missingness indicators so the model can learn from the pattern of gaps.

- **Deterministic preprocessing:** Apply the same normalization and feature derivation for train/valid/test to prevent leakage. Version preprocessing configs so model artifacts and evaluations are reproducible.

- **Utilization + dtype handling:** `analyzers.hardware.utils.resolve_utils` validates utilization fractions in `[0,1]` and defaults missing ones to `1.0` (peak). The shared `dtype_map` fixes bit-widths for `fp32/fp16/bf16/int8`, so ensure precision is decided before emitting sustained/peak perf maps.

- **Hardware-derived features (`analyzers/hardware/devices/all_devices.py`):**
  - CPU FP32 fallback: `peak_fp32_tflops = num_sockets * cores_per_socket * base_clock_ghz * 1e9 * (vector_width_bits/32 * fma_units_per_core * 2) / 1e12` when the page omits FP32. RAM BW fallback: `bandwidth_bytes_per_s = memory_channels * memory_speed_mtps * 1e6 * (memory_bus_width_bits/8)`.
  - GPU FP32 fallback: `_gpu_peak_from_sms` uses SM/core counts and base clock (`total_cores * base_clock_ghz * 1e9 * 2 / 1e12`). Host links normalize `pcie_bandwidth_gbps`/`nvlink_bandwidth_gbps` into bytes/sec.
  - Accelerators normalize `host_bandwidth_gbps`, memory GBps, and latencies (`normalize_latency_seconds`) so all features are in consistent SI units. Jetson/SOC merges CPU+GPU dtype support, sums peak FLOPs/OPS, and mirrors shared RAM as both `ram` and `vram` to keep matcher logic simple.

- **Model-derived workload features (`src/analyzers/model`):**
  - KNN: Euclidean distance FLOPs per pair `= 3 * num_features + (1 if include_sqrt else 0)` (Manhattan drops the sqrt); selection adds `batch_size * num_train * ceil(log2(num_train))` when sorting. Params `= num_train * num_features`; activations `= batch_size * (num_features + num_train)`.
  - KMeans: Same distance kernel as KNN; assignment adds `num_points * (num_clusters - 1)` and M-step `num_features * (num_points + num_clusters)`; total FLOPs `= (flops_dist + flops_assign + flops_m_step) * num_iterations`.
  - Trees/ensembles: FLOPs `= batch_size * average_path_length` (scaled by `num_trees` for ensembles); params `= num_internal + num_leaves * output_dim`.
  - Layer-summary NNs: Per-layer param inference must match shapes; activation bytes `= elems_out * dtype_bytes`, peak tracked explicitly, and `avg_flops_per_byte` is emitted to capture intensity.
  - Transformers: Per layer params `= qkv + out_proj + ffn (+ layernorm)`, with attention FLOPs `2 * batch * num_heads * seq_len * seq_len * d_head`, softmax `batch * num_heads * seq_len * (3 * seq_len - 1)`, FFN dense blocks, and residual adds. Activation per layer `= batch * seq_len * hidden_size * dtype_bytes`.
  - LLM decoders: Adds causal mask cost `batch * num_heads * (seq_len * (seq_len - 1) / 2)`, per-token decode FLOPs, and KV cache bytes `= 2 * num_layers * batch_size * seq_length * hidden_size * dtype_bytes`; activation memory is `max(peak, kv_cache)` when caching.

- **Roofline-ready matching features (`matchers/core.py`):** Scenario FLOPs are aggregated (`total_flops`, `flops_prefill + decode_tokens * flops_per_token_decode`, or iteration sums). Stream bytes `= param_memory_bytes + activation_memory_bytes` and working set adds `kv_cache_bytes`; feasibility gates on capacity per memory model. Latency is `max(flops/base_perf, stream_bytes/bandwidth) + latency_overhead`, where `latency_overhead` picks cache vs. DRAM latency depending on `l3_cache_bytes` coverage.
