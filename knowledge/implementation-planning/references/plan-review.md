# Plan Review

Use this before executing or delegating an implementation plan.

## Review categories

| Category | Blocking issues |
|---|---|
| Spec alignment | Missing requirement, scope creep, wrong target, wrong artifact. |
| Buildability | Steps too vague, missing paths, missing commands, undefined symbols. |
| Task boundaries | Tasks mutate the same files unpredictably or depend on hidden state. |
| Verification | No way to prove success, expected failure/pass state missing. |
| Safety | No scope/authorization/noise gate for offensive or destructive steps. |

## Calibration

Flag issues that would make a worker build the wrong thing, get stuck, or overstep scope. Do not block on style preferences, extra wording, or harmless formatting.

## Handoff checklist

- The first task can start without asking for conversation history.
- Every task has exact files or artifacts.
- Every task has a verification command or evidence check.
- Review checkpoints are placed before large dependent work continues.
- Failing baseline or missing dependency has an explicit stop path.
