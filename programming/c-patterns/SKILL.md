---
name: c-patterns
description: "C language patterns and best practices for safe, maintainable C: ownership, error handling, integer safety, and API design. Use when writing or reviewing C code (C11+) and when designing low-level modules with clear resource lifetimes."
license: MIT
compatibility: "C11 baseline. Toolchains: Clang, GCC, MSVC (C mode), MinGW-w64. Build: CMake or Make. Binary inspection: objdump/nm (MinGW/Linux), dumpbin (MSVC), readelf/ldd/strace (Linux)."
metadata:
  author: AeonDave
  version: "1.0"
---

# C Patterns

This skill focuses on **safe C**: explicit ownership, explicit errors, and predictable control flow.

If you’re writing tests, use `c-testing`.

## When to activate

- Writing/refactoring C modules and APIs
- Reviewing for memory safety and integer safety
- Designing error-handling conventions and cleanup paths

---

## Core rules (high signal)

- Make ownership explicit: allocate/free at the same abstraction level.
- Use a consistent error strategy (return codes, out-params) and document it.
- Avoid in-band error indicators when possible.
- Use a single-exit cleanup path for functions managing multiple resources.
- Treat integer conversions and size calculations as potential bugs.

---

## Resources

Load on demand:

- `references/error-handling.md` — error policy, return codes, cleanup patterns
- `references/memory-ownership.md` — allocation/free rules, zero-length alloc, free-null
- `references/integers.md` — overflow, size_t usage, bounds checking
- `references/concurrency.md` — pthreads, C11 atomics, Win32 threads, race detection
- `references/tooling.md` — warnings, sanitizers, static analysis, binary inspection (MinGW/objdump, MSVC/dumpbin, Linux tools)
