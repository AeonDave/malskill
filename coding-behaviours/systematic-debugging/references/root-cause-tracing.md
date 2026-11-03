# Root Cause Tracing

Use when the symptom is downstream of the defect, spans component boundaries, or appeared after a change.

## Trace pattern

1. Mark the observed failure and the contract it violates. An unexpected value is not necessarily incorrect.
2. Identify the input/state that produced it and the last observed correct state, if known. Preserve the failing artifact before minimizing it.
3. Walk one boundary backward: caller, parser, allocator, transport, fixture, config, or external service. Compare what the producer emitted with what the consumer received and assumed.
4. Probe the uncertain transition and test the proposed mechanism. If the observation contradicts it, revise the model; do not keep tracing only the favored path.
5. Correct the earliest violated contract the code owns. If an upstream cause is outside scope, make any boundary mitigation explicit and preserve the unresolved cause in the report.

## Evidence to collect

- Exact command/input/seed and failure signature, including exit status or exception details.
- Stack/call path and relevant state on both sides of the uncertain boundary.
- Actual loaded build, symbols, configuration, and dependency versions, not just the source checkout.
- Passing/failing differences: data, permissions, locale, test order, caches, concurrency, or deployment.
- Request/job identifiers and event ordering for async or distributed paths; timestamps alone may be misleading across clocks.

Keep probes narrow and avoid exposing secrets or full sensitive payloads. Account for debugger, tracing, and sanitizer effects on timing and memory layout; if instrumentation changes the symptom, retain that as evidence rather than declaring recovery.

## Choose the isolating check

| Situation | Useful next check |
|---|---|
| Regression with a known working state | Compare code, configuration, dependency, and data changes; hold unrelated inputs steady while testing the suspected difference. |
| Crash far from corruption | Follow allocation, mutation, lifetime, and ownership; use a sanitizer or watchpoint to locate the earlier invalid access. |
| Hang or race | Identify what each waiter needs and which owner can produce it; inspect task/thread stacks, locks, queues, and cancellation paths. Exercise the relevant ordering with supported synchronization. |
| Failure only under one environment | Verify the effective runtime and inputs, then vary the meaningful difference; a local pass does not establish deployment equivalence. |

Use [Git bisection](https://git-scm.com/docs/git-bisect) for a reproducible regression with known good/bad revisions and a consistent failure check. Use an isolated checkout to preserve user work. Skip revisions that cannot test that property; an unrelated build failure is not a bad result for a runtime-bug search. If skipped revisions leave several candidates, report the range. Inspect and test the identified change before claiming its causal mechanism.

## Common traps

- Fixing a null dereference without finding why null became possible.
- Increasing timeouts without finding the condition that never becomes true.
- Retrying network calls without checking protocol state or auth/session invalidation.
- Treating exploit instability as “bad luck” without measuring mitigations and target build.
- Trusting a sanitizer backtrace as the allocation root cause without checking ownership flow.

## Minimal patch test

A correction should explain the observed failure and make the relevant reproducer pass without weakening its assertion or changing the intended contract. Check that neighboring valid and invalid inputs still behave correctly. Use a safe before/after comparison or controlled counter-experiment when it distinguishes the cause; do not reintroduce a fault into a live system just to strengthen the claim.

If the original failure cannot be replayed, report what the available checks establish and what remains unverified. Several special cases can signal a late patch point, but patch size alone does not establish or refute a diagnosis.
