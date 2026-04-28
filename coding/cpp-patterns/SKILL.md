---
name: cpp-patterns
description: "Modern C++ patterns and best practices for readable, safe, maintainable C++ code: RAII, ownership, error handling, API design, concurrency basics, and build/tooling hygiene. Use when writing or reviewing C++ (C++20+) code."
license: MIT
compatibility: "C++20 baseline. Toolchains: MSVC, Clang, GCC, MinGW-w64. Build: CMake recommended. Binary inspection: objdump/nm (MinGW/Linux), dumpbin (MSVC), readelf/ldd (Linux)."
metadata:
  author: AeonDave
  version: "1.1"
---

# C++ Patterns

Use this skill for **day-to-day modern C++ (C++20+)** with a bias for safety, clarity, and maintainable APIs.

If your primary task is test architecture/debugging, activate `cpp-testing` alongside this skill.

## When to activate

- Writing new C++ modules/libraries/services
- Reviewing PRs for ownership, lifetime, and exception safety
- Refactoring for cleaner interfaces and fewer footguns
- Introducing RAII, smart pointers, and standard library algorithms

---

## Outcome expectations

- APIs encode ownership and lifetime intent directly in types.
- Resource cleanup is deterministic (RAII) and exception-safe.
- Error behavior is consistent per layer (no mixed ad-hoc strategy).
- Concurrency code has explicit stop/cancellation and race-checking plan.

---

## Core rules (high signal)

- Prefer **RAII** for resource ownership; avoid raw `new`/`delete`.
- Use **value types** by default; use references/pointers to express optionality and non-ownership.
- Use `std::unique_ptr` for exclusive ownership; `std::shared_ptr` only when shared ownership is required.
- Prefer **standard algorithms** over hand-written loops when it improves clarity.
- Keep APIs small; make invalid states unrepresentable where feasible.
- Define clear error strategy: exceptions vs `std::expected`-style returns vs status codes.

---

## Recommended workflow

1. Clarify ownership and lifetime boundaries first (handles, buffers, views, async captures).
2. Design the public API around value semantics and explicit contracts.
3. Implement with RAII wrappers and Rule-of-Zero defaults.
4. Add warnings/sanitizers/static analysis early in the build.
5. Review for footguns (dangling views, iterator invalidation, detached threads).

---

## Quick review checklist

- Ownership is explicit (who allocates, who frees)
- No leaks or dangling refs (temporaries, `string_view`, iterator invalidation)
- Rule of Zero is used; special members defined only when needed
- `const` correctness is consistent
- No surprising implicit conversions; use `explicit`
- Concurrency code has a cancellation/stop strategy
- Error semantics and exception guarantees are documented

---

## Common anti-patterns to reject

- Owning raw pointers in public APIs
- Returning/storing `std::string_view` tied to temporary storage
- Detached threads that capture `this` without a lifetime model
- Broad `catch (...)` blocks that hide failure context
- Exposing mutable shared state without synchronization policy

---

## Resources

Load on demand:

- `references/ownership-raii.md` — ownership rules, RAII patterns, smart pointers, lifetime
- `references/core-guidelines.md` — distilled C++ Core Guidelines pointers
- `references/api-design.md` — interface design, value semantics, error strategy
- `references/concurrency.md` — jthread, mutex, atomic, condition_variable, stop_token, race detection
- `references/tooling-build.md` — compiler warnings, sanitizers, static analysis, binary inspection (MinGW/objdump, MSVC/dumpbin, Linux tools), CMake hygiene
