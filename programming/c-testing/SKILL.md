---
name: c-testing
description: "C testing workflow for unit and integration tests: harness structure, CTest integration, diagnosing failures, and using sanitizers and fuzzing for bug-finding signal. Use when writing or fixing tests for C (C11+) modules."
license: MIT
compatibility: "C11 baseline. Tools: CMake/CTest or Make. Debugging: gdb/lldb (Linux/macOS), MinGW gdb + objdump (Windows), MSVC dumpbin + WinDbg (Windows). Optional: sanitizers (Clang/GCC), fuzzing (libFuzzer/AFL where supported)."
metadata:
  author: AeonDave
  version: "1.0"
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

---

## Resources

Load on demand:

- `references/harness.md` — harness structure, assertions, Unity/cmocka options
- `references/cmake-ctest.md` — CMake/CTest patterns, labels, sanitizer presets, MinGW cross-compile
- `references/sanitizers-fuzzing.md` — ASan/UBSan usage and a minimal fuzz target outline
- `references/debugging.md` — gdb/lldb, Valgrind, MinGW objdump/nm, MSVC dumpbin/WinDbg, ASan env vars
