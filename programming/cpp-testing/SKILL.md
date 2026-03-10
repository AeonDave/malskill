---
name: cpp-testing
description: "C++ testing workflow for unit and integration tests: GoogleTest/GoogleMock, CMake/CTest integration, diagnosing flaky tests, and running sanitizers and coverage for correctness signal. Use when writing or fixing C++ tests and test infrastructure."
license: MIT
compatibility: "C++20 baseline. Tools: CMake 3.20+, CTest. Recommended: GoogleTest. Debugging: gdb/lldb/Valgrind (Linux/macOS), MinGW gdb + objdump (Windows), MSVC dumpbin + WinDbg (Windows). Optional: sanitizers (Clang/GCC/MSVC), coverage (llvm-cov or lcov)."
metadata:
  author: AeonDave
  version: "1.0"
---

# C++ Testing

High-signal workflow for writing and maintaining reliable C++ tests.

## When to activate

- Adding new unit tests, regression tests, or integration tests
- Fixing failing or flaky C++ tests
- Wiring GoogleTest with CMake/CTest
- Enabling sanitizers for memory/UB/race diagnostics

---

## Core rules

- Tests must be deterministic: no sleeping for synchronization.
- Prefer fakes for state, mocks for interactions.
- Use `ASSERT_*` for preconditions, `EXPECT_*` for additional checks.
- Keep unit tests fast; label integration tests separately.

---

## Resources

Load on demand:

- `references/googletest-cmake.md` — FetchContent + CTest discovery (gtest_discover_tests)
- `references/test-design.md` — unit vs integration, fixtures, parameterized tests
- `references/sanitizers-coverage.md` — ASan/UBSan/TSan + coverage recipes
- `references/flakes-debugging.md` — anti-flake rules, gdb/lldb, Valgrind, MinGW objdump/nm, MSVC dumpbin/WinDbg, sanitizer env vars
