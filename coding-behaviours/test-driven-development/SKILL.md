---
name: test-driven-development
description: "Develop behavior through a failing test or reproducer, implementation, and refactoring. Use when test-first development is requested or a new behavior or bug fix benefits from an executable regression before implementation."
license: MIT
compatibility: "Language-agnostic TDD workflow. Pair with language-specific testing skills for commands and framework details."
metadata:
  author: AeonDave
  version: "1.1"
---

# Test-Driven Development

Make the intended behavior observable before implementing it, then use the check to guide a small complete change. A passing test supports the behavior it covers; it is not a proof of correctness.

## Choose the appropriate entry point

- For a new behavior or reproducible bug, use the failing-check loop below when practical. Follow explicit user and repository testing requirements.
- For a behavior-preserving refactor, establish a passing baseline and add characterization only for relevant uncovered behavior. Keep those checks green; do not manufacture a failure for behavior that should stay unchanged.
- For code already written, preserve it and assess the missing verification. Add meaningful checks; use an isolated pre-change baseline or controlled fault to test their sensitivity when useful. Do not discard work or restart implementation merely to recreate test-first history.
- For exploration, configuration, generated artifacts, or changes that do not benefit from a new automated test, choose the appropriate existing check, generator test, static validation, or reproducible manual procedure. State what remains unverified; do not describe tests written afterward as a test-first sequence.

For an urgent incident, use `systematic-debugging` to prioritize authorized mitigation and preserve evidence. Missing deterministic reproduction does not forbid investigation or recovery.

## RED-GREEN-REFACTOR

1. **Specify** one behavior and its observable outcome. Reuse a relevant existing check or failing artifact rather than creating a duplicate.
2. **RED**: write the smallest useful test/reproducer and run it. Confirm that failure represents the missing behavior or defect; distinguish an intentionally absent API from an unrelated import, fixture, or environment error.
3. **GREEN**: implement the smallest complete change that satisfies the behavior. Run the focused check and relevant neighboring cases; do not weaken assertions to make it pass.
4. **REFACTOR**: improve the affected structure while preserving the contract and keeping checks green. Use `software-architecture` for consequential design or simplification decisions.
5. **Continue and verify**: take the next behavior when needed and run applicable broader checks. Use `verification-before-completion` for required gates, evidence freshness, and completion claims.

## Diagnose an unexpected test result

- If a proposed regression already passes, check whether the behavior exists, the intended path ran, and the chosen input/assertion can detect the defect. A passing characterization test is expected.
- If setup fails, repair the relevant fixture or environment before treating the result as evidence about the behavior.
- If setup is excessive, inspect the test scope and existing seams before changing production APIs. Use `testing-reliability` for weak assertions, misleading doubles, fixture coupling, or flakes.

## Apply to security tooling

For parsers, exploit harnesses, or payload tooling, preserve the relevant input, seed, transcript, or artifact before changing code and turn it into a bounded local regression where practical. Use `testing-reliability` for what the assertion must establish and the language/domain testing skill for harness mechanics.

Use `software-guidelines` for patch scope and affected consumers. Language-specific testing skills own framework syntax and execution commands.
