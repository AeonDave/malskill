---
name: claude-agents-creator
description: "Create or revise Claude Code subagents or Claude Managed Agents, including definitions, delegation, permissions, and API sessions."
license: MIT
compatibility: "Claude Code Markdown subagents; reference baseline 2.1.293. Managed Agents use the separate Claude API beta contract."
metadata:
  author: AeonDave
  version: "1.1"
---

# Claude Agents Creator

Create a focused worker with a concrete trigger, capability boundary, and usable result. Default to a project-scoped Claude Code subagent for repository work; use Managed Agents when an application needs the hosted API harness.

For repository instructions use `agent-md-creator`; for reusable Agent Skills use `skill-creator`; for OpenCode workers use `opencode-agent-creator`.

## Build the definition

1. Establish the host, installed version, scope, task, and completion signal. Use an existing built-in worker when it already fits. Derive routine choices from the request; ask only for missing information that changes the result.
2. Give the worker one responsibility. Put the concrete delegation trigger in a short `description`; put workflow and output requirements in the body.
3. Choose project `.claude/agents/`, personal `~/.claude/agents/`, or plugin `agents/`. Keep identities unique; check collision precedence and plugin restrictions in [references/frontmatter-reference.md](references/frontmatter-reference.md).
4. Set the tools the work requires. For a reviewer that must not write, start with `Read, Grep, Glob`; shell and MCP access can permit writes, and persistent memory can add write tools. A prose boundary alone does not restrict capabilities.
5. Choose an available model alias or ID. Set `model: inherit` when matching the parent is intended; an omitted field can resolve through other model settings. Add skills, memory, MCP, hooks, or isolation only when the task needs them.
6. Write the body: role, required inputs, essential steps, completion criteria, and returned evidence. Keep stable conventions in the body or preloaded skills; pass the current task's files, constraints, and observations in the delegation message.

```markdown
---
name: change-reviewer
description: Reviews a supplied change set and reports defects with file references. Use after implementation changes.
tools: Read, Grep, Glob
model: inherit
---

Review the supplied diff and affected files. Report defects with file:line,
impact, and a concrete correction. If no diff was supplied, name the missing
input and inspect the target files without invoking a shell. Do not edit files.
```

## Context and delegation

A named subagent normally starts without the parent's conversation or previously read files. Preloaded `skills:` supply full skill content. An explicit conversation fork inherits the conversation; a skill's `context: fork` still starts a separate subagent without that history. Load the [frontmatter reference](references/frontmatter-reference.md#context-and-execution) when choosing between these modes, nested delegation, or worktree isolation.

## Verify before handing back

- Check YAML, required identity/description, supported field spelling, available tools/model, and the intended discovery scope.
- Parse frontmatter with a strict YAML parser and check required fields. Run `claude plugin validate <path-to-agents-dir>` for additional component lint; use a directory named `agents`. Its success does not establish valid YAML, routing, or effective permissions.
- Run a representative task and a plausible near miss; inspect the actual model, tool calls, result, and any partial completion. Name runtime checks that were not executed.

Load [references/triggering-and-testing.md](references/triggering-and-testing.md) when checking discovery, delegation, capability boundaries, or reload behavior.

## Load when needed

- [references/frontmatter-reference.md](references/frontmatter-reference.md): load when setting fields, permissions, model precedence, context, MCP, hooks, or CLI definitions.
- [references/system-prompt-patterns.md](references/system-prompt-patterns.md): load when designing the body, delegation brief, or coordinator hand-off.
- [references/managed-agents.md](references/managed-agents.md): load for hosted API agents, versioned sessions, events, or environment configuration.
- [assets/agent-template.md](assets/agent-template.md): adapt when creating a Markdown definition.
- [assets/examples/code-reviewer.md](assets/examples/code-reviewer.md), [debugger.md](assets/examples/debugger.md), [safe-researcher.md](assets/examples/safe-researcher.md), [test-runner.md](assets/examples/test-runner.md): load the example matching the requested worker.
