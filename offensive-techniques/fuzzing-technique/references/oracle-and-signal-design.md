# Oracle and signal design

## Objective

Define bug signals that are meaningful, reproducible, and low-noise before scaling campaigns.

## Oracle categories

1. **Memory-safety oracles**
   - Signals: invalid read/write, UAF, OOB, corruption.
   - Typical detection path: sanitizer-enabled profiles.

2. **Behavioral/stability oracles**
   - Signals: hang, timeout, OOM, non-termination, service death.
   - Useful for parsers, protocol state machines, and complex allocators.

3. **Differential oracles**
   - Signals: output mismatch between equivalent implementations.
   - Useful when crashes are rare but logic divergence matters.

4. **Invariant/property oracles**
   - Signals: violations of explicit properties (idempotency, schema validity, monotonic constraints).
   - Useful for API/data pipelines and format round-trip checks.

## Oracle selection rules

- Start with one primary oracle and one secondary oracle.
- Keep oracle outcomes deterministic and machine-checkable.
- Avoid over-instrumentation in every instance; mix high-throughput and high-signal profiles.

## Signal quality checklist

- Failure class is explicit (crash, timeout, mismatch, invariant break).
- Failure can be replayed with same input/sequence.
- Failure bucket can be grouped by stable signature.
- Failure is attributable to target behavior, not harness instability.

## Common pitfalls

- Treating every non-2xx API response as a bug signal.
- Mixing transport instability with target logic failures.
- Using only one oracle type and missing non-crash vulnerabilities.
