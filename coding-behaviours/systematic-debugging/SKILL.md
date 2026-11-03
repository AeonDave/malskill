---
name: systematic-debugging
description: "Root-cause-first debugging workflow for software, exploit tooling, fuzzing harnesses, reverse-engineering helpers, C2/client code, flaky tests, crashes, races, and environment-specific failures. Use when a failure is not immediately obvious or when repeated quick fixes risk hiding the real defect."
license: MIT
compatibility: "Language-agnostic debugging workflow. Pair with language-specific testing, performance, reversing, or offensive-coding skills as needed."
metadata:
  author: AeonDave
  version: "1.1"
---

# Systematic Debugging

Diagnose software failures through observable state and controlled checks. Keep a suspected cause, an effective mitigation, and a verified fix distinct.

## When to activate

- Crash, timeout, flaky test, exploit instability, silent corruption, race, or environment-specific failure.
- Repeated fixes have not explained or resolved the issue.
- The observed failure is far from the likely source: heap corruption, async timing, protocol state, ABI mismatch, or bad fixture isolation.

## Workflow

1. **Frame and preserve**: record expected versus observed behavior, affected scope, command/input, build, configuration, seed, and exact failure evidence as applicable. In an active incident, prioritize authorized containment or recovery; preserve useful evidence without delaying urgent mitigation. Follow [Google SRE's triage guidance](https://sre.google/sre-book/effective-troubleshooting/#triage).
2. **Reproduce or compare**: seek the smallest case retaining the same failure signal. If reproduction is unavailable or intermittent, compare failing and successful traces and relevant environmental differences; continue diagnosis with bounded claims. Do not reset state or discard the only failing artifact to get a clean run.
3. **Localize**: classify the failure and inspect the actual execution path. Trace data, control, ownership, and configuration from the symptom toward the first violated contract; identify the next unknown boundary rather than assuming the crashing line is the cause.
4. **Test a prediction**: state what the suspected mechanism predicts and choose a check that distinguishes it from plausible alternatives. Instrument that boundary with a log, breakpoint, sanitizer, packet/syscall trace, or watchpoint. Iterate tracing and experiments as results arrive; use `hypothesis-driven` when competing explanations need a structured investigation.
5. **Correct the supported cause**: make the smallest complete change that repairs the violated contract, including affected consumers. Keep a necessary workaround explicit when the underlying cause cannot yet be corrected. Preserve diagnostic evidence, then remove temporary probes or retain only useful, bounded diagnostics.
6. **Verify**: add or update a regression test/reproducer where practical, check the original failure and relevant neighboring behavior, then run applicable broader checks. Use `testing-reliability` when the test itself is suspect and `verification-before-completion` for completion gates. For intermittent failures, report tested schedules, seeds, or workload and remaining uncertainty; a single successful run does not establish elimination.

## When progress stalls

When patches or retries stop producing new evidence, stop speculative changes and reassess the observation, environment, and causal model. Use `loop-control-and-pivots`; a fixed attempt count does not diagnose the defect. Continue useful investigation within the authorized scope.

## Offensive debugging focus

- Exploit dev: verify offsets, mitigations, architecture, target build, and debugger side effects.
- Fuzzing: preserve the original input, minimize while retaining the failure signature, and record seed/corpus and instrumentation. Check whether replay outside the fuzzer reproduces the same defect; record environment differences when it does not.
- Shellcode/BOF/loader work: check ABI, stack alignment, calling convention, clobbered registers, and import resolution.
- Network tooling: capture wire data before changing parser or retry logic.
- Evasion research: distinguish bypass failure from environmental control, policy, or telemetry differences.

## Resources

Load only the reference matching the unresolved step:

- [references/root-cause-tracing.md](references/root-cause-tracing.md) — load for downstream symptoms, regression isolation, or tracing state across boundaries.
- [references/condition-based-waiting.md](references/condition-based-waiting.md) — load for startup, async completion, or timing failures where a wait observes the wrong condition.
- [references/defense-in-depth.md](references/defense-in-depth.md) — load after diagnosis when deciding whether a boundary guard or another prevention layer adds value.

Use `software-guidelines` for scoped repository edits and `software-architecture` when the correction changes boundaries or ownership. Report the failure, supported causal chain or remaining hypothesis, delivered change, checks, and limits; use `evidence-before-claims` when the strength of a causal claim is uncertain.
