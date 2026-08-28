# Subagent-Style Extensions

Pi core ships no built-in subagents. A "subagent" is a pattern you build as an extension: a tool that spawns child `pi` processes with isolated context and delegates a task to a named, markdown-defined agent. The official `subagent` example in the Pi repo is the canonical reference. Load this reference when building or tuning that kind of extension, or when writing the markdown agent files it consumes.

## Contents
- [Decision Rules](#decision-rules)
- [Extension Shape](#extension-shape)
- [Agent Definition Files](#agent-definition-files)
- [Discovery And Scope](#discovery-and-scope)
- [Context Isolation](#context-isolation)
- [Tool Modes](#tool-modes)
- [Model Routing](#model-routing)
- [Workflow Presets](#workflow-presets)
- [Design Rules](#design-rules)
- [Security](#security)
- [Validation](#validation)
- [Sources](#sources)

## Decision Rules

- Build a subagent tool when work benefits from an isolated context window, a narrower tool set, or a different model than the main session.
- Keep the main session as the supervisor. Do not let ordinary children spawn their own children unless an agent explicitly receives a `subagent`-style tool.
- Use a named markdown agent when a role, tool boundary, model choice, or output contract is stable across tasks. Use an inline task otherwise.
- Reuse the official subagent example as the baseline; implement only the fields and modes your extension actually needs.

## Extension Shape

Grounded in the official example (`registerTool` plus `exec`/child process):

1. Discover agents fresh on each call so users can edit them mid-session.
2. Register one tool exposing single/parallel/chain modes.
3. Spawn a child `pi` per task with the agent's system prompt, tools, and model.
4. Stream child tool calls and progress through `onUpdate`; pass `signal` so aborting the parent kills the children.
5. Return dense final output to the model (cap the size), and keep full detail in `details`.

Useful helpers from `@earendil-works/pi-coding-agent`: `parseFrontmatter`, `getAgentDir`, `CONFIG_DIR_NAME`.

## Agent Definition Files

Markdown with YAML frontmatter. Official minimal contract:

```md
---
name: scout
description: Fast codebase recon; returns compressed context
tools: read, grep, find, ls, bash
model: claude-haiku-4-5
---

You are a fast codebase scout. Return dense, decision-useful findings.
```

- `name` — required runtime name.
- `description` — required routing text; say exactly when to delegate here.
- `tools` — optional allowlist; accept a comma string (`read, bash`) or a YAML list. Omit to inherit the session's normal tools.
- `model` — optional; when omitted the child inherits the dispatching session's active model and thinking level.
- Body — the child system prompt.

An extension may define and honor extra frontmatter (thinking level, prompt mode, context mode, default reads). Only add a field if your loader reads it; otherwise it is inert.

## Discovery And Scope

| Scope | Path | Loads |
|---|---|---|
| User | `~/.pi/agent/agents/*.md` | Always |
| Project | `.pi/agents/*.md` | Only with `agentScope: "project"` or `"both"` |

- `agentScope`: `user` (default), `project`, or `both`. With `both`, a project agent overrides a same-named user agent.
- Prefer `getAgentDir()` to resolve the user agent directory; it honors `PI_CODING_AGENT_DIR`.

## Context Isolation

- Each child runs in a separate process with its own context window.
- Design axis: start the child from a clean session (independent review, scouting, second opinions that must not inherit parent bias) versus seed it with the current session branch (implementation or debugging that depends on the ongoing conversation). Choose per task; the official example uses isolated fresh children.

## Tool Modes

Modes exposed by the official example:

| Mode | Params | Use |
|---|---|---|
| Single | `{ agent, task }` | One agent, one task |
| Parallel | `{ tasks: [...] }` | Independent tasks with bounded concurrency (the example caps 8 tasks / 4 concurrent) |
| Chain | `{ chain: [...] }` | Sequential; pass prior output through a `{previous}` placeholder |

- Parallel: independent scouts, review lenses, competing approaches, non-overlapping legs.
- Chain: scout -> plan -> implement -> review, or enumerate -> test -> report.
- Do quick orientation and final synthesis in the parent, not a child.

## Model Routing

- Model availability is runtime state. Inspect with `pi --list-models [filter]`, or `ctx.modelRegistry` in code.
- Set a per-agent `model`, or omit it to inherit the parent model and thinking level.
- Express effort as a `:level` suffix on the model id (`provider/model:high`). Thinking levels: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`.
- Cheaper models and `:low` for scouting and formatting; `:medium` for normal implementation; `:high`/`:xhigh` for hard debugging, architecture, and adversarial review.

## Workflow Presets

- Package repeatable flows as prompt templates (`prompts/*.md`) that expand to slash commands and drive the subagent tool in sequence (for example `/implement` = scout -> planner -> worker).
- Prompt-template frontmatter: `description` (required for discovery), `argument-hint` (optional). The body expands arguments with `$1`, `$@` or `$ARGUMENTS`, and `${1:-default}`.

## Design Rules

- Write agent bodies for a cold child: restate every non-obvious constraint in the task, body, or default reads.
- Put "read-only" or "review-only" boundaries in both `tools` and prose.
- Keep writer tools out of reviewers and researchers.
- Do not expose the subagent tool to ordinary children; bound delegation depth.
- Return decision-useful sections: result, evidence, validation, risks.
- Prefer a clean child context for adversarial review; seed context only for implementation after an approved plan.

## Security

- Project-local agents (`.pi/agents/*.md`) are repo-controlled prompts that can drive file reads and bash. Treat them as executable influence.
- Default to user-only agents. Require project trust and confirm before running project agents in untrusted repos (the example gates this and exposes a `confirmProjectAgents` switch).
- Never inject secrets into child prompts unless the target model or provider is approved to receive them.
- Pass `signal` so aborting the parent terminates child processes.

## Validation

```bash
npm run typecheck
pi -e .
```

- Confirm agents appear in discovery from the expected scope.
- Confirm a same-named project agent overrides the user agent under `agentScope: "both"`.
- Confirm read-only agents cannot edit and writer agents make real edits.
- Confirm single, parallel, and chain modes behave and that Ctrl+C kills children.
- Confirm workflow prompts expand and run the intended sequence.

## Sources

- Pi extensions docs: https://pi.dev/docs/latest/extensions
- Pi skills docs: https://pi.dev/docs/latest/skills
- Pi prompt-template docs: https://pi.dev/docs/latest/prompt-templates
- Official subagent example: `packages/coding-agent/examples/extensions/subagent/`
