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

Verify APIs described as already available against the current source or dependency contract. Mark intended new interfaces as proposals and specify their required behavior. Reject unrelated infrastructure or tool choices that substitute for the requested outcome.

## Independent design review

Use for consequential designs whose ambiguity or hidden assumptions could cause expensive rework. Keep local, already specified changes on the normal implementation path.

1. Identify the design revision and repository state under review. Assign a read-only review using the requirements, constraints, design, and relevant source pointers. When fresh-context delegation is available, omit the brainstorming history and the author's defense of the design from the initial review. Preserve applicable host and repository instructions; fresh conversation context does not erase those instructions or guarantee unbiased judgment.
2. Ask the reviewer to restate the proposal and the existing system as the document describes them before critiquing it. Keep this reconstruction separate from source-verified facts; do not silently correct the document's claims while paraphrasing them. Compare that reading with the intended behavior. Repair missing or contradictory contracts in the artifact, rather than explaining them only in chat.
3. Check the design against the table above and current source evidence. Require a location, impact, evidence or counterexample, and the smallest correction or next check for each finding. Distinguish unsupported assumptions from demonstrated defects; a reviewer need not find a problem.
4. Resolve findings using `external-feedback-triage`. Check readiness by whether an implementer can proceed without inventing consequential behavior. Leave private helper names and other harmless implementation choices open.

Recheck affected parts after material revisions. Finish when blocking ambiguities are resolved and remaining risks or unchecked areas are explicit; avoid fixed round counts or repeated reviews with no new evidence. If independent context is unavailable, state that limit and perform the available review without labeling it independent. Review does not establish runtime correctness or add an approval gate to already authorized work.

## Source anchor

- [EGM comprehension reviewer](https://github.com/google/elephant-goldfish-model/blob/main/agents/comprehension.md) and [context-isolation limits](https://github.com/google/elephant-goldfish-model/blob/main/docs/harnesses.md#delegation).
