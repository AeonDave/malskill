# Measure serving behavior without changing the question

Load when establishing a baseline, auditing a harness, or comparing candidate configurations. Prefer the pinned runtime's maintained benchmark client; inspect its measurement boundaries before treating matching metric names as equivalent.

## Freeze the workload and counters

Record exact prompt IDs or reproducible fixtures, model/tokenizer/chat-template revisions, sampling settings, output budget, reasoning mode, stop conditions, concurrency/arrival schedule, and prefix reuse. Include representative security-task requests; synthetic fixed-length prompts are a separate load test.

- Count input tokens after the actual chat template and any system/tool text. For multimodal input, distinguish text tokens from visual/audio representations and memory.
- Use server token IDs or complete usage counters for output counts. If reconstructing from text, use the pinned tokenizer and state that hidden reasoning, special tokens, or tool output may be omitted. Never sum independently tokenized chunks or count events as tokens.
- Reserve context for generated output: prompt plus template plus output must fit the supported effective window. Detect truncation/rejection; a requested character count is not a verified token length.
- Keep incomplete streams, HTTP errors, cancellations, OOMs, short/looping outputs, and missing accounting visible. Do not average only the surviving fast requests and report a successful run.

Treat a dropped connection and a timeout as potentially ambiguous server execution. Check request/cancellation state when available before retrying; record retries as separate attempts and include their resource/latency cost. Neither error type alone proves that repeating the request is harmless or that the first attempt never ran.

## Name the timing boundaries

Use one monotonic clock for each client's intervals. Keep at least these timestamps per request:

| Timestamp | Event |
|---|---|
| `t_submit` | Client submits the request |
| `t_first` | First token-bearing event, including reasoning when measuring all decoding |
| `t_last` | Last token-bearing event |
| `t_done` | Valid protocol completion, possibly after usage/trailer delivery |

Empty role/metadata events are not a first token. If the user cares about the first visible answer, record that separately from the first reasoning token. For tool-only outputs, document which deltas count as generated output; use a client that supports the endpoint.

| Metric | Definition and boundary |
|---|---|
| TTFT | `t_first - t_submit`; includes the observed queue/transport/preprocessing/prefill path |
| Generation-ended request latency | `t_last - t_submit` |
| Protocol-completed request latency | `t_done - t_submit`; includes the trailer/completion tail |
| Conventional TPOT | `(t_last - t_first) / (output_tokens - 1)` for `output_tokens > 1`; undefined otherwise |
| Stream-gap latency | Gaps between token-bearing events; not necessarily gaps between individual tokens |
| Aggregate output rate | Total successfully completed output tokens divided by the declared whole measurement window |
| Request goodput | Successful requests meeting the declared quality/latency conditions divided by that same window |

Record whether a tool's end time is `t_last` or `t_done` before comparing its TPOT. With bundled speculative outputs, conventional TPOT amortizes across tokens while stream gaps measure chunks. Even the first event may contain several tokens: neither statistic reconstructs their individual emission times. A reciprocal median TPOT is not aggregate server throughput.

Example: submit at `0`, first output at `1.2 s`, last output at `1.5 s`, protocol completion at `1.6 s`, and seven generated tokens. TTFT is `1.2 s`, generation-ended latency `1.5 s`, protocol latency `1.6 s`, and conventional TPOT `0.3 / 6 = 50 ms`. Trailer latency is not decode work. An empty or one-token response cannot produce a meaningful TPOT from that denominator.

[vLLM's benchmark definitions](https://docs.vllm.ai/en/latest/benchmarking/cli) explicitly distinguish TPOT from streamed-output gaps. Check the installed implementation because endpoint/version timing boundaries can differ. For Ollama's native counters, use the [Ollama skill](../../ollama/SKILL.md); those engine durations are not client latency measurements.

## Separate load tests

- **Single request:** establish latency at the intended prompt/output length with no competing requests.
- **Closed-loop concurrency:** keep a declared number of outstanding requests. Record actual overlap; launching threads alone does not prove concurrent service.
- **Open-loop arrivals:** send a declared rate/distribution independent of completions. Sweep load and report queueing, tail latency, errors, and goodput. Record client-side waiting when a concurrency cap throttles arrivals.
- **Mixed traffic:** overlap long prefills with short interactive decodes. Aggregate throughput can improve while the latter's latency becomes unacceptable.

For an isolated batch, measure wall time from first submission to last required completion; do not divide summed tokens by the longest per-request duration or sum independent per-request rates. In fixed-duration tests, state arrival, measurement, and drain windows and how unfinished requests are counted. Verify the client itself is not CPU/network/connection limited.

Report p50 and the tails required by the task, completed/attempted counts, and actual input/output distributions. Too few observations cannot support a reliable tail percentile. [MLPerf's scenario rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) illustrate distinct closed-loop, server-arrival, and offline workloads; using that distinction does not make a custom benchmark MLPerf-compliant.

## Separate cold and warm work

Specify what is cold: process, model residency, filesystem cache, compilation cache, graph cache, or prefix KV. Run each relevant state separately.

For uncached-prefill tests, disable/reset prefix reuse using a supported mechanism, or alter tokenized prefixes early enough to prevent reuse and verify engine cache counters. A unique suffix does not invalidate a shared prefix. Label intended warm-prefix tests with their reuse distribution and hit/miss counters.

`prompt_tokens / TTFT` is a client-observed effective input rate, not isolated prefill throughput: TTFT includes queueing, transport, tokenization, first-output work, and possibly cache hits. Use engine spans/counters for prefill compute time and distinguish full prompt length from newly computed tokens. Do not infer uncached processing speed from a cached request.

Measure startup from an explicit launch boundary to readiness **and** the first successful representative request. HTTP health alone can precede model initialization, lazy compilation, graph capture, or tool/parser readiness. Separate cold and persistent-cache restarts.

## Compare candidates with drift controls

Use independent repeated blocks such as baseline/candidate/baseline, then vary block order when appropriate. Keep each run's ID, timestamps, config hash, environment snapshot, request records, and logs unique; repeating a config name must not overwrite the first control.

Inspect both neighboring controls and the distribution of paired effects. If controls drift enough to change the conclusion, mark the block inconclusive and investigate temperature, clocks, power, cache state, or load. Medians resist outliers but do not eliminate systematic drift. Choose a practical improvement threshold and regression limits before selecting a winner; do not inherit universal percentages or sample counts.

Repeat promising candidates on an untouched prompt panel to limit selection bias from many trials. Preserve rejected/invalid runs. If a change shortens output, compare quality and length distributions rather than claiming the entire latency reduction is faster decoding.

## Audit a harness before trusting its ledger

Use an isolated mock or captured trace to exercise: multi-token chunks, reasoning-only and tool deltas, usage-only trailers, delayed completion, missing usage, interrupted streams, request errors, and empty/one-token outputs. Follow each endpoint's completion contract; an unexpected EOF is not a successful response.

Check that:

- Missing usage/monitoring yields an explicit unknown/invalid result, never zero work or zero memory.
- All request failures and quality checks affect acceptance; a warning field alone must not leave a failed candidate eligible.
- Token timestamps exclude metadata while completion status still requires the terminal protocol signal.
- Actual overlap and total wall time support concurrency claims.
- Logs/configs are immutable per run; comparison uses matching workload/settings.
- Ownership, lock failure, timeout, and cleanup behavior are tested without targeting real services.

Use the [upstream vLLM benchmark client](https://docs.vllm.ai/en/latest/benchmarking/cli) or the engine's equivalent where supported. A generic API schema does not guarantee identical usage, reasoning, streaming, or metrics behavior across backends.
