---
name: inference-optimization
description: "Benchmark and tune LLM serving latency, throughput, memory, and startup under a fixed workload and quality contract. Use for model-server bottlenecks, speculative decoding, prefill/decode scheduling, KV capacity, and qualification of a tuned deployment."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Inference Optimization

Optimize a model server supporting the active security task: local analysis, agent backends, or repeatable red-team evaluation. Preserve the required model behavior and evidence handling while improving the measured serving path.

## Define the experiment

Record the objective and constraints before changing the server:

- Workload: prompt/output length distribution, concurrency or arrival rate, context budget, shared prefixes, reasoning, tools, and modalities actually used.
- Targets: relevant latency percentiles, aggregate throughput or goodput, startup, and per-device/host memory limits.
- Quality: unchanged execution semantics or an explicitly permitted quality trade; task-specific checks and tolerances.
- Identity: model/quantization/tokenizer/template revisions, engine and kernel versions, launch settings, hardware topology, drivers, and cache state.
- Ownership: the server/process/container being tested, other workloads to preserve, and how to restore the baseline.

Inspect the existing experiment log and current runtime help. A familiar flag name or quantization format does not establish support for this engine, architecture, and device combination.

## Measure, explain, change

For a calculation or review only, use the supplied evidence and assumptions, show the arithmetic, and label unmeasured limits. Do not start a server or require a live benchmark to answer a hypothetical capacity question. Apply the experimental workflow below when the task calls for actual serving measurements or tuning.

1. Establish a valid baseline using [measurement](references/measurement.md). Keep raw request records and errors; missing measurements remain unknown.
2. Profile the actual workload and use [capacity](references/capacity.md) to estimate the limiting traffic, compute, or state. Distinguish an estimate under assumptions from a proven upper bound.
3. Choose the cheapest intervention addressing that bottleneck using [tuning](references/tuning.md). Change one causal factor at a time where possible; name coupled changes when they cannot be separated.
4. Compare candidate and baseline in repeated interleaved trials. Keep workload and environment comparable, and assess required quality, memory, and latency constraints alongside the target metric.
5. Record accepted, rejected, invalid, and inconclusive trials with unique run IDs, configuration hashes, raw evidence, and the reason. Preserve the working baseline until a candidate is qualified.
6. Recreate the selected configuration from pinned artifacts, or rebuild modified components from pinned sources, and apply [qualification](references/qualification.md) before recommending deployment. Publish or deploy only within the user's requested scope.

Choose repetition counts and regression tolerances from measured variation and the task's service objectives. A fixed sample count, universal noise percentage, or a few failed levers is not an acceptance or stopping rule. Stop when remaining work exceeds the agreed scope/budget or repeated measurements no longer distinguish feasible candidates; report the unresolved bottleneck and next useful experiment.

## Control the measurement environment

- Serialize competing benchmark jobs on the same resources; test that the lock works and fail closed if it cannot be acquired. Intentional concurrency belongs inside the workload.
- Record clock, thermal, power, memory pressure, and competing-load changes. Keep relevant power settings stable and restore settings changed for the experiment.
- Scope monitoring and shutdown to the owned process group/container. A failed memory probe cannot establish compliance with a cap; stop accepting work and invalidate the trial when required monitoring is unavailable.
- When stopping or restarting the owned server, stop admissions, cancel/drain requests within a bounded timeout, then stop it. If emergency termination is needed, record it and reject the performance trial. Preserve the final server state requested by the user; do not kill unrelated jobs to manufacture an idle machine.
- Keep launch credentials outside the evidence bundle. Verify where prompts are executed and stored when the task requires local-only processing.

## Load only the needed depth

| Reference | Load when |
|---|---|
| [measurement.md](references/measurement.md) | Building or auditing a benchmark, comparing results, or diagnosing suspicious speedups. |
| [capacity.md](references/capacity.md) | Estimating decode/prefill limits, concurrency, KV/state capacity, or startup costs. |
| [tuning.md](references/tuning.md) | Selecting or validating scheduler, cache, speculation, graph, precision, or kernel changes. |
| [qualification.md](references/qualification.md) | Checking long-context/concurrent stability, reproducing the chosen build, or handing off a deployment recipe. |

Use [transformers](../transformers/SKILL.md) for HF loading/generation, [ollama](../ollama/SKILL.md) for its local runtime, [pytorch](../pytorch/SKILL.md) for tensor inspection, and [litellm](../litellm/SKILL.md) for gateway behavior. Use [model-scanning](../model-scanning/SKILL.md) for untrusted artifacts and [promptfoo](../promptfoo/SKILL.md) for application/security regression. Optimizing authored weights is a separate task in [weight-space-programming](../weight-space-programming/SKILL.md).

## Completion evidence

For an estimate or review, deliver assumptions, calculations, evidence gaps, and limits of the conclusion. For measured tuning, deliver baseline/candidate metrics with formulas, units, workload, sample counts, variation, quality results, and memory scope; include the pinned launch, raw records, rejected experiments, and final server state. Name untested contexts/devices and any lossy change. A successful arithmetic fixture or mock stream test validates that component, not actual model speed or hardware compatibility.

Workflow adapted from the [Sybil Solutions inference-optimisation skill](https://github.com/sybil-solutions/inference-optimisation-skill/tree/fda968e7fc1996aa23c67139c755fe541c9d4be0) with independently checked measurement and capacity contracts. Its scripts and hardware-specific speedup claims are not bundled.
