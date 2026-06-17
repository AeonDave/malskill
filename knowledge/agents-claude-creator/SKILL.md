---
name: agents-claude-creator
description: "Design, build, and tune Claude agents — primarily Claude Code subagents (the Markdown + YAML files under .claude/agents/ or ~/.claude/agents/ that Claude delegates to), and also Claude Managed Agents (the cloud agent harness on the API). Use when asked to create a Claude agent or subagent, write agent frontmatter (name, description, tools, model, skills, permissionMode, hooks, memory), design a focused reviewer/debugger/researcher agent, scope tool access, route work to a cheaper model, build a team of delegating agents, or fix an agent that never triggers or sees the wrong context. Not for AGENTS.md / CLAUDE.md instruction files (use agent-md-creator), portable Agent Skills (use skill-creator), or OpenCode agents (use opencode-agent-creator)."
license: MIT
compatibility: "Claude Code subagents (.claude/agents/ and ~/.claude/agents/, *.md). Managed Agents target the Claude API (managed-agents beta). Frontmatter validated against the current Claude Code subagent spec."
metadata:
  author: AeonDave
  version: "1.0"
---

# Claude Agent Creator

Build precise, focused, production-grade **Claude agents** without re-researching the platform. The default product is a **Claude Code subagent**: a Markdown file with YAML frontmatter plus a system-prompt body, stored under `.claude/agents/` (project) or `~/.claude/agents/` (personal), that Claude **automatically delegates to** when a task matches its `description`. The subagent runs in its **own fresh context window**, with its own tools and model, and returns only a summary.

> Scope: this skill creates the agents that *do work*. For repo instruction files (`AGENTS.md`/`CLAUDE.md`) use `agent-md-creator`; for portable Agent Skills use `skill-creator`; for OpenCode agents use `opencode-agent-creator`. A subagent often *preloads* a Skill to get its methodology — the two compose via the `skills:` field. For a cloud/programmatic agent on the Claude API, see [references/managed-agents.md](references/managed-agents.md).

## The five things that define an agent

Internalize this — every decision below maps to one of these:

1. **Identity** — `name` (lowercase-hyphens; how Claude and `@`-mentions address it).
2. **Routing** — `description` (third person; the trigger that makes Claude delegate).
3. **Capability boundary** — `tools` / `disallowedTools` / `mcpServers` / `skills` (what it can touch).
4. **Brain** — `model` (cost vs. capability: `haiku` / `sonnet` / `opus` / `inherit`).
5. **Behavior** — the Markdown body (the system prompt: role, workflow, output contract).

## The one constraint that shapes every prompt

**A subagent starts cold.** It does **not** see the conversation history, the files Claude already read, or the skills already invoked. Its entire world at startup is: its own system-prompt body, the one-shot delegation message Claude writes, the `CLAUDE.md` hierarchy, a git-status snapshot, and any `skills:` you preload. **Any context the agent needs must be in the body, in the `description`, preloaded as a skill, or restated in the task you delegate** — otherwise it does not cross. (The built-in `Explore` and `Plan` agents skip even `CLAUDE.md`.) Design as if briefing a brand-new contractor who can read the repo but was in none of your meetings.

## Workflow

### 1. Is a subagent even the right tool?

| Want | Use |
|---|---|
| Reusable behavior in the **main** context, frequent back-and-forth | a **Skill** (`skill-creator`) — not a subagent |
| Isolate verbose/throwaway work (tests, logs, wide search) so it never floods main context | **subagent** |
| Enforce a tool/permission boundary on a sub-task | **subagent** |
| A repeated, well-defined worker you keep re-spawning with the same instructions | **subagent** |
| Long-running / async / cloud-sandboxed autonomous task on the API | **Managed Agent** ([reference](references/managed-agents.md)) |

Do **not** recreate the built-ins: `Explore` (read-only codebase search, Haiku), `Plan` (read-only research), `general-purpose` (full tools). Create a custom subagent only when a focused role, tool boundary, or model choice beats those.

### 2. Scope to one responsibility

One agent, one bounded job, one deliverable, one clear hand-off. If you can't state its success signal in a sentence, split it. Single-responsibility agents route more reliably (the `description` stays sharp) and stay debuggable.

**Infer; don't interrogate.** Derive the role, tools, and model from the request plus sensible defaults, **state the assumptions you made**, and build. Ask the user only when a choice genuinely changes the build and can't be inferred (e.g. project vs. personal scope when it matters, or a required secret). A one-line assumption the user can correct beats a questionnaire.

### 3. Choose scope (location) and name

| Location | Scope | When |
|---|---|---|
| `.claude/agents/` | this project (check into git) | team-shared, repo-specific agents — **default for repo work** |
| `~/.claude/agents/` | all your projects | personal, cross-project agents |
| plugin `agents/` | where the plugin is enabled | distribution to others |

Higher-priority scope wins on name collisions (managed → CLI `--agents` → project → user → plugin). Identity comes from the `name` field, **not** the filename; keep `name` unique across the tree. Subfolders are allowed for organization and don't change the name.

### 4. Write the frontmatter (least privilege, right brain)

Minimum viable agent — only `name` and `description` are required:

```markdown
---
name: code-reviewer
description: Expert code-review specialist. Proactively reviews changes for quality, security, and maintainability. Use immediately after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: inherit
---
```

- **`description` is the router.** Write it in **third person**, name the concrete trigger, and state what it does. Add **"use proactively"** / **"use immediately after X"** when you want Claude to delegate without being asked. Vague (`Helps with code`) → never triggers. (Full guidance + good/bad examples: [references/system-prompt-patterns.md](references/system-prompt-patterns.md).)
- **Tools = least privilege.** **Omitting `tools` inherits ALL tools** — rarely what you want. Use an allowlist (`tools: Read, Grep, Glob`) or a denylist (`disallowedTools: Write, Edit`). A read-only reviewer/researcher must **exclude `Write` and `Edit`**; a fixer needs `Edit`.
- **Model = cost routing.** `haiku` for fast/cheap/bulk search & summarizing; `sonnet` for balanced analysis; `opus` for hard reasoning; `inherit` (default) to match the main session. Route cheap work to cheap models.
- **`skills:`** preloads the *full content* of named skills into the agent at startup — the cleanest way to hand a cold agent your methodology/conventions.
- Optional dials: `memory` (cross-session learning), `permissionMode`, `mcpServers`, `hooks`, `color`, `effort`, `isolation: worktree`. Every field, precedence, and model-resolution order: [references/frontmatter-reference.md](references/frontmatter-reference.md).

### 5. Write the system-prompt body

The body **is** the system prompt. Proven shape:

```
You are a <role> specializing in <domain>.

When invoked:
1. <first concrete step — often "run git diff" / "read the failing test">
2. ...
3. <produce the deliverable>

<Checklist or key practices the agent must apply>

<Output contract: exactly how to format the result that returns to the caller>

<Focus rule: the one thing to optimize / not do>
```

Match **degrees of freedom** to the task: tight numbered steps for fragile/destructive work (migrations, batch edits); high-level direction for open-ended judgement (code review). Because the agent is cold, put any non-obvious repo fact, convention, or constraint **in the body**. Worked examples and the full pattern: [references/system-prompt-patterns.md](references/system-prompt-patterns.md). Copy-ready skeleton: [assets/agent-template.md](assets/agent-template.md).

### 6. Validate and test

- Frontmatter is valid YAML between `---`; `name` is lowercase-hyphens; `tools` names are real; `model` is a valid alias/ID/`inherit`.
- Manual file edits load at **session start** — restart, or create via `/agents` (effective immediately).
- **Triggering test:** give a natural prompt that *should* delegate and confirm Claude picks the agent; if not, sharpen the `description`. **Behavior test:** run it on a real task and confirm it stays in its tool boundary and returns the contracted output. Method: [references/triggering-and-testing.md](references/triggering-and-testing.md).

For teams of agents (a coordinator that delegates to specialists), keep each specialist single-responsibility and let the coordinator route — see the orchestration notes in [references/system-prompt-patterns.md](references/system-prompt-patterns.md).

## Anti-patterns

- **Omitting `tools` "to be safe"** → inherits everything, including `Write`/`Edit`/`Bash` on a "reviewer". Always set the boundary.
- **Assuming the agent sees the chat** → it starts cold. Restate context, or preload a skill.
- **A vague `description`** → Claude never delegates. Name the trigger; add "use proactively".
- **One mega-agent** doing review + fix + test + deploy → split by responsibility.
- **Recreating `Explore`/`Plan`/`general-purpose`** → use the built-ins.
- **`bypassPermissions` by default** → only when truly justified; prefer `tools`/`disallowedTools` + hooks.
- **Premium model for bulk work** → route summarizing/search to `haiku`.

## Resources

- [references/frontmatter-reference.md](references/frontmatter-reference.md) — every frontmatter field (`tools`, `disallowedTools`, `model`, `skills`, `memory`, `permissionMode`, `mcpServers`, `hooks`, `effort`, `isolation`, `color`, `initialPrompt`, `maxTurns`), scopes & precedence, model-resolution order, tool-inheritance rules, what loads at startup. Load when writing or debugging frontmatter.
- [references/system-prompt-patterns.md](references/system-prompt-patterns.md) — how to write the body and the `description`: role + "When invoked" workflow + checklist + output contract, degrees-of-freedom, cold-context briefing, orchestration/teams, plus annotated example agents. Load when writing prompts.
- [references/managed-agents.md](references/managed-agents.md) — Claude **Managed Agents** (cloud harness): agent = model + system prompt + tools + MCP + skills; when to use vs. a Code subagent; create-agent/session essentials and the beta header. Load when the user wants a programmatic/cloud agent.
- [references/triggering-and-testing.md](references/triggering-and-testing.md) — triggering tests (does it delegate?) and behavior/pressure tests (does it stay in bounds and deliver?). Load before finalizing.
- [assets/agent-template.md](assets/agent-template.md) — fill-in subagent skeleton (frontmatter + body).
- [assets/examples/](assets/examples/) — ready-to-adapt agents: `code-reviewer.md` (read-only), `debugger.md` (fix-capable), `safe-researcher.md` (restricted tools), `test-runner.md` (isolates verbose output). Read for concrete patterns.
