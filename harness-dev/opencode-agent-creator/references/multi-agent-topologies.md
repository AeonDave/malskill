# Choose an agent topology

| Shape | Use when | Implementation |
|---|---|---|
| One specialist | One bounded recurring question or permission boundary | Explicit `mode: subagent`; invoke via Task or `@`. |
| Supervisor and leaf workers | Several specialties or isolated results need central review | A primary with a Task roster; workers use `task: deny`. |
| Parallel workers | Subtasks are independent and their write sets do not overlap | Dispatch independent calls together; verify the whole batch before dependent work. |
| Nested workers | A worker has a real bounded need to delegate | Explicit depth limit and worker Task permissions; see [agent-config-reference.md](agent-config-reference.md#primary-selection-and-nesting). |

Keep coordination at one primary unless nested delegation removes a concrete bottleneck. Native Task creates child sessions; it is not a general peer-mailbox or shared-memory API. For worker-to-worker needs, return the missing input to the coordinator and resume the appropriate child with the answer.

For each worker, define the question, accepted result, relevant inputs, and file ownership. Workers share the workspace even when their conversations are separate. Serialize overlapping writes and resource-heavy checks.

Use a discovery worker when the target is unfamiliar or version-sensitive; skip a separate discovery stage for a small understood change. Pass paths to large context/artifact files instead of duplicating entire transcripts. Review outputs against acceptance criteria before dependent work.

Load [orchestrator-pattern.md](orchestrator-pattern.md) when writing the dispatch protocol. For asynchronous work, use its version-scoped background guidance; do not assume a third-party plugin's behavior is part of native Task.
