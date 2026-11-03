---
name: testing-reliability
description: "Diagnose flaky tests, misleading mocks or fakes, sleep-based waits, brittle fixtures, test-only production hooks, weak assertions, and mutation-testing gaps. Use when CI behavior differs, tests hide defects, or coverage creates false confidence."
license: MIT
compatibility: "Language-agnostic testing guidance. Pair with python-testing, c-testing, cpp-testing, golang-testing, rust-testing, or asm-testing for concrete commands."
metadata:
  author: AeonDave
  version: "1.3"
---

# Testing Reliability

Make tests detect the behavior they claim to cover and make failures attributable. Use this skill to repair the test signal; `test-driven-development` owns the test-first implementation loop.

## When to activate

- Flaky, timing-sensitive, or order-dependent tests.
- Heavy mocks, unclear patch targets, or fakes that do not match real behavior.
- Production code changed only to make tests easier.
- Coverage increased without stronger assertions.
- Surviving or uncovered mutants in behavior that matters.
- CI failures that cannot be reproduced locally.

## Reliability workflow

1. Identify the claimed behavior and the misleading result. Preserve the failure evidence or demonstrate a missed defect with the smallest relevant test selection; a local pass does not invalidate a CI failure.
2. Investigate the relevant source of uncertainty: assertions, test doubles, fixture lifecycle, time, randomness, filesystem/network state, locale, order, or concurrency. Use `systematic-debugging` when failure attribution or the product defect remains unclear.
3. Correct that cause. Strengthen an assertion, isolate/reset owned state, repair synchronization, or replace an inaccurate double as needed; do not apply every technique to every test.
4. Check sensitivity to the defect and preservation of valid behavior. For a double, check the part of the collaborator's contract that matters; choose a real dependency, fake, stub, or mock according to the test's scope and control needs.
5. Run focused checks and relevant broader tests. Repeat or vary order/schedules when investigating a flake, with a bounded diagnostic purpose; do not rerun until a convenient green result hides failures. Use `verification-before-completion` for final coverage and freshness.

## Anti-patterns to remove

- Testing incidental internal calls instead of the required behavior or interaction contract.
- Partial mocks that silently omit important side effects.
- Sleeping for async behavior instead of waiting on a condition.
- Shared mutable fixtures that couple tests by order.
- Golden outputs updated without reviewing semantic changes.
- Coverage-only tests that assert nothing meaningful.

## Offensive testing focus

- Exploit harnesses must prove primitives, not just crash/no-crash.
- Fuzz reproducer tests must pin seed/input and minimized artifact.
- Network tooling tests should use captured transcripts, local test servers, or protocol fakes.
- Evasion tests must distinguish telemetry absence from collection failure.

## Resources

Load on demand:

- [references/testing-anti-patterns.md](references/testing-anti-patterns.md) — load when diagnosing mock/timing failures, coverage without useful assertions, or mutation results.

Scripts:

- `scripts/find_polluter.py` — runs matching test files separately and reports the first that leaves a watched filesystem path present. It does not detect in-memory state, changes to existing files, or interactions requiring a sequence of test files; inspect command failures before interpreting a clean result.
