# Qualify the selected configuration

Load when accepting long-context/capacity claims, rebuilding the winner, or handing off a serving recipe. Tailor gates to the advertised capability and security workflow; do not require reasoning, tools, or vision from a model that does not support them.

## Verify the behavior the workload needs

| Capability | Evidence to retain |
|---|---|
| Load/readiness | Expected model identity and a successful representative request after launch |
| Chat/code/structured output | Task oracle, schema/parser result, stop reason, output length, and regression comparison |
| Reasoning | Correct answer and required separation/visibility of reasoning and answer fields |
| Tools | Valid call, result ingestion, and a final answer using an unpredictable value from that result |
| Long context | Verified token length, retained task information, and correct answers at varied positions/lengths |
| Concurrent capacity | Actual overlapping requests at the claimed context/output budget, peak memory, errors, and latency tails |
| Vision/audio | Correct input path and task outcome using the intended modality and its memory/token budget |

Make deterministic retrieval fixtures with randomized identifiers/values and an answer oracle outside the prompt. Do not include the expected answer in the query. Use multiple positions, distractors, absent-key cases, and the task's real code/log/document format. Freeze normalization before exact-match scoring; substring containment can accept contradictory or verbose incorrect answers.

Test moderate and near-limit context with space reserved for output and template overhead. Confirm the server processed that length without truncation or hidden cache reuse. Needle retrieval checks a narrow retrieval behavior; it does not establish general long-context reasoning or preservation of the security task's evidence semantics.

For a capacity claim, run repeated overlapping waves and an appropriate sustained soak at the advertised mix. Include output growth and mixed prefill/decode; idle allocated slots are not concurrent full-context service. Retain failures, preemptions/recomputations, throughput, tail latency, and peak per-device/host memory. Use [capacity](capacity.md) for memory accounting.

## Match the quality claim

- For a purported execution-only change, preserve model, tokenizer, template, sampling and workload. Compare token outputs under the required deterministic setup, then run the task oracle. Differences require diagnosis; floating-point order or nondeterminism can change an argmax without proving intentional quality loss.
- For an exact speculative sampler, use the conditions in [tuning](tuning.md); greedy agreement on a few prompts is not proof of distribution preservation.
- For quantization, pruning, approximate attention, or another permitted lossy change, compare representative and difficult cases against the baseline with declared tolerances. Retain a task-quality floor alongside speed/memory results.
- For attacker/scorer models in red-team evaluation, check that the optimization has not changed the behaviors or scoring criteria being measured. Route application/security checks through [promptfoo](../../promptfoo/SKILL.md) or the existing evaluation harness.

## Recreate the actual winner

1. Record model and tokenizer revisions, quantized-artifact hashes, engine/kernel commits or image digests, dependency lock, build flags, driver/runtime versions, and relevant configuration.
2. Materialize required draft models, vocabularies, templates, and plugins from durable sources with hashes. A developer's local file or a mutable tag is insufficient.
3. For pinned official images or wheels, materialize the exact artifact and verify its identity and configuration. For components compiled or modified as part of the candidate, build in a clean isolated checkout from exact source and dependency pins. Preserve the original working checkout; do not discard its changes to make it clean.
4. Compare the rendered launch, environment, artifacts, and hardware to the candidate. Explain intentional differences, including persistent caches and their cold/warm state.
5. Execute the required functional, context, memory, and performance checks on the recreated deployment. Interleave it with the qualified candidate under the same workload; investigate differences exceeding the established variation or quality tolerance.

Prefer reproducible dependency/build manifests over assuming that matching `pip freeze` output reproduces native libraries, compiler flags, or drivers. Preserve source and artifact availability through retained releases, immutable storage, or reachable protected refs; a hash identifies content but does not guarantee it will remain retrievable.

## Handoff evidence

Provide the exact launch and pins, workload/metric definitions, raw request and memory records, baseline/candidate distributions, quality results, failures, and tested capacity. Keep engine counters, client timings, short smoke gates, and sustained load results distinguishable. Remove secrets and private prompt/log content from any publishable bundle.

State what remains running, which profile/settings changed, what was restored, and how to stop the owned service. Restore the agreed baseline or qualified server as requested. A request to free the accelerator means stopping the owned workload and monitoring loop, then verifying its resources were released; it does not authorize stopping other users' processes.

The [source workflow](https://github.com/sybil-solutions/inference-optimisation-skill/blob/fda968e7fc1996aa23c67139c755fe541c9d4be0/skills/inference-optimisation/references/publishing.md) motivates clean-build comparison and evidence retention. Its fixed gate durations and hardware results are not universal acceptance criteria.
