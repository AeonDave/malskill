# Capacity and throughput estimates

Use this workflow to identify a resource limit or reject a configuration before benchmarking. Record assumptions beside every estimate; a microbenchmark-derived rate is not a guaranteed hardware ceiling.

## Establish the accounting boundary

- Separate cold loading, prompt prefill, decode, speculative drafting/verification, and request scheduling.
- Record model revision, actual packed weight layout, cache/state formats, device placement, batch size, prompt/output lengths, and cache reuse.
- Use bytes consistently: GB = `10^9` bytes, GiB = `2^30` bytes. FLOPs count operations; FLOP/s is a rate. Count a multiply-add as two operations.
- Choose the memory boundary being modeled: device DRAM, cache, host-device link, or inter-device link. Do not combine bytes from one boundary with bandwidth from another.
- Count reads **and** writes. For a copy of `S` bytes, effective traffic is normally `2*S`; a reported payload-copy rate may instead use `S/time`. Record which convention the measurement uses. [CUDA bandwidth accounting](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#effective-bandwidth-calculation)
- Use representative matrix shapes, precision, kernels, and sustained conditions. A larger GEMM running slower does not by itself establish thermal throttling; check clocks, power, and the selected implementation.

For a phase with traffic `B`, work `F`, bandwidth `BW`, and compute rate `P`:

```text
t_memory = B / BW
t_compute = F / P
t_resource = max(t_memory, t_compute)
```

With required traffic/work and true resource ceilings, this is a latency lower bound, before dependencies and overheads. With measured sustained rates and approximate traffic, it is a scenario estimate. Do not insert a fixed utilization percentage or call the result achievable throughput. Account separately for communication and sequential phases. [Roofline accounting](https://docs.nersc.gov/tools/performance/roofline/)

## Count decode traffic

Start from the execution path, not total parameter count:

- Include evaluated dense projections, router/shared experts, selected experts, output projection, KV reads/writes, recurrent-state updates, and intermediate traffic that crosses the selected boundary.
- Inspect runtime packing, scales, zero points, padding, and conversions. Checkpoint bytes help inventory storage; they do not establish runtime residency or bytes transferred per step.
- An input embedding lookup reads selected rows; an output projection may read the full vocabulary matrix. Account for tied storage and actual access separately.
- Weight reuse across batch rows is an assumption to verify. Kernels, tiling, caches, offload, and expert placement determine actual traffic.
- KV/state traffic scales with active sequences and their actual lengths. Hybrid recurrent state may be independent of context length but still costs storage and updates per sequence.

Within one MoE layer with equal-sized experts, `E` experts, top-`K` routing, and `R` rows, the independent uniform-routing model gives:

```text
expected_unique_experts = E * (1 - (1 - K/E)^R)
expected_expert_bytes = all_expert_bytes * expected_unique_experts / E
```

This is an expectation, not a bound or a measured route union. With exactly `K` distinct experts per row, the union lies between `K` and `min(E, R*K)`. Correlated routes, unequal expert sizes, and per-layer routing require counting actual selected experts and their bytes. Reading every selected expert once is an additional reuse assumption.

Do not label all decode workloads memory bound. Compare both resource times after changing batch size, speculative width, quantization, or placement. [Transformer inference cost analysis](https://arxiv.org/abs/2211.05102)

## Model speculative work and concurrency

Define `k` as proposed draft tokens and `a` as mean **emitted tokens per verification step per sequence**. For the standard algorithm with a correction/bonus token, `a` includes that token; accepted-draft count and draft acceptance rate do not. Use measured emitted work when termination, constrained decoding, or the implementation changes this accounting. [Speculative decoding algorithm](https://arxiv.org/abs/2211.17192), [vLLM metric definitions](https://docs.vllm.ai/en/latest/features/speculative_decoding/acceptance_metrics/)

For `N` equally sized active sequences, let `B_verify_batch` and `B_draft_batch` cover the **whole batch** and all draft steps:

```text
emitted_tokens_per_step = N * a
bytes_per_emitted_token = (B_verify_batch + B_draft_batch) / (N * a)
memory_rate_estimate = BW * N * a / (B_verify_batch + B_draft_batch)
```

The rate is already aggregate tokens/s. Do not multiply by `N` again. Sanity check: one 1 GB weight read per batch, 100 GB/s, `a=1`, and no other work yields 100 tokens/s at `N=1`, 400 at `N=4`.

- Count actual verification rows; the standard `k`-draft algorithm evaluates up to `k+1` target positions. More rows increase compute even when weights are reused.
- Draft weights may be reused across batched sequences; draft KV/state remains per sequence. Do not automatically multiply shared draft weight bytes by concurrency.
- Verification may reuse historical KV across rows. Count actual cache reads, new entries, temporary speculative state, and rollback; neither one read nor `k+1` reads is universal.
- If drafting and verification have different effective rates, estimate their times separately and combine according to the actual schedule. Include sampling, synchronization, and rejected work.
- Use the workload's acceptance distribution. A theoretical acceptance assumption cannot establish a speedup; compare emitted tokens per total elapsed time with speculation disabled.

## Count prefill work

For ordinary dense projections, forward matrix multiplication costs approximately `2*P_linear` FLOPs per processed token, where `P_linear` counts evaluated matrix entries. For MoE, count active experts plus dense/shared/router projections. Exclude unused parameters and embedding lookups; account separately for an output head evaluated only on selected positions. [Forward-pass operation count](https://arxiv.org/abs/2211.05102)

For full causal attention with equal key/value head dimension `d`, `Hq` query heads, `Lattn` identical attention layers, `C` new tokens, and `S` cached prefix tokens:

```text
mean_attended_positions = S + (C + 1) / 2
attention_flops_per_new_token = 4 * Lattn * Hq * d * mean_attended_positions
```

This counts QK and attention-value multiply-adds on allowed causal pairs. For a fresh prompt, `S=0`; `C/2` is only the large-`C` approximation. For heterogeneous layers, sum their terms. With unequal key/value dimensions, replace `4*d` by `2*(d_key+d_value)`.

- Use query heads for attention arithmetic, KV heads for cache storage. GQA shares K/V but still evaluates each query head. [Attention tensor shapes and grouped heads](https://github.com/Dao-AILab/flash-attention)
- Add softmax, normalization, positional transforms, routing, recurrent/linear-attention work, and conversions where material. Tiled kernels may execute extra work on masked/padded positions.
- For chunked or prefix-cached prefill, use the processed chunk and its existing prefix; do not substitute total context into a fresh-prompt formula.
- Model sliding-window or sparse attention from attended pairs. Do not apply a full-attention quadratic term to recurrent layers.
- Estimate compute time using the actual dtype and matrix shapes. FP8/INT8 support or peak ratios are hardware/kernel specific; cache precision does not establish arithmetic precision.
- Check memory and communication too. Small expert token counts, uneven routes, or small prefill chunks can prevent efficient matrix multiplication.

## Budget cache and state per device

For a standard materialized K/V cache, sum over layers assigned to a device:

```text
KV_bytes_per_sequence = sum(context_layer * kv_heads_on_device
                            * (d_key * key_bytes + d_value * value_bytes))
```

Use the backend's actual allocated context and head layout. Add quantization scales, block rounding, allocator overhead, and reserved growth. FP8 reduces element bytes but does not eliminate metadata or establish acceptable quality. [Quantized KV formats](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache.html)

- Tensor parallelism does not always divide KV storage by the device count. For example, vLLM replicates KV heads when there are more tensor-parallel ranks than KV heads. Inspect the configured layout and budget each device. [Pinned head partitioning](https://github.com/vllm-project/vllm/blob/2aa3f0ec1eb29eb3e42d979da2c53fb4cb02b15f/vllm/model_executor/layers/linear.py#L1148)
- For MLA/compressed caches, use the stored representation. For hybrid models, add convolution/recurrent states, their actual dtype, and speculative snapshots per active sequence.
- Sliding-window limits save allocation only if the backend actually evicts/reuses blocks. Shared prefixes save memory only to the extent blocks are shared; copying or divergent continuations changes the budget.
- Reserve weight packing/conversion buffers, activations, graph/workspace allocations, draft-model memory, and runtime headroom. Unified-memory systems also share capacity with host processes.

For equal-length independent streams with no prefix sharing, a planning estimate is:

```text
streams_per_device = floor((usable_budget - fixed_allocations - reserve)
                          / (KV_per_stream + state_per_stream + other_per_stream))
```

The replica's limit is the most constrained device. Treat a negative remaining budget as a configuration failure. Confirm with the runtime's allocation report and the intended workload; logical KV size alone does not prove a configuration fits. Hybrid concurrency is jointly limited by KV, recurrent-state slots, workspace, and scheduler capacity.

## Observe memory without hiding missing data

Record the memory limit's scope, units, sample interval/count, and covered processes/devices. A periodic sampler can miss short peaks; combine runtime high-water counters and the workload's allocation report where available. Zero samples or failed probes mean unavailable evidence, not zero consumption or a proven hard cap.

- Distinguish tensor-allocated, allocator-reserved, process/device-resident, and whole-host memory. PyTorch's [allocator counters](https://docs.pytorch.org/docs/stable/notes/cuda.html#memory-management) cover its managed allocations; allocator tuning does not control every driver, communication, or custom-library allocation.
- Discover the actual cgroup rather than assuming a Docker path. In [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html), `memory.current` includes the cgroup and descendants; `memory.stat`'s `anon` is only one component. Inspect `dmem` device accounting when supported instead of assuming all GPU memory is always absent from cgroups.
- For Linux DRM fdinfo, parse each value's suffix: no suffix means bytes; `KiB` and `MiB` have distinct multipliers. Deduplicate repeated client entries with device identity as well as client identity, following the driver's [DRM statistics contract](https://docs.kernel.org/gpu/drm-usage-stats.html). Residency and requested buffer size are different counters.
- On unified memory, CPU and GPU views can overlap. Show component counters and their overlap assumptions; summing anonymous RAM plus driver residency is not a portable total. Use platform-specific accounting and preserve unsupported/unknown components.
- Budget headroom from measured peaks, fragmentation, co-tenants, and workload growth. A fixed number copied from another device cannot establish safe capacity.

## Bound startup and first-token claims

- Separate cold disk reads, warm page-cache reads, device transfer, allocation/repacking, compilation, autotuning, graph capture, and readiness. Dividing checkpoint bytes by disk speed models only that transfer under its stated assumptions.
- TTFT follows the request's critical path: queueing, tokenization/input preparation, transfer, prefill, and first-token sampling/serialization. Include cache state and prompt shape; one decode-step estimate is insufficient.
- Report estimated limiting resources beside observed startup/TTFT and unexplained gaps. Do not assign universal millisecond or second targets from model size or device class.
