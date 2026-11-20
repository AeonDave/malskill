# Tune the measured bottleneck

Load after identifying whether startup, prefill, decode, scheduling, or memory limits the security workload. Keep the deployed model, tokenizer, chat template, sampling policy, and quality fixtures fixed unless the experiment explicitly changes one.

Use the installed engine's help, startup logs, and matching release documentation. A flag accepted by the CLI does not prove the requested kernel, dtype, or graph path ran. Record fallbacks and effective settings.

## Choose a lever

| Observed symptom | Candidate change | Required correctness and cost check |
| --- | --- | --- |
| Repeated startup spends time compiling | Persist compatible compile/autotune artifacts | Cold versus warm startup, invalidation after a version/config change, host RAM and disk cost |
| Weight loading stalls on storage | Compare supported mmap, prefetch, or eager loaders | Same checkpoint tensors; startup time, page faults, peak host RAM |
| Device trace has gaps between short decode kernels | Graph capture or supported device sampling | Eager parity, supported shapes, capture cost, retained memory, steady-state latency |
| Target decode dominates at low concurrency | Compatible speculative decoding | Target-only baseline, sampler correctness, accepted tokens per total draft/verify cost |
| Repeated prompts reprocess an identical prefix | Prefix caching within the permitted trust scope | Actual cache-hit counters, cold/warm TTFT, identity isolation and eviction behavior |
| Long prefills stall active generations | Chunked prefill and scheduler token budget | Mixed short/long traffic, tail TTFT and inter-token latency, aggregate throughput |
| Weights or KV traffic dominates | Supported weight or cache quantization | Effective kernel/dtype, quality loss, prefill/decode speed and peak memory separately |
| One kernel dominates after configuration tuning | Supported backend switch, then a scoped kernel change | Operator parity across served shapes, model-level regression, end-to-end benefit |

## Startup and graphs

Persist only identified caches with compatible engine/compiler builds, model/configuration, and hardware. Do not assume copying every cache directory preserves valid binaries or gives a cache hit. Reduce compile parallelism only after measuring host-memory pressure; compilation can become slower.

For slow network-file loading, eager loading can trade random I/O for an upfront CPU-memory copy. It is not a universal replacement for mmap on local storage; check loader behavior and RAM in the installed [vLLM configuration](https://docs.vllm.ai/en/stable/api/vllm/config/).

Graph capture reduces repeated launch overhead; it does not remove arithmetic, memory traffic, or scheduler work. Compare eager and supported graph modes using the actual batch/context distribution.

- Warm representative shapes before timing; record compilation, capture, padding, and graph misses separately.
- Check graph/eager outputs, not just successful capture. Include batch-size transitions, speculative verify lengths, and supported cancellation/reuse paths.
- Measure memory after repeated shape changes: capture pools can retain allocations. More captured shapes may cost more memory than they save in latency.
- Keep capture mode backend-specific. A CUDA, HIP, or XPU path working elsewhere does not establish support for this engine/model combination.

[PyTorch CUDA semantics](https://docs.pytorch.org/docs/stable/notes/cuda.html#cuda-graphs) require stable replay addresses and prohibit dynamic shapes inside an individual captured graph; engines may bucket shapes or select among graphs. A generic resource-exhaustion error does not identify graph size as its cause.

## Speculation: preserve the requested sampler

Begin with the same deployed target running without speculation. A quantized target's baseline is that quantized target, not its full-precision ancestor. Confirm model/head compatibility, tokenizer/token-ID mapping, context limits, cache rollback, and support for the requested sampling mode.

For classic speculative sampling, let `p` be the effective target distribution and `q` the actual proposal distribution at a prefix. Accept a proposal `x` with `min(1, p(x)/q(x))`; on rejection sample the normalized positive part of `p - q`. The proposal, acceptance, and correction distributions must agree. See the [speculative sampling algorithm](https://arxiv.org/html/2211.17192v2).

Different exact algorithms can use different acceptance rules. Audit the selected runtime's method rather than replacing it with this formula blindly.

- Pruning a draft vocabulary is not automatically output-preserving because the target sees the full vocabulary. A supported reduced-vocabulary method must map tokens correctly and account for the actual proposal and correction distribution; otherwise do not apply the pruning.
- Greedy verification accepts only target-compatible choices. Greedy parity does not demonstrate correctness at nonzero temperature.
- Distribution equivalence does not promise identical text for the same seed: random draws and floating-point batch/kernel behavior can differ. [vLLM documents these separate guarantees](https://docs.vllm.ai/en/latest/features/speculative_decoding/).
- Keep temperature, top-k/top-p, penalties, grammar constraints, stop/EOS handling, and sampler order consistent with the target-only contract. Do not silently fall back to greedy verification for sampled requests.
- Rejection must restore the correct KV/recurrent state and positions before continuing. Test rejected prefixes, EOS inside a draft, all-accepted drafts, and context boundaries.

For a sampler implementation change, test known small `p`/`q` distributions, including unequal support and forced rejection, then run repeated sampled comparisons with a predefined statistical test and sample budget. For configuration changes, inspect the runtime's sampler tests and exercise the selected mode with task fixtures. Neither a few matching strings nor similar average quality proves distribution equality.

Sweep draft length against concurrency, context, and prompt type. Measure drafting, verification, correction, synchronization, accepted tokens per step, and end-to-end latency. Include draft weights/cache in memory cost and keep a no-draft candidate; higher acceptance can still lose overall.

Verification needs the correct causal mask and state semantics for several proposed positions. Benchmark supported multi-query kernels; do not prescribe one decode call per row or force a prefill kernel by name. GPU sampling is useful when host synchronization dominates, but must preserve sampler behavior. Gumbel-max sampling is not a replacement for a top-k operator.

[SGLang's speculative-decoding guide](https://docs.sglang.ai/advanced_features/speculative_decoding.html) describes method-specific sampling and compatibility. Check those restrictions for the pinned release, including reduced-vocabulary heads, graph modes, and recurrent models.

## Prefix caching and chunked scheduling

Cache reuse requires the same effective prefix computation: token IDs and positions, model/adapter identity, multimodal inputs, and relevant runtime state. Equal visible text alone is insufficient. Preserve the tokenizer/template and inspect actual prompt tokens when an expected hit is absent.

1. Compare a cold request with a repeated exact prefix, then a request that diverges after the shared prefix. Account for block granularity and eviction.
2. Inspect the engine's hit/reused-token metric and processed-prefill tokens. Do not infer a hit solely from faster TTFT or assume every API exposes `cached_tokens`.
3. Change an adapter, image, or cache namespace and verify incompatible state is not reused. Include concurrent requests and cache pressure.
4. Keep tenant or engagement boundaries explicit. Use runtime-supported isolation with a trust-group identifier assigned by trusted ingress; do not let untrusted callers choose another tenant's namespace. If unavailable, isolate the workers/caches.

The [vLLM cache design](https://docs.vllm.ai/en/latest/design/prefix_caching/) includes adapter/multimodal hashes and optional cache salts. Prefix reuse can expose timing information across trust boundaries. Follow the installed runtime's isolation mechanism rather than treating a shared cache as access control.

[Automatic prefix caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) avoids shared-prefix prefill computation; it does not skip generation of new answer tokens. Hybrid recurrent models may require additional checkpoints and different reuse boundaries. Verify effective behavior instead of assuming enabled/disabled defaults.

For chunked prefill, vary the scheduler's token budget while holding maximum context and traffic fixed. Smaller chunks can reduce decode stalls but add scheduling overhead or delay completion of long prefills; larger chunks can improve prompt processing while hurting inter-token latency.

Test both isolated long prompts and a mixed arrival stream with ongoing generation. Report tail latency, throughput, queue growth, and preemption/recomputation. A faster isolated prefill is insufficient. [vLLM's tuning guide](https://docs.vllm.ai/en/latest/configuration/optimization/) describes its decode-prioritized policy; do not assume other engines implement the same scheduler.

## Quantization and hardware portability

Treat weight, activation, attention-KV, and recurrent-state precision as separate changes. Lower storage precision does not establish native low-precision compute or faster execution. Record the selected quantization scheme, scales/group size, accumulation type, kernel/backend, and any dequantization or fallback.

| Change | Qualify before keeping it |
| --- | --- |
| Weight-only quantization | Supported device/kernel and tensor shapes; dequantization cost; small-batch decode versus larger-batch prefill |
| Activation/prefill quantization | Calibration/scales, logits or task-quality drift, and later generation using the resulting KV/state |
| KV quantization | Attention-backend support, long-context quality, prefill peak memory versus resident decode cache, quantize/dequantize cost |
| Recurrent-state dtype | Long-sequence state accumulation, chunk/decode equivalence, speculative rollback and prefix-checkpoint behavior |

Use [vLLM's quantization support matrix](https://docs.vllm.ai/en/latest/features/quantization/) as a version-specific eligibility check, not a performance ranking. Ampere lacking native FP8 tensor arithmetic does not imply every FP8 storage path is unsupported or every INT4 path wins.

Lossy prefill changes the state consumed by decode. An unchanged or bit-exact decode kernel does not make the resulting end-to-end generation lossless. Evaluate the entire changed path with the same quality fixtures, including long-context extraction and structured output needed by the security task.

Keep these engine checks conditional rather than transferring recipes between backends:

- **llama.cpp/GGML:** inspect the selected backend's K/V types, flash-attention path, offload placement, and draft settings. Main and draft cache configuration are distinct in the [server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md); accepted flags alone do not prove a fast fused path.
- **MLX-LM:** verify model/cache support and the actual generation path. Its [long-prompt guidance](https://github.com/ml-explore/mlx-lm#long-prompts-and-generations) distinguishes prompt caching, prefill step size, and rotating caches; shrinking a rotating cache can discard usable context and change quality.
- **ExLlama/TabbyAPI:** pin the ExLlama generation and backend build, quantization format, and graph behavior. A [maintainer's ROCm graph report](https://github.com/turboderp-org/exllamav3/issues/543) supports investigating retained graph memory on that stack; it does not establish a permanent rule to disable every HIP graph.

## Kernel changes after configuration tuning

Profile the representative served shapes before switching attention/GEMM libraries or altering split-K, tiling, padding, fusion, or work-group sizes. Graph capture does not make fusion useless: it can still remove memory traffic or intermediates. Keep changes only when the full request path benefits.

Compare against a trusted operator/reference with declared absolute/relative tolerances, finite-value checks, masks, and precision. Cover boundary row counts, tails, strides, batches, long contexts, quantization extremes, and concurrency supported by the kernel.

Then check eager versus graph execution, layer/model outputs, and security-task fixtures. Bit-identical weights, agreement on two shapes, or a small mean KL value is not a proof of complete losslessness. Scope bit-exact claims to the exact tested path and inputs.

For a backend crash or silent corruption, retain the minimal reproducer, engine/compiler/driver versions, effective kernel, and device logs. Verify any fence, cache-policy, top-k, or graph workaround against that implementation; do not transplant an unversioned device-specific fix.
