# Testing Anti-Patterns

Use this reference during test review or flake triage.

## Mocking problems

| Anti-pattern | Risk | Replacement |
|---|---|---|
| Mock every dependency | Tests mirror implementation | Mock only trust boundaries |
| Assert only calls happened | No behavior verified | Assert output/state/security property |
| Partial fake omits side effects | False confidence | Complete fake or real local service |
| Patch where defined, not used | Mock has no effect | Patch/import at call site |

## Timing problems

- Avoid fixed sleeps for async/process/network readiness.
- Wait on observable state with deadline and diagnostic timeout output.
- Prefer fake clocks, events, channels, health checks, or file hash/size stability.

## Test-only production changes

Reject changes that add public APIs, flags, or behavior only for tests unless they represent a legitimate seam also useful in production. Prefer dependency injection, local fixtures, or package-private/internal helpers where language conventions support them.

## Flake triage

1. Repeat focused test enough times to confirm instability.
2. Randomize or isolate order if shared state is suspected.
3. Capture seed, environment, CPU/OS, timezone, and parallelism settings.
4. Fix isolation or synchronization before increasing timeouts.

## Coverage traps

Coverage does not prove correctness. Add assertions for:

- security boundary behavior
- malformed/edge input
- error paths and cleanup
- privilege/authorization decisions
- concurrency invariants
