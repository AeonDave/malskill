---
name: c-testing
description: "C testing workflow for unit and integration tests: deterministic harnesses, CMake/CTest execution strategy, sanitizer-first debugging, and fuzzing escalation. Use when writing or fixing tests for C (C11+) modules, stabilizing flaky suites, or reproducing memory/UB bugs."
license: MIT
compatibility: "C11 baseline. Tools: CMake/CTest or Make. Debugging: gdb/lldb (Linux/macOS), MinGW gdb + objdump (Windows), MSVC dumpbin + WinDbg (Windows). Optional: sanitizers (Clang/GCC), fuzzing (libFuzzer/AFL where supported)."
metadata:
  author: AeonDave
  version: "1.1"
---

# C Testing

Pragmatic workflow for reliable C tests and bug-finding.

## When to activate

- Adding unit tests for C functions
- Building a small test harness around a module
- Debugging failing tests or memory corruption
- Enabling sanitizers or fuzzing to reproduce crashes

---

## Core rules

- Keep unit tests deterministic and isolated.
- Avoid real network/time in unit tests.
- Run ASan/UBSan in CI for memory and UB signal.
- Reproduce failures in the smallest possible command first.
- Do not hide memory/UB bugs behind test-only flags, retries, or inflated timeouts.
- Pair with `test-driven-development` when implementing persistent code or bug fixes test-first.
- Pair with `testing-reliability` for fixture/timing anti-patterns and `systematic-debugging` when the root cause is unclear.

---

## Recommended workflow

### Phase 1 — Reproduce with smallest scope

- Run the single failing test first (`ctest -R ...` or direct binary invocation).
- Capture exact command, seed/input, and environment variables.
- Eliminate unrelated test noise before debugging.

### Phase 2 — Strengthen harness determinism

- Keep each test independent (no shared mutable global state).
- Use explicit fixtures/setup-teardown for temp files and state reset.
- Prefer table-driven tests for parsers and boundary-heavy functions.

### Phase 3 — Sanitizer-first diagnosis

- Run AddressSanitizer for memory corruption/UAF/OOB.
- Run UndefinedBehaviorSanitizer for integer/shift/null/alignment UB.
- Use stack-symbolized reports before stepping into debugger.

### Phase 4 — CTest execution strategy

- Label tests (`unit`, `integration`, `slow`, `flaky`) and run by label.
- Use `--output-on-failure` and `--rerun-failed` in local loops.
- Add per-test `TIMEOUT` to avoid hanging pipelines.

### Phase 5 — Fuzzing escalation

- Add libFuzzer target for parser/decoder/validator style APIs.
- Seed corpus with valid and invalid minimal inputs.
- Keep fuzz target stateless, deterministic, and side-effect free.

---

## Fast triage checklist

- [ ] Single failing test reproduced in isolation.
- [ ] Failure reproduced under sanitizer build (if memory/UB suspected).
- [ ] Backtrace/symbolization points to root cause function.
- [ ] Regression test added for the fixed bug.
- [ ] Full suite rerun (or label-targeted suite if justified) with no new failures.

---

## Resources

Load on demand:

- `references/harness.md` — harness structure, assertions, Unity/cmocka options
- `references/cmake-ctest.md` — CMake/CTest patterns, labels, sanitizer presets, MinGW cross-compile
- `references/sanitizers-fuzzing.md` — ASan/UBSan usage and a minimal fuzz target outline
- `references/debugging.md` — gdb/lldb, Valgrind, MinGW objdump/nm, MSVC dumpbin/WinDbg, ASan env vars
