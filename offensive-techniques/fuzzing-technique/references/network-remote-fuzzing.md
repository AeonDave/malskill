# Network and remote fuzzing methodology

## Objective

Expose bugs in protocol parsing and state transitions while preserving replayability.

## Start from protocol state, not packets

1. Model protocol phases (connect, auth, negotiate, data, teardown).
2. Define legal transitions and high-value illegal transitions.
3. Fuzz both field-level payloads and sequence ordering.
4. For undocumented or partially-documented protocols, derive a machine-readable grammar from RFCs/captures (manually or LLM-assisted) and feed it to a structure-aware mutator instead of byte-only mutation.

## Transport strategy

- Prefer in-memory/emulated transport when possible for speed and determinism.
- Use real network only when transport behavior is itself in scope.
- For remote-only targets, isolate network variability (retries, jitter windows, explicit timeouts).

## Monitor and restart architecture

Use a monitor chain with clear responsibilities:

- **Liveness monitor**: target process/service health.
- **Crash evidence monitor**: crash synopsis, dumps, key logs.
- **Restart monitor**: deterministic recovery and ready-check before next test.

If restart is unreliable, triage quality collapses; fix recovery path first.

## Corpus strategy for protocols

- Seed with captures from real traffic and known-good handshakes.
- Include negative seeds (missing fields, reordering, length mismatches).
- Keep separate corpora for handshake-only and deep-session paths.

## Stateful campaign patterns

- **Depth-first bursts**: explore long sequences for state bugs.
- **Breadth validation**: sweep short sequences for parser robustness.
- **Checkpoint replay**: reuse known-good prefixes to focus mutations near target states.

## Failure handling

- Distinguish protocol rejects from target instability.
- Bucket by state phase + failure signature.
- Minimize to shortest sequence that reproduces bug.

## Common pitfalls

- Treating protocol as stateless and mutating isolated packets only.
- Ignoring restart health and producing non-reproducible “ghost crashes.”
- Mixing transport flakiness with parser faults in the same bucket.
