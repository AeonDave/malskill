# Claude Subagent Frontmatter Reference

Complete field reference for Claude Code subagents. A subagent is a Markdown file: YAML frontmatter between `---` fences, then the system-prompt body. Only `name` and `description` are required.

## Contents
- [Scopes, locations, and precedence](#scopes-locations-and-precedence)
- [Supported frontmatter fields](#supported-frontmatter-fields)
- [Model selection and resolution order](#model-selection-and-resolution-order)
- [Tool access and inheritance](#tool-access-and-inheritance)
- [Permission modes](#permission-modes)
- [Preloading skills](#preloading-skills)
- [Persistent memory](#persistent-memory)
- [MCP servers scoped to a subagent](#mcp-servers-scoped-to-a-subagent)
- [Hooks](#hooks)
- [What loads at startup (the cold-context contract)](#what-loads-at-startup-the-cold-context-contract)
- [Invoking subagents](#invoking-subagents)
- [Defining subagents via CLI](#defining-subagents-via-cli)

## Scopes, locations, and precedence

Store the `.md` file in one of these locations. On a name collision, the higher-priority scope wins.

| Location | Scope | Priority | Notes |
|---|---|---|---|
| Managed settings dir `.claude/agents/` | Organization-wide | 1 (highest) | Deployed by admins; overrides project/user |
| `--agents` CLI flag (JSON) | Current session only | 2 | Not saved to disk; good for testing |
| `.claude/agents/` | Current project | 3 | **Check into git** for team sharing |
| `~/.claude/agents/` | All your projects | 4 | Personal, cross-project |
| Plugin `agents/` dir | Where plugin enabled | 5 (lowest) | Distributed via plugins |

- Both `.claude/agents/` and `~/.claude/agents/` are scanned **recursively** — organize into subfolders (`agents/review/`, `agents/research/`) freely. Identity comes from the `name` field, not the path or filename.
- Keep `name` unique across the whole tree. Two files with the same `name` in one scope: one is silently kept, the other discarded.
- Plugin subfolders **do** become part of a scoped identifier: `agents/review/security.md` in plugin `my-plugin` registers as `my-plugin:review:security`.
- Plugin subagents **ignore** `hooks`, `mcpServers`, and `permissionMode` (security). Copy the file into `.claude/agents/` if you need them.

## Supported frontmatter fields

| Field | Required | Purpose |
|---|---|---|
| `name` | **Yes** | Unique identifier, lowercase letters and hyphens. Hooks receive it as `agent_type`. Filename need not match. |
| `description` | **Yes** | When Claude should delegate here. Third person, concrete triggers. The routing signal. |
| `tools` | No | Allowlist of tools the agent may use. **Omitted → inherits ALL tools.** Prefer `skills:` over listing `Skill` here. |
| `disallowedTools` | No | Denylist removed from the inherited or specified set. Applied before `tools`. |
| `model` | No | `sonnet` / `opus` / `haiku` / `fable`, a full model ID (e.g. `claude-opus-4-8`), or `inherit`. Default: `inherit`. |
| `permissionMode` | No | `default` / `acceptEdits` / `auto` / `dontAsk` / `bypassPermissions` / `plan`. Ignored for plugin subagents. |
| `maxTurns` | No | Max agentic turns before the subagent stops. |
| `skills` | No | Skills to **preload** (full content injected at startup). Subagent can still invoke other skills via the Skill tool. |
| `mcpServers` | No | MCP servers for this subagent: a string (reference an already-configured server) or an inline definition. Ignored for plugin subagents. |
| `hooks` | No | Lifecycle hooks scoped to this subagent. Ignored for plugin subagents. |
| `memory` | No | Persistent memory scope: `user` / `project` / `local`. Enables cross-session learning. |
| `background` | No | `true` → always run as a background task. Default `false`. |
| `effort` | No | `low` / `medium` / `high` / `xhigh` / `max` while active. Overrides session effort. |
| `isolation` | No | `worktree` → run in a temporary git worktree (isolated repo copy, auto-cleaned if unchanged). |
| `color` | No | `red` / `blue` / `green` / `yellow` / `purple` / `orange` / `pink` / `cyan` (UI accent). |
| `initialPrompt` | No | Auto-submitted first user turn when the agent runs as the **main** session (via `--agent`). |

## Model selection and resolution order

`model` accepts an alias (`sonnet`, `opus`, `haiku`, `fable`), a full ID (`claude-opus-4-8`, `claude-sonnet-4-6`), or `inherit`. Choose by job:

| Model | Use for |
|---|---|
| `haiku` | Fast, cheap, high-volume: codebase search, file discovery, log scanning, bulk summarizing. |
| `sonnet` | Balanced analysis: code review, debugging, data analysis, most specialists. |
| `opus` | Hardest reasoning: architecture, tricky root-cause, multi-constraint planning. |
| `inherit` (default) | Match the main session — when the agent's difficulty tracks the parent task. |

Claude Code resolves the effective model in this order (first wins):
1. `CLAUDE_CODE_SUBAGENT_MODEL` env var
2. the per-invocation `model` parameter Claude passes
3. the agent's `model` frontmatter
4. the main conversation's model

## Tool access and inheritance

- **Default (no `tools`):** inherits every internal and MCP tool the main conversation has. This is the most common mistake for "safe" agents — set a boundary explicitly.
- **Allowlist:** `tools: Read, Grep, Glob, Bash` — only these.
- **Denylist:** `disallowedTools: Write, Edit` — everything except these.
- **Both set:** `disallowedTools` is applied first, then `tools` resolves against what remains. A tool in both is removed.
- **Always unavailable to subagents** (UI/session-bound), even if listed: `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers`, and `ExitPlanMode` (unless `permissionMode: plan`).
- **Spawning other agents:** include `Agent` in `tools` to let a subagent spawn nested subagents; omit it (or add to `disallowedTools`) to forbid. For a main-thread agent (`--agent`), `Agent(worker, researcher)` is an allowlist of which types it may spawn.

Read-only pattern (reviewer/researcher): `tools: Read, Grep, Glob, Bash` (no `Write`/`Edit`). Fixer pattern (debugger): add `Edit`.

## Permission modes

`permissionMode` controls prompt handling. The agent inherits the parent's permission context and can override it, **except**: if the parent is `bypassPermissions` or `acceptEdits`, that takes precedence; if the parent is `auto`, the subagent inherits auto and its own `permissionMode` is ignored.

| Mode | Behavior |
|---|---|
| `default` | Standard permission prompts. |
| `acceptEdits` | Auto-accept edits + common fs commands within the working dir. |
| `auto` | Background classifier reviews commands and protected-dir writes. |
| `dontAsk` | Auto-deny prompts (explicitly allowed tools still work). |
| `bypassPermissions` | Skip prompts. Use with caution — can write to `.git`, `.claude`, etc. |
| `plan` | Read-only exploration (plan mode). |

## Preloading skills

```yaml
skills:
  - api-conventions
  - error-handling-patterns
```

The **full content** of each listed skill is injected at startup — the reliable way to give a cold subagent domain knowledge it must have immediately. This controls what is *preloaded*, not what is *accessible*: without it, the subagent can still discover and invoke project/user/plugin skills through the Skill tool. You cannot preload a skill marked `disable-model-invocation: true`; missing/disabled skills are skipped with a debug-log warning.

## Persistent memory

```yaml
memory: project
```

Gives the agent a directory that survives across conversations; its system prompt gains read/write instructions plus the first 200 lines / 25KB of `MEMORY.md`. Read/Write/Edit are auto-enabled for memory management.

| Scope | Location | Use when |
|---|---|---|
| `user` | `~/.claude/agent-memory/<name>/` | learnings apply across all projects |
| `project` | `.claude/agent-memory/<name>/` | project-specific, shareable via git (**recommended default**) |
| `local` | `.claude/agent-memory-local/<name>/` | project-specific, not checked in |

Reinforce in the body: "Update your agent memory as you discover codepaths, patterns, and key decisions."

## MCP servers scoped to a subagent

```yaml
mcpServers:
  # inline definition — connected only while this subagent runs
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
  # reference an already-configured server by name
  - github
```

Inline servers use the same schema as `.mcp.json` (`stdio`/`http`/`sse`/`ws`). Defining a server here instead of in `.mcp.json` keeps its tool descriptions out of the main conversation's context — the subagent gets the tools, the parent does not.

## Hooks

Scope lifecycle hooks to the agent. Common events: `PreToolUse`, `PostToolUse`, `Stop` (becomes `SubagentStop` at runtime).

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
```

Use a `PreToolUse` hook (exit code 2 to block) for finer control than `tools` gives — e.g. allow `Bash` but block SQL writes. On Windows, write the script in PowerShell and add `shell: powershell` to the hook entry.

## What loads at startup (the cold-context contract)

A non-fork subagent's initial context contains **only**:
- **System prompt** — the agent's own body + environment details (NOT the full Claude Code system prompt).
- **Task message** — the one-shot delegation prompt Claude writes at hand-off.
- **CLAUDE.md + memory hierarchy** — `~/.claude/CLAUDE.md`, project rules, `CLAUDE.local.md`, managed policy.
- **Git status** — a snapshot from the start of the parent session.
- **Preloaded skills** — full content of anything in `skills:`.

It does **not** see the conversation history, files Claude already read, or skills already invoked. The built-in `Explore` and `Plan` agents additionally skip `CLAUDE.md` and git status. Consequence: bake every must-have fact into the body, the `skills:`, or the delegation prompt.

A **fork** is the exception — it inherits the full conversation, system prompt, tools, and model of the main session. Use a fork (not a named subagent) when a side task needs all the existing context and re-briefing would be wasteful.

## Invoking subagents

- **Automatic delegation** — Claude reads each `description` and delegates when a task matches. "Use proactively" / "use immediately after X" encourages it.
- **Natural language** — name it: "Use the test-runner subagent to fix failing tests."
- **`@`-mention** — `@agent-code-reviewer` (or pick from the typeahead) guarantees that agent runs for one task.
- **Whole session** — `claude --agent code-reviewer`, or set `"agent": "code-reviewer"` in `.claude/settings.json`. The agent's prompt replaces the default system prompt for the session.
- **Disable one** — add `"deny": ["Agent(Explore)"]` under `permissions` in settings, or `--disallowedTools "Agent(Explore)"`.

## Defining subagents via CLI

For session-only agents (testing/automation), pass JSON to `--agents`. Same fields as frontmatter, but the system prompt goes in `prompt` (not a body):

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

On Windows PowerShell, wrap the JSON in a single-quoted here-string (`@'` … `'@`).
