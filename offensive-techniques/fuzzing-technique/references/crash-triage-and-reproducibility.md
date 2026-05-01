# Crash triage and reproducibility

## Objective

Convert raw failures into a small set of reproducible, prioritized vulnerability candidates.

## Triage pipeline

1. **Collect evidence**
   - Preserve crashing input/sequence and runtime metadata.
   - Keep stack traces, failure logs, and campaign profile identity.

2. **Bucket**
   - Group by stable signature (stack + failure class + state phase).
   - Avoid treating every artifact as unique until bucketing is done.

3. **Minimize**
   - Reduce to shortest reproducer that still triggers same bucket behavior.
   - Keep one representative minimized artifact per bucket.

4. **Replay and confirm**
   - Replay in controlled environment and confirm deterministic trigger.
   - Verify not caused by harness/model instability.

5. **Prioritize**
   - Higher priority for strong control primitives, high reachability, and low preconditions.
   - Lower priority for flaky or environment-dependent failures.

## Repro metadata contract

For each confirmed bucket, record:

- target version/build identity,
- profile identity (throughput vs signal-focused),
- exact input/sequence artifact,
- resource limits and runtime assumptions,
- expected failure signature.

## Practical replay rules

- Reproduce with minimal moving parts first.
- If non-deterministic, fix reset/time dependency before deeper analysis.
- Maintain a regression set for fixed bugs and rerun periodically.

## Common pitfalls

- Debugging before minimization.
- Mixing sanitizer and non-sanitizer results without labeling.
- Promoting non-reproducible failures as confirmed vulnerabilities.
