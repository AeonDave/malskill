# Task dispatch and coordination

Baseline: [released Task source, v1.18.35](https://github.com/anomalyco/opencode/blob/v1.18.35/packages/opencode/src/tool/task.ts).

## Native call shape

```json
{
  "description": "Review authentication diff",
  "subagent_type": "code-reviewer",
  "prompt": "Review the named diff. Return actionable findings with file:line evidence. Do not edit."
}
```

Required: `description`, `subagent_type`, `prompt`. Optional: `task_id` resumes an existing child; `command` records the triggering command. `background` is exposed when the experimental background flag is enabled. There is no per-call model field; load [model-tiering.md](model-tiering.md) for model resolution.

Without `task_id`, Task creates a fresh child rather than copying the parent's transcript. The worker still has its agent prompt, project configuration/rules, tools, and workspace. With a valid prior `task_id`, it continues that child's history. Preserve returned IDs when follow-up work needs the child's earlier reasoning. An invalid/unavailable ID falls back to a new child in this release; verify the returned session identity if continuity matters. Do not reuse a task ID for a different worker role.

Foreground calls wait for a result. Treat errors, empty results, and a worker's missing-input report as unresolved work; narrow the packet or fix the failed capability instead of accepting an unsupported claim.

## Dispatch packet

Include only inputs that change the worker's action:

- Objective and one accepted deliverable.
- Target paths/artifacts and the relevant facts from the conversation.
- Existing authorization, constraints, allowed writes, and checks to run.
- Skills to load by exact name, when applicable.
- Evidence/output shape and any missing-input behavior.

For a resumed child, send the correction or additional input it needs; do not paste the parent's entire conversation. Carry user authorization forward rather than inserting a new approval gate for work already authorized.

## Coordinator workflow

1. Decompose only when independent roles or permission boundaries help.
2. Assign disjoint writes; dispatch independent work together.
3. Check each returned artifact and evidence against its acceptance criteria.
4. Resume the same child for corrections that depend on its context; create a fresh child for independent work.
5. Complete integration and checks before reporting the outcome. Summarize results, not raw transcripts.

Use [supervisor-template.md](../assets/supervisor-template.md). Leaf workers retain `task: deny`; intentional nesting follows the [depth/permission contract](agent-config-reference.md#primary-selection-and-nesting). `steps` limits iterations, not elapsed time, tokens, filesystem access, or the number of child calls.

## Experimental background work

In this release, `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` enables Task's `background: true`. It returns a running task ID immediately; completion/error is injected into the parent session. A call with the running task's ID can add context. Keep unrelated work independent and wait for completion notification; the runtime instructs the caller not to sleep, poll, or duplicate that work.

Workers share the workspace. Verify notification, cancellation, resumption, and job lifetime across host restarts before depending on background behavior. For plugin-provided delegation APIs, load [opencode-plugin-creator](../../opencode-plugin-creator/SKILL.md) and inspect the selected plugin's own contract.
