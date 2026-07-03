# Harness writing for effective fuzzing

## Why harness quality matters

The harness is the control plane of the campaign. A weak harness wastes CPU; a good harness multiplies bug yield.

## Non-negotiable properties

- **Deterministic**: same input should follow same behavior.
- **Stateless across iterations**: no leaked mutable global/session state.
- **Fast**: avoid avoidable I/O and expensive setup in per-input path.
- **Failure-transparent**: harness must not swallow target faults.

## Design pattern

1. **One-time init**
   - Load static tables/config once.
   - Keep initialization read-only after setup.

2. **Per-input execution**
   - Parse/route input to a narrow target function.
   - Apply strict local bounds (size/depth) to prevent harness resource collapse.

3. **Cleanup/reset**
   - Reset allocated objects and mutable globals.
   - Ensure threads/timers spawned for one iteration are not retained.

## Scope decisions

- Prefer fuzzing a focused library function over a full application CLI.
- Split multi-format handlers into separate targets when practical.
- Avoid mixing unrelated features in one harness (coverage dilution).

## Input modeling guidance

- For structured formats, consume input in segments and map to semantic fields.
- Reject clearly invalid framing early, but do not over-filter and kill mutation diversity.
- Keep “accept/reject” behavior consistent to stabilize corpus evolution.

## Performance checklist

- In-memory input path preferred over temp files.
- Logging disabled or minimal in hot path.
- No repeated heavy init per testcase.
- Throughput measured before and after each harness refactor.

## Stability checklist

- Warmup run with high iteration count completes without harness-side errors.
- No non-deterministic branch explosions from random/time-dependent code.
- Sanitizer builds run clean on seed corpus (except true target bugs).

## Common harness bugs (and symptoms)

- **Residual state**: unstable coverage, flaky reproductions.
- **Over-broad try/catch/error suppression**: missing crash signal.
- **Timeout-prone parser recursion**: many hangs, weak path growth.
- **Resource leaks in harness**: memory growth unrelated to target bug.

## Decision rule

If a testcase cannot be replayed reliably, fix harness determinism before continuing campaign scale-out.
