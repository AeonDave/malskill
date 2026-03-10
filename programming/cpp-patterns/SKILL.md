---
name: cpp-patterns
description: "Modern C++ patterns and best practices for readable, safe, maintainable C++ code: RAII, ownership, error handling, API design, concurrency basics, and build/tooling hygiene. Use when writing or reviewing C++ (C++20+) code."
license: MIT
compatibility: "C++20 baseline. Toolchains: MSVC, Clang, GCC, MinGW-w64. Build: CMake recommended. Binary inspection: objdump/nm (MinGW/Linux), dumpbin (MSVC), readelf/ldd (Linux)."
metadata:
  author: AeonDave
  version: "1.0"
---

# C++ Patterns

This skill is for **day-to-day modern C++**: safety, clarity, and maintainable APIs.

If you’re focused on test writing/tooling, use `cpp-testing`.

## When to activate

- Writing new C++ modules/libraries/services
- Reviewing PRs for ownership, lifetime, and exception safety
- Refactoring for cleaner interfaces and fewer footguns
- Introducing RAII, smart pointers, and standard library algorithms

---

## Core rules (high signal)

- Prefer **RAII** for resource ownership; avoid raw `new`/`delete`.
- Use **value types** by default; use references/pointers to express optionality and non-ownership.
- Use `std::unique_ptr` for exclusive ownership; `std::shared_ptr` only when shared ownership is required.
- Prefer **standard algorithms** over hand-written loops when it improves clarity.
- Keep APIs small; make invalid states unrepresentable where feasible.
- Define clear error strategy: exceptions vs `std::expected`-style returns vs status codes.

---

## Quick review checklist

- Ownership is explicit (who allocates, who frees)
- No leaks or dangling refs (temporaries, `string_view`, iterator invalidation)
- Rule of Zero is used; special members defined only when needed
- `const` correctness is consistent
- No surprising implicit conversions; use `explicit`
- Concurrency code has a cancellation/stop strategy

---

## Resources

Load on demand:

- `references/ownership-raii.md` — ownership rules, RAII patterns, smart pointers, lifetime
- `references/core-guidelines.md` — distilled C++ Core Guidelines pointers
- `references/api-design.md` — interface design, value semantics, error strategy
- `references/concurrency.md` — jthread, mutex, atomic, condition_variable, stop_token, race detection
- `references/tooling-build.md` — compiler warnings, sanitizers, static analysis, binary inspection (MinGW/objdump, MSVC/dumpbin, Linux tools), CMake hygiene
