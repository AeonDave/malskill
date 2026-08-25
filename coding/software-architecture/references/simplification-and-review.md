# Simplification and Review

Use this reference after a feature, fix, or refactor is working, or when reviewing recently changed code. The goal is lower cognitive and maintenance cost with identical intended behavior, not a smaller diff at any price.

## Contents

- [Preservation contract](#preservation-contract)
- [Simplification loop](#simplification-loop)
- [Keep or remove an abstraction](#keep-or-remove-an-abstraction)
- [Clarity patterns](#clarity-patterns)
- [Review checklist](#review-checklist)

## Preservation contract

Before changing structure, identify the behavior that must remain stable:

- Public inputs, outputs, error types/messages where callers depend on them, side effects, ordering, retries, timing bounds, persistence, and compatibility.
- Security checks, authorization outcomes, audit events, telemetry relied on by operations, and resource cleanup.
- Tests, fixtures, snapshots, configuration, and undocumented behavior that consumers demonstrably rely on.

If behavior is unclear, add a characterization test or reproducer first. If the user requested a behavior change, separate it from simplification and label both in the plan and diff.

## Simplification loop

1. **Scope:** list files and recently changed sections. Do not widen the cleanup because adjacent code looks untidy.
2. **Baseline:** run the smallest relevant tests and checks. Record existing failures instead of attributing them to the review.
3. **Map behavior:** identify inputs, branches, state changes, external calls, and error paths.
4. **Remove:** delete dead code, duplicate transformations, speculative configuration, unused parameters, and abstractions with no consumer or boundary value.
5. **Flatten:** replace avoidable nesting and pass-through delegation with clear named steps and early exits. Preserve sequencing and cleanup semantics.
6. **Clarify:** rename by domain intent; make ownership, optionality, errors, and side effects visible in APIs and types where the language supports it.
7. **Re-check boundaries:** keep an abstraction when it protects a real invariant, volatile dependency, independent contract, security seam, or meaningful test isolation.
8. **Verify after each coherent change:** rerun focused tests, static checks, and relevant integration tests. Review the final diff for scope drift.

Do not optimize for a line count. A few explicit lines are simpler than a clever expression; a small amount of duplication can be simpler than coupling through a premature shared abstraction.

## Keep or remove an abstraction

Ask these questions in order:

1. Does this abstraction enforce an invariant or prevent an invalid state?
2. Does it isolate a dependency that is genuinely volatile, remote, expensive, or unavailable in tests?
3. Does it define a contract consumed by multiple independent implementations or modules?
4. Does it make a likely change local without hiding important behavior?
5. Can its purpose be stated in one domain-specific sentence?

If all answers are no, inline or remove it. If one is yes, keep it only as narrow as the reason requires. Re-evaluate abstractions after requirements stabilize; a future possibility is not a current boundary.

Keep a boundary even when it adds code if collapsing it would leak framework, storage, transport, security, or vendor decisions into business policy.

## Clarity patterns

Prefer:

- Domain names over `data`, `result`, `helper`, `common`, or unexplained abbreviations.
- One decision per conditional and named predicates for business rules.
- Early returns when they reduce nesting without hiding cleanup or transaction scope.
- Explicit branches or a `switch` for several cases instead of nested ternaries.
- Small cohesive functions, but no arbitrary maximum. Split when a reader must hold multiple responsibilities in mind.
- Explicit error contracts and context-preserving errors at boundaries.
- Local helpers for local policy; shared helpers only for stable, domain-neutral behavior.

Avoid:

- “Cleanups” that alter unrelated comments, formatting, public APIs, or behavior.
- Generic utility packages that accumulate unrelated policy.
- Boolean flags that make one function serve multiple workflows when separate named operations are clearer.
- Comments that narrate obvious syntax; retain comments that state an invariant, external constraint, or non-obvious trade-off.
- Catching and discarding errors, retrying without idempotency, or swallowing cancellation to make a path look simpler.

## Review checklist

### Behavior

- Do focused tests cover the changed behavior and important error paths?
- Did any output, error, ordering, retry, transaction, or authorization behavior change unintentionally?
- Are resource cleanup and cancellation still guaranteed on every path?

### Design

- Does each changed module have a clear owner and responsibility?
- Are dependencies and data ownership still pointed in the intended direction?
- Are ports, adapters, DTOs, and shared code justified by a real boundary?
- Is the simplest design that meets the current quality scenarios now in place?

### Maintainability

- Can a new contributor name the purpose of each changed abstraction?
- Are names specific enough to guide future changes?
- Is complexity reduced in the paths people must read, debug, and operate?
- Did the change remove speculative work without deleting useful safety checks?

### Verification

- Were formatter, compiler/type checker, linter, focused tests, broader relevant tests, and build checks run as applicable?
- Was the final diff reviewed for orthogonal edits and generated-file noise?
- Did documentation, ADRs, contracts, and tests remain aligned with the code?

If simplification makes verification harder, stop and restore the clearer seam. The result is not simpler if its correctness becomes harder to establish.
