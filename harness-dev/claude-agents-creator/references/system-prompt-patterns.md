# Agent Prompts and Hand-offs

## Description

Name the worker's job and the situation that should trigger it. Keep the description short; workflow details belong in the body. Use a proactivity cue only when automatic delegation is intended, then test it with natural requests and near misses.

| Intended worker | Description |
|---|---|
| Reviewer | Reviews a supplied change set for defects. Use after implementation changes. |
| Researcher | Maps the code paths involved in a requested feature without editing files. |
| Debugger | Reproduces a reported failure, identifies its cause, and verifies a focused correction. |
| Test runner | Runs the requested tests and returns failures with relevant code references. |

Do not promise automatic routing from wording alone. Explicit naming is appropriate for a worker that should run only on request.

## Body

Include only what changes execution:

- Role and bounded responsibility.
- Required inputs and where to obtain them with the granted tools.
- Essential ordering when failure or data loss depends on it.
- Completion criteria and evidence to return.
- Actual capability constraints and how to report missing inputs or blocked work.

A reviewer with only `Read, Grep, Glob` cannot run `git diff`. Supply the diff in the delegation message or let it review specified files; add an execution tool only when that capability is required. Do not make an optional input a mandatory approval stop.

Keep open-ended analysis flexible. Use exact steps for fragile operations, with verification appropriate to the change. Avoid copying ordinary coding advice into every agent.

## Delegation brief

For a named worker, provide task-specific facts in the hand-off: objective, files or supplied diff, required revision, constraints, observations already established, and expected result. Put reusable methodology in preloaded skills and stable repository conventions in the body.

Choose the [context mode](frontmatter-reference.md#context-and-execution) explicitly when the side task must reuse conversation history. If the worker uses `omitClaudeMd`, restate any repository rule it still needs. For a worktree worker, verify that its base and inputs include the changes to inspect.

## Return contract

| Worker | Useful result |
|---|---|
| Reviewer | Prioritized defects with file:line, impact, and a concrete correction; say when no actionable defect was found. |
| Researcher | Relevant files, control/data flow, change seams, and unresolved questions, with source references. |
| Debugger | Reproduction, cause, correction, and fresh verification; separate observed evidence from hypotheses. |
| Test runner | Failing test names, errors, relevant code locations, and a short total; distinguish environment failure from a test failure. |

Adapt the [reviewer](../assets/examples/code-reviewer.md), [researcher](../assets/examples/safe-researcher.md), [debugger](../assets/examples/debugger.md), or [test runner](../assets/examples/test-runner.md) instead of maintaining duplicate example bodies here.

## Coordinator

Give each specialist a bounded task and return contract. A main-session coordinator can restrict spawn types with `Agent(worker, researcher)`; a nested subagent does not enforce that type list. Configure and test capability boundaries using the [frontmatter reference](frontmatter-reference.md#effective-tools-and-permissions).

Pass each worker the facts it needs and synthesize its evidence. Wait for completion notifications before using a background result. Resume the existing worker when its history matters; start a new one for an independent task.
