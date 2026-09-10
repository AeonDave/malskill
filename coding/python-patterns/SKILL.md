---
name: python-patterns
description: "Pythonic patterns for readable, robust Python: typing, error handling, data modeling, iteration, resource management, threading/process/subinterpreter primitives, project layout, and tooling. Use when writing or reviewing Python code and APIs. For measurement/GIL/JIT use python-performance; for asyncio orchestration use python-async-patterns."
license: MIT
compatibility: "Python 3.11+ (guidance baseline; current stable CPython 3.14.7). Optional tools: ruff, mypy, pytest."
metadata:
  author: AeonDave
  version: "1.3"
---

# Python Patterns

This skill is for **day-to-day Python code quality**: readability, correctness, maintainability.

If you are doing asyncio-heavy work, prefer `python-async-patterns`. If the task is profiling, GIL/free-threading, or experimental JIT, use `python-performance`.

## When to activate

- Writing/refactoring Python modules, libraries, services
- Reviewing PRs for idioms, clarity, and footguns
- Introducing typing or improving error handling
- Designing lightweight data models and APIs
- Choosing threads vs processes vs subinterpreters (not asyncio)

---

## Core principles (high signal)

- Readability beats cleverness.
- Be explicit at boundaries (I/O, parsing, network). Keep inner code simple.
- Prefer small, typed functions with clear names.
- Use context managers for resource safety.
- Raise specific exceptions and preserve causes (`raise ... from e`).

---

## Outcome expectations

- Code is readable; intent is clear from names and structure, not comments.
- All public APIs have type annotations; error boundaries are explicit.
- Resource cleanup is deterministic (via context managers, no `__del__`).
- Exceptions are domain-specific and chain causes; no silent failures.

---

## Recommended workflow

1. Design module interfaces with clear input/output types and error contracts.
2. Use context managers for all resource acquisition.
3. Validate at I/O boundaries; raise specific errors with cause chaining.
4. Apply ruff, mypy (on public APIs), and pytest baseline in CI.
5. Review code for footguns (mutable defaults, bare `except`, type hiding).

---

## Quick review checklist

- No mutable default arguments; `None` sentinel used
- `is None` / `is not None` (not `== None`)
- Specific `except` clauses; no bare `except:`
- Types: public functions/classes have annotations; 3.12+ type-parameter syntax; `T | None` not `Optional[T]`
- Files/paths use `pathlib.Path` (`Path.walk` 3.12+); not `os.path` string soup
- Iteration uses comprehensions/generators only when simple
- CPU-bound fan-out uses executors from `concurrency.md`, not unbounded `Thread` spawns

---

## Resources

Load on demand:

- `references/typing.md` — load for annotations, PEP 695 generics, Protocols, 3.14 deferred evaluation
- `references/errors.md` — load for exception hygiene, `ExceptionGroup` / `except*`, `finally` control flow
- `references/data-models.md` — load for dataclasses, `copy.replace`, `StrEnum`, t-strings (3.14)
- `references/iteration.md` — load for comprehensions, generators, `itertools.batched`, `match`
- `references/resources.md` — load for context managers and pathlib
- `references/concurrency.md` — load for threads, `concurrent.futures`, queues, multiprocessing start methods, `InterpreterPoolExecutor`
- `references/layout-tooling.md` — load for `pyproject.toml`, ruff/mypy/pytest, removed stdlib modules
- `references/performance.md` — one-screen "don't micro-optimize here"; real measurement is `python-performance`
