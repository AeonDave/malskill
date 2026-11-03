# Condition-Based Waiting

Use when a test, exploit harness, or service integration advances too early, hangs, or relies on arbitrary sleeps. For waiting on agent tools and delegated jobs, use `loop-control-and-pivots` and the host's actual wait contract.

## Replace sleeps with conditions

| Weak signal | Condition to establish |
|---|---|
| Sleep after server start or wait for an open port | Readiness for the operation about to run, using the service's defined readiness response or a safe representative probe. |
| File exists or size/hash stops changing | Successful producer completion and validation of the expected artifact; use a completion marker or atomic publication only when the producer guarantees that contract. |
| Sleep after an async task | Await the future/task result or join the worker, then inspect success, failure, or cancellation. |
| Sleep before an exploit stage | The required protocol/target state for this attempt, observed on wire, log, or API. |
| Retry until something succeeds | The operation is safe to repeat and the observed state is documented as transient. |

A port accepting connections proves reachability at that moment, not application readiness. [Kubernetes probe semantics](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-tcp-liveness-probe) make this distinction concrete: a TCP probe checks connection establishment. Likewise, an unchanged file may be paused, stale, truncated, or left by a failed run. Match signals to the current job or generation.

## Wait design

- Define the required predicate and terminal failure states before choosing the wait. Prefer supported futures/events/joins over polling; a notification alone does not prove the predicate or operation succeeded.
- Use one elapsed-time deadline, based on a monotonic clock where available. Bound each blocking probe by the remaining budget; an outer loop timeout cannot bound an unbounded inner call.
- If polling is necessary, use bounded intervals/backoff appropriate to latency and load. Keep the probe read-only where possible; avoid retrying an operation with side effects just to observe completion.
- Handle terminal errors and cancellation promptly instead of swallowing them until timeout. Clean up subscriptions and temporary resources according to their ownership; timing out a wait does not by itself stop the underlying operation.
- On timeout, report the expected predicate, elapsed budget, and last relevant state/error. Do not log secrets. Distinguish an unmet condition from a failed or cancelled producer.
- In tests, use fake clocks or controlled events/barriers where they model the actual mechanism. Exercise pending, success, failure, and cancellation/timeout paths that matter; replacing all concurrency with mocks may hide the race.

## Offensive cautions

- Sleeps can hide races that break outside the lab.
- Repeated probes may increase target noise; waiting longer is not evidence that the state will eventually become ready.
- Retrying exploitation without state checks may change target state or lock accounts.
- A reliable harness records why each stage advanced.
