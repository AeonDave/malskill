---
name: cpp-testing
description: "C++ testing workflow for unit and integration tests: GoogleTest/GoogleMock, CMake/CTest integration, diagnosing flaky tests, and running sanitizers and coverage for correctness signal. Use when writing or fixing C++ tests and test infrastructure."
license: MIT
compatibility: "C++20 baseline. Tools: CMake 3.20+, CTest. Recommended: GoogleTest. Debugging: gdb/lldb/Valgrind (Linux/macOS), MinGW gdb + objdump (Windows), MSVC dumpbin + WinDbg (Windows). Optional: sanitizers (Clang/GCC/MSVC), coverage (llvm-cov or lcov)."
metadata:
  author: AeonDave
  version: "1.1"
---

# C++ Testing

High-signal workflow for writing and maintaining reliable C++ tests.

## When to activate

- Adding new unit tests, regression tests, or integration tests
- Fixing failing or flaky C++ tests
- Wiring GoogleTest with CMake/CTest
- Enabling sanitizers for memory/UB/race diagnostics

---

## Outcome expectations

- Fast deterministic unit tests with clear failure messages.
- Integration tests separated and labeled by cost/risk.
- Flake triage follows reproducible, root-cause-first workflow.
- Sanitizers/coverage are integrated as recurring quality signal.

---

## Core rules

- Tests must be deterministic: no sleeping for synchronization.
- Prefer fakes for state, mocks for interactions.
- Use `ASSERT_*` for preconditions, `EXPECT_*` for additional checks.
- Keep unit tests fast; label integration tests separately.
- Keep one source of truth for test configuration in CMake targets.
- Avoid production-only test hooks unless they expose a real design seam.
- Pair with `test-driven-development` when implementing persistent code or bug fixes test-first.
- Pair with `testing-reliability` for mock/timing anti-patterns and `systematic-debugging` when symptoms are far from the defect.

---

## Recommended workflow

1. Define the behavior and test scope (unit vs integration) first.
2. Add/adjust tests with clear Arrange-Act-Assert structure.
3. Run focused test selection (`ctest -R` / gtest filter).
4. Run sanitizers for memory/UB/races where applicable.
5. If flaky/failing, minimize reproducer and fix root cause before broad reruns.

---

## Triage loop for failing tests

1. Reproduce deterministically on one test binary.
2. Capture failure class: assertion mismatch, crash, timeout, data race, UB.
3. Narrow input/state until minimal failing case is obtained.
4. Fix production code first (or fixture isolation), then harden test.
5. Re-run focused + full suite + sanitizer build.

---

## Resources

Load on demand:

- `references/googletest-cmake.md` — FetchContent + CTest discovery (gtest_discover_tests)
- `references/test-design.md` — unit vs integration, fixtures, parameterized tests
- `references/sanitizers-coverage.md` — ASan/UBSan/TSan + coverage recipes
- `references/flakes-debugging.md` — anti-flake rules, gdb/lldb, Valgrind, MinGW objdump/nm, MSVC dumpbin/WinDbg, sanitizer env vars
