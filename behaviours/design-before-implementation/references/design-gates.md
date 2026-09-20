# Design Gates

Use when reviewing a substantial design before implementation or handoff.

| Check | Required evidence |
|---|---|
| Outcome | Observable success criteria and affected users or consumers. |
| Consistency | Requirements fit the proposed interfaces and current constraints. |
| Scope | Each proposed change contributes to the requested outcome. |
| Authorization | Consequential actions fit the permission already granted. |
| Dependencies | Shared state and ordering are explicit where they matter. |
| Validation | A later worker can check the result with available artifacts or commands. |

Resolve ambiguous commitments before depending on them. Record nonblocking unknowns with the decision they affect instead of demanding that every detail be known upfront.

Split work when pieces have independent acceptance or ownership. Keep tightly coupled implementation and its tests together when splitting would duplicate discovery.

Reject designs that invent local APIs, add unrelated infrastructure, or substitute a favored tool for the requested outcome.
