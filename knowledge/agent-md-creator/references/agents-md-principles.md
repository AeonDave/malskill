# AGENTS.md Principles

Use this reference when creating, updating, or reviewing an `AGENTS.md` file.

## Core facts

- `AGENTS.md` is plain Markdown — there are **no required headings or schema fields**.
- Put the main file at the **repository root**.
- In monorepos or large repos, add **nested `AGENTS.md` files** where subprojects need different instructions.
- The **closest file in the directory tree wins** when instructions conflict.
- Explicit user instructions override file instructions.
- `AGENTS.md` complements `README.md`; it should contain agent-facing **operational instructions**, not design rationale, interface definitions, or general project documentation for humans.
- `AGENTS.md` is **not written in stone**: it should evolve as development practices, available tools, discovered workflows, and boundaries change.
- **Default home for developer detail**: `README.md` is the first place for architecture notes, interface overviews, pipeline explanations, and design rationale. Use a reference file only when that material is too detailed or too specialized for the README.
- **Instruction scope**: if a section explains how the code works rather than directing the agent on what to do, move it to `README.md` or a reference file. The test: "does this change how the agent acts?" — if no, it does not belong here.

## What to include

Include only high-signal details that help an agent act correctly:

1. exact build / lint / test / run commands (with prerequisites and change triggers when relevant)
2. active user decisions that materially affect tool choice or workflow
3. file or package discovery tips for the repo layout
4. project-specific code conventions that are not obvious
5. comment-style expectations when the repo cares about language, tone, or what deserves explanation
6. hard constraints with safe alternatives when violations are silent but costly
7. testing expectations and fast feedback commands
8. debugging expectations, escalation paths, and available tooling
9. extension guides for modular architectures (short numbered steps for "adding a new X")
10. boundaries, approval rules, and risky areas to avoid
11. accepted diagnostics or deferred issues when the user explicitly wants them ignored
12. optional PR / commit conventions if they are enforced by the team

When describing structure, prefer **directory-level notes** such as `src/api/` or `packages/web/` with a short explanation of what belongs there. Avoid exhaustive file-by-file inventories unless a file is uniquely important to agent behavior. Mark generated files inline (e.g., `⚡ GENERATED`) so the agent skips them. Use `See <path>/AGENTS.md` to delegate subdirectory-specific detail rather than duplicating it at root.

## What strong files do well

Recent public guidance and repo analysis repeatedly favor these patterns:

- put commands early, with any prerequisite or change-triggered re-run steps clearly noted
- prefer executable examples over abstract prose
- be specific about stack, versions, and key directories
- keep project structure brief and folder-oriented instead of turning it into a file manifest
- mark generated files inline so agents do not attempt to edit them
- when comment guidance matters, make it qualitative: English, technical, precise, and brief — explain intent rather than narrating obvious code
- make testing expectations explicit when the agent is expected to add or update tests
- give a short debugging workflow that favors local evidence before outside research
- capture durable user decisions in a clear section so the agent does not have to rediscover them from chat history
- record intentionally ignored diagnostics so the agent does not keep reopening them
- define boundaries with clear `always`, `ask first`, or `never` style rules when needed
- for modular architectures, include a short numbered "adding a new X" guide to prevent structural errors
- for projects with hard constraints (security, OPSEC, compatibility), use a two-column `forbidden → use instead` table
- for complex projects with many non-obvious rules, a `## Checklist for new code` section is more actionable than prose conventions
- use cross-references (`See path/AGENTS.md`) to keep root files lean when subtrees have specialized rules
- keep instructions short enough to load often

## Monorepo guidance

Use a root file for workspace-wide facts:

- package manager
- workspace commands
- shared tool choices or operator agreements
- CI/test strategy
- shared debugging tools or escalation expectations
- how to find the right package

Use nested files for subtree-specific facts:

- local commands
- local user decisions if they differ from the root behavior
- local test locations and commands
- local debug entrypoints or scripts
- accepted warnings limited to that subtree
- local architecture rules
- files in scope
- stricter boundaries

## Migration guidance

When replacing tool-specific files:

- keep one canonical source of truth in `AGENTS.md`
- preserve only verified repo-specific instructions
- avoid copying generic prompts from older files
- add compatibility links or symlinks only if the repo actually needs them

## Maintenance guidance

- Update `AGENTS.md` after important repository changes that affect commands, directory layout, workflow, conventions, or boundaries.
- Update it when testing/debugging practices materially change, when the user declares or retracts a persistent tool/workflow choice, or when new available tools change the preferred flow.
- Update accepted diagnostics entries when an ignored warning is fixed, reopened, or no longer relevant.
- If a change does not affect agent behavior, do not add noise just to record it.
- Keep maintenance edits small and factual so the file stays current without growing into a changelog.

## Testing and debugging guidance

- If the project has tests, `AGENTS.md` should state whether the agent is expected to add or update tests for changed behavior.
- Prefer fast, scoped validation commands before slow full-suite commands.
- For debugging, prefer local tools first: tests, logs, debuggers, repro scripts, profiling, and temporary helpers.
- If repeated local attempts fail, `AGENTS.md` can say to escalate after 2–3 iterations instead of retrying blindly.
- If online research is sensitive, costly, or policy-relevant, say that the agent should align with the user before using it.

## Decisions and accepted diagnostics guidance

- If the user says to prefer a tool or workflow repeatedly, store that in a dedicated section such as `## Active user decisions`.
- Mark those entries as current choices, not eternal truth; they can be changed later.
- If the user says a warning, lint issue, or UI error should not be modified, record it in a scoped section such as `## Accepted diagnostics`.
- Each accepted diagnostic should identify the path, the issue, and whether it is ignored, deferred, or out of scope.
- When only one or two diagnostics are accepted, an inline comment on the build command that produces them is sufficient; a dedicated section is not needed.

## Instruction scope guidance

`AGENTS.md` contains **operational instructions** — what to run, what to avoid, how to add new features, what constraints apply, how to verify work.

**Do not include in `AGENTS.md`:**
- interface definitions or struct declarations (belong in `README.md` or code comments)
- step-by-step explanations of internal build pipeline behavior (belong in `README.md`)
- behavioral deep-dives explaining how a technique, algorithm, or design works
- long reference tables that describe what exists rather than what to do

**Do include in `AGENTS.md`:**
- the specific steps an agent must follow to extend or modify the system correctly
- hard constraints with safe alternatives when the violation is non-obvious
- new-code checklists for projects where many rules apply simultaneously
- error code ranges or naming conventions the agent must follow when writing new code

If you are unsure, ask: "does this line change how the agent behaves?" If no, move it to `README.md` first, or to a reference file if it is too detailed for the README.

## Sources

- `https://agents.md/` — official open-format overview and FAQ, including precedence and root/nested usage
- `https://raw.githubusercontent.com/agentsmd/agents.md/main/AGENTS.md` — sample repository guidance showing command-first, operational instructions
- `https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/` — GitHub blog, Nov 2025, summarizing what works across 2,500+ repos

For a condensed extraction of the GitHub article, see [github-lessons.md](github-lessons.md).
