---
name: python-testing
description: "Python testing with pytest: TDD loop, fixtures, parametrization, mocking, test organization, async tests, Hypothesis, ExceptionGroup, free-threaded caveats, coverage, and CI hygiene. Use when writing or reviewing Python tests to improve correctness and reduce flakiness."
license: MIT
compatibility: "Python 3.11+ (guidance baseline; current stable CPython 3.14.7). Tools: pytest. Optional: pytest-cov, pytest-asyncio, hypothesis. Free-threaded CI: python3.14t."
metadata:
  author: AeonDave
  version: "1.2"
---

# Python Testing

High-signal guidance for writing tests that are **deterministic**, **readable**, and **maintainable**.

## When to activate

- Adding tests (unit/integration) for new or existing code
- Refactoring tests to reduce flakiness
- Designing fixtures and test organization
- Adding coverage, CI checks, or async tests
- Property tests (Hypothesis) or concurrent/free-threaded suites

---

## Outcome expectations

- Tests are deterministic and pass reliably in CI.
- Coverage is meaningful; assertions test behavior, not implementation details.
- Flaky tests are rare and quickly diagnosed (fixtures, mocking, timing).
- New developers can understand test intent within 30 seconds of reading.

---

## Recommended triage workflow

**For new code**:
1. Write a failing test (red).
2. Implement minimal code to pass (green).
3. Refactor with tests staying green.

**For flaky/failing tests**:
1. Check for shared state (mocks, fixtures, filesystem).
2. Check for timing assumptions (avoid `sleep`, use synchronization).
3. Check mock patch targets (patch as used, not where defined).
4. Isolate to minimal reproduction in separate test.

---

## Core rules

- Prefer **small unit tests** for logic; use integration tests for boundaries.
- Use pytest fixtures to remove duplication, but avoid fixture overengineering.
- Avoid sleeping in tests; synchronize via conditions/events.
- Mock at boundaries (network, time, DB), not everywhere.
- Coverage is a signal: aim for meaningful assertions, not line-hits.
- Do not add production hooks solely for tests; use real seams or dependency injection.
- Pair with `test-driven-development` when implementing persistent code or bug fixes test-first.
- If mocks, timing, or flakes dominate, pair with `testing-reliability`; if the root cause is unclear, pair with `systematic-debugging`.
- Asyncio-heavy tests: also load `python-async-patterns` `testing.md`.
- `CancelledError` and `ExceptionGroup` are not caught by `pytest.raises(Exception)` / `pytest.raises(ValueError)` respectively.

---

## Resources

Load on demand:

- `references/tdd-and-structure.md` — TDD loop, naming, organizing tests
- `references/fixtures-parametrize.md` — fixtures (scopes, autouse), parametrization patterns
- `references/mocking.md` — unittest.mock, patching correctly, async mocks
- `references/async.md` — pytest-asyncio loop scope; cancellation/`ExceptionGroup` pointers
- `references/concurrency.md` — load for threads, `InterpreterPoolExecutor`, free-threaded suites
- `references/property.md` — load when example tests miss a space Hypothesis can shrink
- `references/coverage-ci.md` — pytest-cov, coverage hygiene, CI tips
- `references/commands.md` — common pytest commands and selectors
