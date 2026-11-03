# Testing Anti-Patterns

Use this reference during test review or flake triage.

## Mocking problems

| Anti-pattern | Risk | Replacement |
|---|---|---|
| Replace every collaborator without a test-specific reason | Tests mirror implementation and miss integration behavior | Keep practical real collaborators; replace dependencies where control or isolation serves the tested contract |
| Assert incidental internal calls | Brittle tests can pass while the outcome is wrong | Assert output, state, or a required boundary interaction; check integration separately when the claim depends on it |
| Fake omits a relevant side effect or error | False confidence | Model the contract needed by this test or use a real local collaborator; validate that contract against the real implementation where practical |
| Double installed on the wrong binding, instance, or lifetime | Real dependency still runs or the intended path is bypassed | Confirm what the exercised code resolves at runtime; use the language testing skill for patch semantics |

## Timing problems

For sleep-based synchronization or false readiness, load [systematic-debugging](../../systematic-debugging/SKILL.md), then its condition-based waiting reference. That reference owns completion signals, deadlines, and cancellation; file stability or a listening port alone does not establish application completion or readiness.

Choose fake clocks or controlled scheduling only when they exercise the mechanism the test claims to cover. Keep relevant integration coverage for timing or concurrency that the fake removes.

## Test-only production changes

Avoid expanding public behavior solely to inspect private state. Prefer existing dependency injection, local fixtures, or internal helpers where language conventions support them. A testability seam can be useful without another production caller; judge its contract and cost rather than requiring a speculative consumer. Use `software-architecture` if the change affects public boundaries or ownership.

## Flake triage

1. Preserve the failing command, test order/seed, environment, and relevant parallelism settings. Compare focused execution with the suite context; isolate one suspected difference at a time.
2. If order or shared state is suspected, replay the failing sequence and inspect fixture cleanup, background workers, and state ownership. Running every test alone cannot expose every interaction.
3. If repetition is needed, set a diagnostic budget and retain both successes and failures. Reruns or quarantine may contain disruption but do not establish a fix; retain the failure record and a tracked investigation when quarantining.
4. Correct the supported isolation, synchronization, assertion, or product defect. Change timeouts only when the measured operation and its intended bound justify it.

Use [pytest's flake guidance](https://docs.pytest.org/en/stable/explanation/flaky.html) for concrete examples of order-dependent state, overly strict assertions, and worker cleanup; apply the relevant framework's mechanics.

## Coverage traps

Coverage does not prove correctness. Add assertions for:

- security boundary behavior
- malformed/edge input
- error paths and cleanup
- privilege/authorization decisions
- concurrency invariants

## Mutation results

Use a focused mutation run when important behavior has weak test evidence or the repository already requires it. Start from a passing baseline, a supported tool, and a bounded set of changed or high-risk code; avoid making every small edit depend on a full mutation campaign.

| Finding | Action |
|---|---|
| Behavior-changing survivor | Identify the violated contract; add an input and observable assertion that distinguish the defect, then rerun the focused tests and mutant. |
| No coverage | Check whether the path is required. Exercise meaningful behavior, or remove code only after establishing that it is dead. |
| Equivalent mutant | Demonstrate why the mutation preserves behavior for valid inputs; document the limitation instead of inventing a test to reach a score. |
| Compile/runtime error or timeout | Inspect tool diagnostics and baseline behavior. Distinguish an invalid mutant, infrastructure failure, and mutation-induced hang before treating the result as test evidence. |

Prefer observable state, output, errors, and required side effects over assertions on private helpers. Keep documented exclusions narrow; do not change production semantics or remove useful code to satisfy a percentage. Mutation results reveal gaps for the chosen operators and scope, not proof of correctness.

## Source anchors

- [Mutant states and metrics — Stryker Mutator](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)
- [Equivalent mutants — Stryker Mutator](https://stryker-mutator.io/docs/mutation-testing-elements/equivalent-mutants/)
