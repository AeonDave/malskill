---
name: agent-md-creator
description: "Create, update, or refactor repository-root and nested AGENTS.md files for AI coding agents. Use when the user asks to bootstrap AGENTS.md, replace tool-specific instruction files with a shared open format, compress overly verbose agent instructions, document build/test commands for agents, or design minimal project instructions for monorepos and subprojects."
license: MIT
compatibility: "Markdown; works for repos using GitHub Copilot Coding agent, OpenAI Codex, Cursor, Claude Code, Gemini CLI, Windsurf, RooCode, Amp, and other agents that read AGENTS.md"
metadata:
  author: AeonDave
  version: "1.0"
---

# Agent MD Creator

Create technical, token-efficient `AGENTS.md` files that help coding agents work immediately without bloating context. Treat `AGENTS.md` as a living operational file: it should evolve with the codebase, discovered workflows, current tool availability, and real team practices. Prefer compact, evidence-based instructions over generic prompting.

## Workflow

### 1. Discover the real project shape

Before drafting anything:

- Search for existing instruction files: `AGENTS.md`, `AGENT.md`, `.github/copilot-instructions.md`, `CLAUDE.md`, `.cursorrules`, README files, and CI workflows.
- Inspect build/test/lint commands from actual repo files instead of guessing.
- Identify stack, package manager, subprojects, test framework, and directories the agent will likely edit.
- If the repo is a monorepo, decide whether one root file is enough or whether nested `AGENTS.md` files are needed.

If you need structure, precedence, or section guidance, load [references/agents-md-principles.md](references/agents-md-principles.md).
If you need the 2025 GitHub-specific lessons from analysis of 2,500+ repositories, load [references/github-lessons.md](references/github-lessons.md).

### 2. Choose the smallest useful scope

Default to a single root `AGENTS.md`.

Add nested `AGENTS.md` files only when at least one of these is true:

- subprojects use different stacks or commands
- backend/frontend/infrastructure have different workflows
- the root file would become long or full of exceptions
- a subdirectory needs stricter boundaries than the rest of the repo

Keep instructions local: the nearest `AGENTS.md` should carry only the details relevant to that subtree.

### 3. Draft a minimal, technical AGENTS.md

Use only sections supported by evidence from the repo. Preferred order:

1. Commands the agent can run
2. Active user decisions / workflow choices
3. Testing / validation expectations
4. Debugging expectations when useful
5. Project structure or key paths
6. Code style or architecture rules that are not obvious
7. Boundaries / approval rules
8. Optional accepted diagnostics or PR / commit rules

Write short bullets, concrete paths, and exact commands. Prefer this:

- `pytest tests/api/test_users.py -q`
- `npm run lint`
- `src/api/` contains HTTP handlers
- `Code comments must be technical, precise, and written in English; explain why or intent, not obvious syntax`
- `Add or update tests for changed behavior in tests/api/`
- `If debugging stalls after 2–3 failed iterations, ask before using online research`
- `Use Tavily for online research when external lookup is needed`
- `Use objdump for binary inspection before switching tools`
- `Ignore the existing warning in src/ui/App.tsx unless the user reopens it`
- `go vet ./... # one pre-existing unsafe.Pointer warning in injection/ is accepted — do not fix it`
- `Regenerate the resource blob after changes in evasion/ or injection/: bash scripts/gen.sh`

For `## Project structure`, stop at the **folder level** unless a specific file is truly operationally important. Describe what each directory contains or should contain. Do **not** dump long file inventories. Mark generated files inline when their presence causes confusion (e.g., `resources.enc ⚡ GENERATED — do not edit`). When a subdirectory has its own specialized rules, write `See <path>/AGENTS.md` to keep the root lean instead of duplicating content.

Avoid this:

- “Use best practices”
- “Be careful with code quality”
- long prose repeating the README
- interface definitions, config structs, pipeline breakdowns, or behavioral deep-dives — put those in `README.md` or a reference file
- giant `Project structure` sections listing every file in the repo

If the user asks for a starter file from scratch, use [assets/minimal-agents-template.md](assets/minimal-agents-template.md) as the base and then replace every placeholder with repo-specific facts.

### 3a. Record active user decisions explicitly

When the user declares persistent tool/workflow choices, capture them in a dedicated section (`## Active user decisions`, `## Working agreements`, or `## Current tool choices`). Mark entries as active but revisable — not permanent rules. See [references/agents-md-principles.md](references/agents-md-principles.md).

### 3b. Treat testing as part of the change

When the project has tests, state whether the agent should add or update tests for changed behavior and which test command to run first. If the repo has no meaningful automated tests, say what validation is expected instead. Do not promise test creation for repos where tests are intentionally absent or generated elsewhere.

### 3c. Treat debugging as an evidence-gathering workflow

Encode the debugging workflow as short operational bullets:
- local tools first: tests, linters, type checkers, logs, debuggers, trace output, repro scripts, profilers
- create small temporary debugging helpers when local tooling is missing and that is the fastest path to clear answers
- after **2–3 failed iterations**, escalate deliberately instead of retrying blindly
- align with the user before online research unless already permitted

### 3d. Record accepted diagnostics and intentionally ignored UI issues

When the user says a warning or lint issue should not be changed, store it in a scoped entry (`## Accepted diagnostics`, `## Known ignored warnings`, or `## Deferred issues`) with path, issue summary, and disposition (ignored/deferred/out of scope). Prevents repeated re-analysis. See [references/agents-md-principles.md](references/agents-md-principles.md).

### 4. Optimize for token cost

Target **30–80 lines** for small repos, **60–120 lines** for medium repos. Commands early. One real example beats abstract rules. No product history, motivation, or template noise.

Load [references/optimization-checklist.md](references/optimization-checklist.md) when tightening a draft.
Use [references/github-lessons.md](references/github-lessons.md) for command order, examples, and the six high-value sections.

### 5. Merge or refactor existing files carefully

Preserve verified commands, boundaries, repo-specific gotchas, and active decisions still in force. Remove stale commands, duplicated explanations, and generic filler. Prefer one canonical `AGENTS.md`; migrate tool-specific files only when the user requests it or duplication is clearly harmful. See [references/agents-md-principles.md](references/agents-md-principles.md) § Migration and Maintenance.

### 6. Validate before finishing

- Commands and paths are real; no placeholders, TODOs, or fake examples.
- `Project structure` is directory-level only — no file inventories.
- Developer documentation moved to `README.md` or a reference file.
- Only instructions that change agent behavior remain.

Load [references/optimization-checklist.md](references/optimization-checklist.md) for the full quality checklist.

## Drafting Rules

- Be precise, technical, and minimal.
- Prefer repo facts over generic advice.
- Mention commands with flags when they reduce ambiguity.
- In `Project structure`, prefer folders plus one short explanation of what lives there.
- Mention approval boundaries only when they prevent real risk.
- If no reliable command exists, say so instead of inventing one.
- Treat `AGENTS.md` as a living operational file: update it when the project changes, when better workflows are discovered, or when available tools materially change.
- A single accepted diagnostic can be recorded as an inline comment on the command that produces it rather than creating a dedicated section for just one issue.

## Common Section Patterns

### Small repository

- `## Commands`
- `## Active user decisions`
- `## Testing`
- `## Debugging`
- `## Project structure`
- `## Accepted diagnostics`
- `## Boundaries`

### Monorepo root

- `## Workspace commands`
- `## Working agreements`
- `## Package discovery tips`
- `## Testing strategy`
- `## Debugging strategy`
- `## Accepted diagnostics policy`
- `## Nested AGENTS.md policy`

### Specialized subtree

- `## Local commands`
- `## Local decisions`
- `## Local testing`
- `## Local debugging`
- `## Local accepted diagnostics`
- `## Files in scope`
- `## Local conventions`
- `## Do not touch`

## Resources

### references/

- [references/agents-md-principles.md](references/agents-md-principles.md) — load when deciding structure, precedence, section selection, or migration rules.
- [references/optimization-checklist.md](references/optimization-checklist.md) — load when shrinking a draft, reviewing quality, or turning vague instructions into concise, actionable bullets.
- [references/github-lessons.md](references/github-lessons.md) — load when you need the actionable lessons from GitHub's Nov 2025 analysis of 2,500+ `AGENTS.md` files.

### assets/

- `assets/minimal-agents-template.md` — minimal starter template for root `AGENTS.md` files; customize every placeholder with repo-specific facts before saving.
