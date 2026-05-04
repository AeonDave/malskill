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

## Exploitability triage state machine

After a crash is minimized and replayable, classify it before handoff:

1. **Crash-only**: deterministic fault, but no attacker influence beyond reachability yet.
2. **Influence suspected**: input bytes affect crash address, size, index, or corrupted object state.
3. **Primitive candidate**: controlled write, controlled read, instruction pointer influence, type confusion, UAF reuse, or allocator metadata corruption is demonstrated.
4. **Exploit path candidate**: mitigations, object lifetime, heap/stack layout, and reachable payload/state path are understood.
5. **Handoff-ready**: evidence package is sufficient for `vuln-exploit-technique` or relevant `offensive-coding/*` exploit-development skill.

Minimum checks:

- Re-run under debugger with the minimized input.
- Inspect registers, fault address, stack/heap object, and taint-adjacent bytes.
- Verify whether the same bytes control length, offset, pointer, index, or branch state.
- Map mitigations: NX/DEP, ASLR/PIE, canary, RELRO, CFG/CET, allocator hardening.
- Record whether the primitive is data-only, control-flow, or denial-of-service only.

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
- Keep minimized artifacts in a regression corpus with expected failure class and fixed-build status.
- If behavior changes under ASLR, threading, or timing variation, isolate that variable before claiming exploitability.

## Common pitfalls

- Debugging before minimization.
- Mixing sanitizer and non-sanitizer results without labeling.
- Promoting non-reproducible failures as confirmed vulnerabilities.
