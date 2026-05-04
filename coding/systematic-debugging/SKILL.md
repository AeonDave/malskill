---
name: systematic-debugging
description: "Root-cause-first debugging workflow for software, exploit tooling, fuzzing harnesses, reverse-engineering helpers, C2/client code, flaky tests, crashes, races, and environment-specific failures. Use when a failure is not immediately obvious or when repeated quick fixes risk hiding the real defect."
license: MIT
compatibility: "Language-agnostic debugging workflow. Pair with language-specific testing, performance, reversing, or offensive-coding skills as needed."
metadata:
  author: AeonDave
  version: "1.0"
---

# Systematic Debugging

Fix the cause, not the symptom. Fast guesses are allowed only after the failure is reproduced and falsifiable.

## When to activate

- Crash, timeout, flaky test, exploit instability, silent corruption, race, or environment-specific failure.
- Two attempted fixes did not solve the issue.
- The observed failure is far from the likely source: heap corruption, async timing, protocol state, ABI mismatch, or bad fixture isolation.

## Workflow

1. **Reproduce**: get the smallest command/input that fails. Capture environment, seed, target version, and exact output.
2. **Classify**: assertion failure, crash, hang, race, memory/UB, network/protocol, config, permission, or tool misuse.
3. **Trace backward**: follow data/control flow from symptom to first wrong state.
4. **Form one hypothesis**: state what would prove or disprove it.
5. **Instrument narrowly**: log, breakpoint, sanitizer, packet trace, syscall trace, or debugger watchpoint at the boundary of uncertainty.
6. **Patch minimally**: fix the root cause and remove temporary instrumentation.
7. **Regression gate**: add or update a test/reproducer, then run focused and relevant broader checks.

## Three-fix stop rule

After three plausible fixes fail, stop patching. Re-open the investigation from reproduction and assumptions; the model of the bug is probably wrong.

## Offensive debugging focus

- Exploit dev: verify offsets, mitigations, architecture, target build, and debugger side effects.
- Fuzzing: minimize reproducer, dedupe crashes, record seed/corpus, and confirm outside the fuzzer.
- Shellcode/BOF/loader work: check ABI, stack alignment, calling convention, clobbered registers, and import resolution.
- Network tooling: capture wire data before changing parser or retry logic.
- Evasion research: distinguish bypass failure from environmental control, policy, or telemetry differences.

## Resources

Load on demand:

- `references/root-cause-tracing.md` — tracing from symptom to first wrong state.
- `references/condition-based-waiting.md` — replacing sleeps/timeouts with deterministic waits.
- `references/defense-in-depth.md` — layered fixes that prevent recurrence without overengineering.

Pair with `test-driven-development` when turning a root cause into a regression test, and `verification-before-completion` before claiming the fix is complete.
