---
name: c-patterns
description: "C language patterns and best practices for safe, maintainable C: ownership, API contracts, error handling, integer safety, portability, and concurrency boundaries. Use when writing or reviewing C code (C11+), designing module interfaces, refactoring legacy C, or hardening low-level code paths."
license: MIT
compatibility: "C11 baseline. Toolchains: Clang, GCC, MSVC (C mode), MinGW-w64. Build: CMake or Make. Binary inspection: objdump/nm (MinGW/Linux), dumpbin (MSVC), readelf/ldd/strace (Linux)."
metadata:
  author: AeonDave
  version: "1.1"
---

# C Patterns

This skill focuses on **safe C**: explicit ownership, explicit errors, predictable control flow, and contracts that survive refactors.

If you’re writing tests, use `c-testing`.

## When to activate

- Writing/refactoring C modules and APIs
- Reviewing for memory safety and integer safety
- Designing error-handling conventions and cleanup paths
- Hardening code for sanitizer/static analysis adoption
- Porting C code across GCC/Clang/MSVC/MinGW

---

## Core rules (high signal)

- Make ownership explicit: allocate/free at the same abstraction level.
- Use a consistent error strategy (return codes, out-params) and document it in headers.
- Avoid in-band error indicators when possible.
- Use a single-exit cleanup path for functions managing multiple resources.
- Treat integer conversions and size calculations as potential bugs.

---

## Recommended workflow

### Phase 1 — Define API contract first

Before coding:

- Define ownership of every pointer parameter (`borrowed`, `owned`, `transferred`).
- Define preconditions/postconditions in the header, not only in comments inside `.c`.
- Define error domain (`enum` or code space) and whether `errno` is used.

### Phase 2 — Implement with explicit lifetimes

- Use `create/destroy`, `init/deinit`, or `open/close` pairs consistently.
- Keep one cleanup exit path for multi-resource functions.
- Do not mix allocator families (`malloc/free` vs custom pool vs Win32 heaps).

### Phase 3 — Harden integer and bounds logic

- Use `size_t` for sizes/counts and guard all multiplication/addition used in allocation.
- Validate all signed/unsigned conversions and indexing arithmetic.
- Reject impossible sizes early (`n == 0`, `n > MAX_ALLOWED`, overflow guards).

### Phase 4 — Concurrency boundaries

- Prefer immutable data or message passing where possible.
- If locks are needed, document lock ownership and lock order in header comments.
- Use atomics for single-value state; mutexes for compound invariants.

### Phase 5 — Toolchain-aware portability

- Keep warning set strict on all compilers (GCC/Clang/MSVC).
- Avoid UB-dependent behavior and compiler-specific assumptions.
- Guard compiler-specific attributes/macros with feature checks.

---

## Quick review checklist

- [ ] Every pointer has clear ownership semantics in the API.
- [ ] Every non-trivial function has deterministic cleanup path.
- [ ] Every allocation arithmetic path has overflow guard.
- [ ] Every error path returns actionable status.
- [ ] Concurrency primitives protect explicitly documented data.
- [ ] Code builds clean with strict warnings on at least two toolchains.

---

## Resources

Load on demand:

- `references/error-handling.md` — error policy, return codes, cleanup patterns
- `references/memory-ownership.md` — allocation/free rules, zero-length alloc, free-null
- `references/integers.md` — overflow, size_t usage, bounds checking
- `references/concurrency.md` — pthreads, C11 atomics, Win32 threads, race detection
- `references/tooling.md` — warnings, sanitizers, static analysis, binary inspection (MinGW/objdump, MSVC/dumpbin, Linux tools)
