---
name: test-driven-development
description: "Use when implementing persistent code, bug fixes, refactors, scripts, exploit tooling, harnesses, or skill utilities before writing implementation code. Applies when tests, reproducers, assertions, or verification can be written first; treat disposable spikes separately and convert them to tested code before claiming reliability."
license: MIT
compatibility: "Language-agnostic TDD workflow. Pair with language-specific testing skills for commands and framework details."
metadata:
  author: AeonDave
  version: "1.0"
---

# Test-Driven Development

Write the proof first. If the proof never failed, it may not prove anything.

## Activation

Use this for code that is meant to remain: features, bug fixes, refactors, test harnesses, scripts, offensive tooling, parsers, and skill utilities.

Disposable exploration is allowed only as a spike. Do not ship, commit, or claim reliability from spike code until behavior is captured by a test, reproducer, or explicit verification gate.

## RED-GREEN-REFACTOR

1. **RED**: write one minimal test or reproducer for desired behavior or the bug.
2. **Verify RED**: run it and confirm it fails for the expected reason.
3. **GREEN**: implement the smallest code that makes it pass.
4. **Verify GREEN**: run the focused check and relevant broader checks.
5. **REFACTOR**: clean structure while checks stay green.
6. **Repeat**: one behavior at a time.

## Good tests

- Test behavior, primitive, or contract rather than mock call trivia.
- Use clear names that describe expected behavior.
- Keep setup small enough that failure attribution is obvious.
- Cover error paths, trust boundaries, and edge inputs when they define the contract.

## Bug fixes

Before changing production code, create the smallest reproducer for the failure. For exploit or fuzzing work, preserve the crash input, seed, transcript, or packet sample and prove the fix against it.

## Stop signals

- Test passes before implementation: the test is wrong or behavior already exists.
- Test errors for setup reasons: fix the test until it fails for the intended reason.
- Test requires massive setup: the design may be too coupled; simplify the seam.
- You wrote code first: restart from a failing test or mark the earlier code as disposable spike material.

## Resources

Load on demand:

- `references/tdd-rationalizations.md` — common shortcuts, legitimate exceptions, and offensive-development adaptations.
