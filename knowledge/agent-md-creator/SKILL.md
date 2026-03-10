---
name: agent-md-creator
description: "Create, update, or refactor repository-root and nested AGENTS.md files for AI coding agents. Use when the user asks to bootstrap AGENTS.md, replace tool-specific instruction files with a shared open format, compress overly verbose agent instructions, document build/test commands for agents, or design minimal project instructions for monorepos and subprojects."
license: MIT
compatibility: "Markdown; works for repos using GitHub Copilot, Codex, Cursor, Claude Code, Aider, Gemini CLI, and other agents that read AGENTS.md"
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

When the user declares operational choices during chat sessions, capture them in a **clear dedicated section** if the file does not already have one.

Typical examples:

- preferred online research tools such as Tavily
- preferred local analysis tools such as `objdump`, `readelf`, `pytest`, `dlv`, or platform-specific debuggers
- explicit workflow preferences such as "use local tools first" or "ask before web research"
- temporary but currently active project choices that should keep behavior stable across sessions

Recommended section names:

- `## Active user decisions`
- `## Working agreements`
- `## Current tool choices`

State these decisions as **active but revisable**. The file should make it clear that they can be changed or retracted later without rewriting unrelated guidance.

### 3b. Treat testing as part of the change

When the project has a test suite or test conventions, say so explicitly in `AGENTS.md`:

- the agent should add or update tests that cover the behavior it changed
- the agent should prefer the smallest relevant test command first, then broader validation if needed
- if the repo has no meaningful automated tests, the file should say what validation is expected instead

Do not promise test creation blindly for repos where tests are intentionally absent, generated elsewhere, or not appropriate for the project type.

### 3c. Treat debugging as an evidence-gathering workflow

If the repository often requires debugging, encode that workflow in `AGENTS.md` with short, operational bullets:

- use available local tools first: tests, linters, type checkers, logs, debuggers, trace output, repro scripts, profilers, or existing project diagnostics
- when local tooling is missing, create small temporary debugging helpers or scripts in Python or the project language when that is the fastest way to get clear answers
- prefer tools that produce concrete evidence over guesswork
- after **2–3 failed iterations** on the same unresolved problem, escalate deliberately instead of retrying blindly
- if external or online research is needed, the agent should first align with the user before using it unless the repo already explicitly permits that workflow

### 3d. Record accepted diagnostics and intentionally ignored UI issues

If the user explicitly says that a warning, lint issue, or UI diagnostic should **not** be changed, store that in a dedicated section instead of letting the agent rediscover it constantly.

Good examples:

- `## Accepted diagnostics`
- `## Known ignored warnings`
- `## Deferred issues`

Each entry should be short and scoped:

- file or path scope
- error / warning summary
- whether it is intentionally ignored, deferred, or out of scope
- optional condition for revisiting it

This helps the agent avoid repeatedly analyzing the same accepted warning and preserves flow across sessions.

### 4. Optimize for token cost

The default target is a short file that an agent can load often without wasting context.

- Prefer **30–120 lines** for most repositories.
- Keep only high-signal instructions that change agent behavior.
- Put executable commands early.
- Prefer one real example over multiple abstract rules.
- Do not duplicate content already obvious from filenames unless it saves repeated discovery.
- Do not document product history, motivation, or onboarding prose for humans.
- Do not add sections just to match a template.
- Keep testing and debugging guidance short and operational; avoid generic quality slogans.
- Keep user-declared decisions and accepted diagnostics concise, scoped, and easy to revise.

Load [references/optimization-checklist.md](references/optimization-checklist.md) when tightening a draft or reviewing an existing verbose file.
Use [references/github-lessons.md](references/github-lessons.md) when you want concrete guidance on command order, examples, boundaries, and the six high-value sections.

### 5. Merge or refactor existing files carefully

When an instruction file already exists:

- preserve verified commands, boundaries, repo-specific gotchas, real testing/debugging workflows, active user decisions, and accepted diagnostics that are still in force
- remove stale commands, duplicated explanations, and generic filler
- consolidate overlapping files only if the user asked for it or if duplication is clearly harmful
- keep the result in `AGENTS.md` when the goal is a portable, tool-agnostic format
- update `AGENTS.md` whenever important repository changes, discovered workflows, or tool availability affect how the agent should work

When migrating from tool-specific files, keep compatibility notes short and prefer a single source of truth.

### 6. Validate before finishing

Check that the final `AGENTS.md`:

- uses commands that exist in the repo
- references real directories and filenames
- records user-declared tool or workflow choices in a dedicated section when they affect ongoing behavior
- records intentionally ignored or deferred diagnostics when the user asked for that behavior
- keeps `Project structure` focused on directories and high-signal paths, not exhaustive file listings
- explains testing/debugging expectations when they materially affect how the agent should work
- contains only instructions that matter to agent behavior
- stays concise enough to load frequently
- does not leave placeholders, TODOs, or fake examples
- moves developer-facing detail to `README.md` or a reference file instead of leaving it in `AGENTS.md`
- is refreshed after important repo changes so it does not drift from reality

## Drafting Rules

- Be precise, technical, and minimal.
- Use imperative language.
- Prefer bullets over paragraphs.
- Prefer repo facts over generic advice.
- Mention commands with flags when they reduce ambiguity.
- Put durable chat-made decisions in a clear section instead of leaving them implicit in conversation history.
- In `Project structure`, prefer folders plus one short explanation of what lives there.
- In `Testing`, say whether tests must be added or updated for behavioral changes.
- In `Debugging`, prefer a short escalation rule: local tools first, then user-approved online research if repeated attempts fail.
- If the user does not want a specific warning or lint issue touched, record that explicitly with scope.
- When documenting code-comment expectations, prefer qualitative guidance: comments should be technical, precise, in English, and brief. Explain intent, invariants, edge cases, or non-obvious tradeoffs — not line-by-line mechanics.
- Mention approval boundaries only when they prevent real risk.
- If no reliable command exists, say so instead of inventing one.
- Treat `AGENTS.md` as a living operational file: update it when the project changes, when better workflows are discovered, or when available tools materially change.
- Distinguish **agent instructions** (what to do, how to validate, what to avoid) from **developer documentation** (how the code works, interface definitions, design rationale). The former belongs in `AGENTS.md`; the latter belongs in `README.md` by default, or in a dedicated reference file when it is too detailed for the README. If a section describes code internals rather than directing agent behavior, move or remove it.
- For hard technical constraints where violations are silent but costly (security, OPSEC, compatibility), prefer a two-column `forbidden → use instead` table over prose rules.
- For modular or plugin-style architectures, a short numbered "Adding a new X" guide (4–8 steps) prevents structural mistakes without duplicating the README.
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

### Hard constraint tables

For projects where using certain patterns is security-critical, OPSEC-important, or compatibility-breaking, document as a compact two-column table (`forbidden pattern → safe alternative`). Pair each constraint with a clear replacement so the agent has a path forward. Example:

| Forbidden | Use instead |
|-----------|-------------|
| `crypto/rand` | `math/rand` seeded via `time.Now().UnixNano()` |
| `math/rand/v2` | `math/rand` (v1) for TinyGo compatibility |

Place this in a dedicated section such as `## Hard constraints` or inline under `## Conventions`.

### `## Checklist for new code`

For complex projects with many non-obvious rules, a bulleted checklist is more actionable than prose conventions — each item is something the agent can explicitly verify before finishing. Keep it to rules the agent could realistically miss. Useful when violations are hard to catch in review and have significant impact (security, OPSEC, ABI compatibility, naming conventions).

### Comment guidance

If the repository has strong expectations for source-code comments, capture them as 1–3 short bullets under `## Conventions` or `## Code style`. Good guidance is qualitative, not quantitative: comments should be technical, precise, written in English, and used for intent, invariants, hazards, or non-obvious reasoning. Avoid rules that encourage a comment for every line or every function regardless of value.

### Extension guides

For modular or plugin-style architectures (interface + `init()` registration, strategy pattern, encoder stacks), a short numbered "Adding a new X" section (4–8 steps) prevents the agent from missing required steps. Cover: file placement, interface implementation, self-registration, flag wiring, and any alias or build updates needed. Do **not** reproduce the full interface spec — just the steps required to add a new instance correctly.

## Resources

### references/

- [references/agents-md-principles.md](references/agents-md-principles.md) — load when deciding structure, precedence, section selection, or migration rules.
- [references/optimization-checklist.md](references/optimization-checklist.md) — load when shrinking a draft, reviewing quality, or turning vague instructions into concise, actionable bullets.
- [references/github-lessons.md](references/github-lessons.md) — load when you need the actionable lessons from GitHub's Nov 2025 analysis of 2,500+ `AGENTS.md` files.

### assets/

- `assets/minimal-agents-template.md` — minimal starter template for root `AGENTS.md` files; customize every placeholder with repo-specific facts before saving.
