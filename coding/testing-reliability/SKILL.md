---
name: testing-reliability
description: "Cross-language testing reliability skill for flaky tests, bad mocks, sleep-based timing, test-only production hooks, brittle fixtures, incomplete fakes, and weak assertions. Use alongside language-specific testing skills when tests pass locally but fail in CI, hide real defects, or create false confidence."
license: MIT
compatibility: "Language-agnostic testing guidance. Pair with python-testing, c-testing, cpp-testing, golang-testing, rust-testing, or asm-testing for concrete commands."
metadata:
  author: AeonDave
  version: "1.1"
---

# Testing Reliability

This skill focuses on test trustworthiness, not syntax. A test suite that passes for the wrong reason is worse than no test.

## When to activate

- Flaky, timing-sensitive, or order-dependent tests.
- Heavy mocks, unclear patch targets, or fakes that do not match real behavior.
- Production code changed only to make tests easier.
- Coverage increased without stronger assertions.
- CI failures that cannot be reproduced locally.

## Reliability workflow

1. Reproduce the failure or false confidence with the smallest test selection.
2. Identify the hidden dependency: time, random, filesystem, network, process state, global state, locale, order, or concurrency.
3. Replace sleeps with observable conditions or fake clocks/events.
4. Move mocks to trust boundaries; prefer fakes for stateful collaborators.
5. Remove test-only production hooks unless they represent a real public seam.
6. Strengthen assertions around behavior and invariants, not implementation trivia.
7. Run focused, repeated, and then broader checks.

## Anti-patterns to remove

- Testing mock expectations instead of product behavior.
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

- `references/testing-anti-patterns.md` — detailed anti-patterns and safer replacements.

Scripts:

- `scripts/find_polluter.py` — run tests one by one to identify which test creates unwanted files or state.
