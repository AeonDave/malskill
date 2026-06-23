# Custom Subagent Agents

Use this when creating, reviewing, or packaging markdown agents for Pi subagent extensions.

## Contents
- [Decision Rules](#decision-rules)
- [Locations and Precedence](#locations-and-precedence)
- [Agent File Contract](#agent-file-contract)
- [Supervisor Pattern](#supervisor-pattern)
- [Context Selection](#context-selection)
- [Chains and Fanout](#chains-and-fanout)
- [Packaging Agents](#packaging-agents)
- [Extension Differences](#extension-differences)
- [Security Checks](#security-checks)
- [Validation](#validation)
- [Sources](#sources)

## Decision Rules

- Pi core does not ship built-in subagents. Treat agents as resources consumed by an installed subagent extension.
- Default to `nicobailon/pi-subagents` when `npm:pi-subagents` is installed. It supports named agents, builtins, chains, background runs, fork context, package agents, overrides, acceptance gates, and optional intercom.
- Use `pi-fork` for same-persona branch-aware investigation that should inherit the active session. It does not read markdown agent files.
- Keep the main Pi session as supervisor unless the user explicitly wants a child that can spawn children.
- Use a custom agent when a reusable role, tool boundary, model choice, context mode, or output contract is stable across tasks.
- Use `agentOverrides` for small builtin tweaks. Create a markdown agent with the same runtime name when the role changes substantially.

## Locations and Precedence

For `nicobailon/pi-subagents`, discovery is recursive.

| Scope | Path | Use |
|---|---|---|
| Project | `.pi/agents/**/*.md` | Repo-specific team agents; highest normal priority. |
| Project legacy | `.agents/**/*.md` | Legacy project agents; skip `.agents/skills`. |
| User | `~/.pi/agent/agents/**/*.md` | Personal global agents. |
| User legacy | `~/.agents/**/*.md` | Personal global agents outside Pi state. |
| Package | paths from package manifest | Distributable reusable agents. |
| Builtin | extension bundle | Lowest priority. |

Collision rules:
- Project beats user.
- User/project agents beat package and builtin agents.
- A same-named user or project agent overrides a builtin.
- Package names can namespace runtime names. Use this for reusable bundles that should not collide with common names.

Official Pi example behavior is narrower:
- User agents: `~/.pi/agent/agents/*.md`.
- Project agents: nearest `.pi/agents/*.md`.
- Default `agentScope` is `user`; project agents load only with `agentScope: "project"` or `"both"`.

## Agent File Contract

Minimum `nicobailon/pi-subagents` agent:

```md
---
name: security-reviewer
description: Reviews code changes for concrete security risks with evidence
tools: read, grep, find, ls, bash
thinking: high
systemPromptMode: replace
inheritProjectContext: true
inheritSkills: false
defaultContext: fresh
---

You are a security review subagent.

When invoked:
1. Inspect the assigned diff, files, or plan.
2. Verify findings against code, tests, or documented behavior.
3. Return only actionable findings with evidence.

Output:
- Blocker: issue, evidence, required fix
- Warning: issue, evidence, suggested fix
- Clear: what was checked when no issues are found
```

Core fields for `nicobailon/pi-subagents`:

| Field | Use |
|---|---|
| `name` | Required runtime name. Lowercase hyphenated names work best. |
| `package` | Optional namespace. Runtime name becomes `<package>.<name>`. |
| `description` | Required routing text. Say exactly when to use the agent. |
| `tools` | Comma-separated tool allowlist. Omit only when the agent should inherit broadly. Use `mcp:<tool>` for direct MCP tools. |
| `model` | Optional `provider/model` override. Prefer settings overrides for builtins. |
| `fallbackModels` | Comma-separated fallback model IDs. |
| `thinking` | `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. |
| `systemPromptMode` | `replace` for a specialist prompt; `append` for a parent-like delegate. |
| `inheritProjectContext` | `true` to keep `AGENTS.md`/`CLAUDE.md` style project context. |
| `inheritSkills` | `true` only when the child should see the parent skill catalog. |
| `skills` / `skill` | Comma-separated skills to inject. Avoid injecting the orchestration skill into ordinary children. |
| `defaultContext` | `fresh` or `fork`. Explicit launch `context` wins. |
| `defaultReads` | Comma-separated files the run should read first, such as `context.md, plan.md`. |
| `defaultProgress` | `true` to maintain progress when workflows expect it. |
| `output` | Default output path for large or reusable child results. |
| `extensions` | Comma-separated extension sources loaded in child processes. |
| `subagentOnlyExtensions` | Extensions available only to subagent children. |
| `interactive` | `true` for agents intended to use interactive clarify/UI behavior. |
| `maxSubagentDepth` | Tighten nested delegation depth for agents with `tools: subagent`. |
| `completionGuard` | `false` disables completion guard behavior when supported. |

Prompt body shape:

```md
You are <role>.

When invoked:
1. <first concrete action>
2. <core work>
3. <deliverable>

Rules:
- <tool boundary>
- <scope boundary>
- <when to escalate>

Output:
<exact format returned to parent>
```

Design rules:
- Write the body for a cold child. Restate every non-obvious constraint in the delegated task, body, skill, or default reads.
- Put "review-only", "read-only", or "single writer thread" boundaries in both `tools` and prose.
- Do not let every agent see `subagent`. Only fanout/coordinator agents should include it.
- Prefer lowercase Pi tool names: `read`, `grep`, `find`, `ls`, `bash`, `edit`, `write`, `subagent`, `intercom`, `contact_supervisor`.
- Use `systemPromptMode: replace` for specialists. Use `append` only for a child that should act like the parent plus extra instructions.

## Supervisor Pattern

Put supervisor behavior in the parent session's instruction files, not in a default child.

Good global supervisor file:

```text
~/.pi/agent/AGENTS.md
```

Project-specific supervisor file:

```text
<repo>/AGENTS.md
```

Supervisor rules:

```md
# Pi Supervisor Rules

You are the supervisor. Keep ownership of planning, risk control, approvals, and final synthesis.

Use subagents for bounded specialist work:
- scout for local code reconnaissance
- researcher for current external facts with sources
- planner for read-only implementation plans
- worker for approved implementation
- reviewer or security-reviewer for independent review
- oracle for risky decision checks before editing

Use `context: "fork"` when the child needs the current conversation and repo state.
Use `context: "fresh"` for independent review, scouting, and second opinions.

Default implementation loop:
clarify -> planner -> worker -> fresh reviewers -> worker -> final synthesis

Do not let children spawn children unless the assigned agent is a controlled fanout agent.
```

Create a child supervisor only for bounded fanout:

```md
---
name: supervisor-fanout
description: Coordinates one bounded parallel subagent pass and returns a synthesized handoff
tools: read, grep, find, ls, bash, subagent
thinking: high
systemPromptMode: replace
inheritProjectContext: true
inheritSkills: false
defaultContext: fork
maxSubagentDepth: 1
---

You coordinate one bounded fanout pass.

Rules:
- Spawn only the specific child roles needed for the assigned task.
- Never create open-ended recursive delegation.
- Prefer fresh reviewers and forked planners/workers only when context matters.
- Return one synthesized answer with child result IDs, decisions, and next action.
```

## Context Selection

Use fresh context for:
- independent code review
- security review
- lightweight scouting
- external research
- second opinions that should not inherit parent assumptions

Use fork context for:
- oracle checks over current decisions
- implementation workers executing an approved plan
- debugging that depends on the current conversation
- review of a branch state built up in the parent

`nicobailon/pi-subagents` behavior:
- `context: "fork"` creates a real branched session from the parent leaf.
- If any requested agent has `defaultContext: fork` and the call omits `context`, the invocation uses forked context.
- `context: "fork"` fails fast when the parent session cannot be persisted or branched; it should not silently downgrade.

`pi-fork` behavior:
- The child receives the active session branch and a final task message.
- It does not apply a custom agent markdown persona.
- Use it for dense `Result`, `Output`, `Evidence`, `Learnings` reports from the same persona/context.

## Chains and Fanout

Use slash commands for manual workflows:

```text
/run security-reviewer "Review the current diff"
/run worker "Implement the approved plan" --fork
/parallel security-reviewer "review for auth bugs" -> reviewer "review for tests"
/chain scout "scan auth flow" -> planner "plan the change from {previous}" -> worker
```

Use tool calls from extensions or parent agent reasoning:

```ts
subagent({
  agent: "security-reviewer",
  task: "Review the current diff for concrete exploitable risks.",
  context: "fresh",
  acceptance: "attested",
});
```

```ts
subagent({
  tasks: [
    { agent: "security-reviewer", task: "Review auth and secrets handling." },
    { agent: "reviewer", task: "Review tests and regression risk." }
  ],
  context: "fresh",
  concurrency: 2,
});
```

Use `.chain.md` for reusable local or packaged workflows:

```md
---
name: implement-and-review
description: Implement an approved plan, review it, then apply selected fixes
---

## worker
output: implementation.md
progress: true

Implement the approved plan with minimal edits.

## reviewer
reads: implementation.md
output: review.md

Review the implementation for correctness, tests, and scope control.

## worker
reads: review.md

Apply only the review fixes that are clearly required.
```

Use JSON chains when you need parallel groups, worktrees, structured output, or acceptance gates.

## Packaging Agents

Package agents when they should install with `pi install`.

Minimal package:

```json
{
  "name": "my-pi-agent-pack",
  "type": "module",
  "keywords": ["pi-package"],
  "pi": {
    "subagents": {
      "agents": ["./agents"],
      "chains": ["./chains"]
    }
  },
  "pi-subagents": {
    "agents": ["./agents"],
    "chains": ["./chains"]
  }
}
```

Use both `pi.subagents` and `pi-subagents` when targeting mixed installed versions. Keep paths relative and inside the package.

Recommended layout:

```text
my-pi-agent-pack/
+-- package.json
+-- agents/
|   +-- security-reviewer.md
|   +-- implementation-worker.md
+-- chains/
    +-- implement-and-review.chain.md
```

Do not package workstation-specific absolute paths, usernames, provider API keys, or local model names unless the package is private and documented.

## Extension Differences

`nicobailon/pi-subagents`:
- Tool name: `subagent`.
- Single call uses `{ agent, task }`.
- Management actions include `list`, `get`, `create`, `update`, `delete`, `status`, `interrupt`, `resume`, `append-step`, `doctor`.
- Supports project/user/package/builtin agents, recursive discovery, chains, background runs, fork context, worktrees, intercom bridge, acceptance gates, and builtin `agentOverrides`.
- Package manifests can expose agents through `pi.subagents.agents` or `pi-subagents.agents`.

Official Pi example extension:
- Tool name: `subagent`.
- Single call uses `{ agent, task }`.
- Supports user/project markdown agents with `name`, `description`, `tools`, `model`, and body prompt.
- Loads project agents only when `agentScope` enables them.
- Good base for building a small custom extension, not a complete product.

`tintinweb/pi-subagents`:
- Tool name: `Agent`.
- Spawn call uses `{ subagent_type, prompt, description }`.
- Custom agent filename is the agent type; frontmatter `name` is not required in examples.
- Fields include `display_name`, `tools`, `extensions`, `exclude_extensions`, `skills`, `memory`, `disallowed_tools`, `isolation`, `model`, `thinking`, `max_turns`, `prompt_mode`, `inherit_context`, `run_in_background`, `isolated`, `enabled`.

`@gotgenes/pi-subagents`:
- Tool name: `subagent`.
- Spawn call uses `{ subagent_type, prompt, description }`.
- Focused in-process core with typed service API.
- Removed some upstream fields; worktree isolation and permission policy live in companion packages.
- Use `permission:` with `@gotgenes/pi-permission-system` instead of old `disallowed_tools`.

`pi-fork`:
- Tool name: `fork`.
- Call uses `{ task, effort? }`.
- No markdown agents, no persona registry.
- Configure effort profiles, child extension loading, offline mode, environment, and cost footer under `pi-fork` settings.

## Security Checks

Before creating or enabling project-local agents:
- Confirm the repo is trusted. Agent files are prompt/code-execution influence.
- Keep writer tools out of reviewers and researchers.
- Do not expose `subagent` to ordinary children.
- Prefer `context: fresh` for adversarial review to reduce inherited bias.
- Prefer `context: fork` for implementation only after the parent has a clear approved plan.
- Use `worktree: true` for parallel writer agents in the same repo.
- Add `maxSubagentDepth` to any fanout agent.
- Do not enable project agents globally for untrusted repos.
- Keep package agent names namespaced when publishing.
- Install `pi-intercom` only when live child-to-parent decisions are needed; otherwise avoid extra coordination surface.

## Validation

Validate custom agents by running:

```text
/subagents-doctor
Show me the available subagents.
/run security-reviewer "Review the current diff"
```

Check behavior:
- The agent appears in discovery with the expected source.
- A same-named project agent overrides the user/builtin agent.
- Read-only agents cannot edit files.
- Writer agents make actual edits instead of returning patch prose.
- Fresh reviewers do not depend on parent-only context.
- Forked workers fail clearly if no persisted parent session exists.
- Background runs can be inspected with `subagent({ action: "status" })`.

For packaged agents:
- Install from a local path with `pi install ./my-pi-agent-pack`.
- Confirm package agents appear below user/project overrides.
- Confirm `.chain.md` or `.chain.json` workflows parse and run.

## Sources

- Official Pi extensions documentation: `https://pi.dev/docs/latest/extensions`
- Official Pi subagent example source: `packages/coding-agent/examples/extensions/subagent/`
- `nicobailon/pi-subagents`: `https://github.com/nicobailon/pi-subagents`
- `tintinweb/pi-subagents`: `https://github.com/tintinweb/pi-subagents`
- `gotgenes/pi-packages` / `@gotgenes/pi-subagents`: `https://github.com/gotgenes/pi-packages`
- `elpapi42/pi-fork`: `https://github.com/elpapi42/pi-fork`
