# Design Gates

Use this reference to review a design before turning it into tasks.

## Spec review checklist

| Category | Check |
|---|---|
| Completeness | No TODO, TBD, placeholders, or vague success criteria. |
| Consistency | Requirements do not contradict architecture or constraints. |
| Scope | One coherent deliverable; independent subsystems are split. |
| Safety | Authorized boundaries and destructive/noisy limits are explicit. |
| YAGNI | No unrelated hardening, abstractions, or nice-to-have features. |
| Testability | Validation can be run or inspected by a later worker. |

## When to split the design

Split into separate specs when each piece can be built, tested, reviewed, or authorized independently. Examples: recon pipeline vs exploit harness, parser library vs CLI, skill content vs installer script.

## Common design failures

- Starting with a favored tool instead of the operator goal.
- Combining research, implementation, and reporting in one vague task.
- Hiding authorization assumptions in examples.
- Treating “simple” as a reason to skip non-goals or validation.
- Adding broad refactors unrelated to the current objective.
