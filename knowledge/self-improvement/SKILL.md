---
name: self-improvement
description: "Capture errors, corrections, discoveries, and recurring patterns so future sessions start smarter. Use when a user corrects the agent, a non-obvious failure is diagnosed, a project convention is discovered, a requested capability is missing, or before starting long multi-session work in an area that may already have learnings."
license: MIT
compatibility: "Python 3.11+ for full helper automation, a POSIX shell for fallback .sh scripts, or WSL on Windows via the included PowerShell bridge."
metadata:
  author: malskill
  version: "1.2"
---

# Self Improvement

Use this skill to preserve hard-won knowledge across long coding cycles, follow-up sessions, and repeated work in the same repository. Log what mattered, review it before similar work, and promote durable patterns into project memory or reusable skills.

> **Core principle**: treat solved surprises as reusable assets, not disposable chat history.

## When to use

Activate this skill when any of these happen:

- the user corrects the agent or reveals a project convention
- a command, build, validator, or tool fails in a non-obvious way
- a better workflow is discovered while debugging or implementing
- the user requests a capability the current workflow does not support
- the same mistake, workaround, or reminder shows up again
- a new session begins on a task family that may already have learnings

Do not use this skill for trivial one-off typos or obvious failures that add no future value.

## Quick Reference

| Situation | Log file | Default type |
|---|---|---|
| User correction or new repo fact | `.learnings/LEARNINGS.md` | `correction` or `knowledge_gap` |
| Non-obvious fix or better workflow | `.learnings/LEARNINGS.md` | `best_practice` or `insight` |
| Command, tool, or integration failure | `.learnings/ERRORS.md` | error entry |
| Missing capability requested by user | `.learnings/FEATURE_REQUESTS.md` | feature request |
| Session end or significant milestone | `.learnings/STATUS.md` | session handoff |
| Repeated issue or repeated workaround | update existing entry first | recurring pattern |
| Broadly reusable lesson | promote beyond `.learnings/` | `promoted` or `promoted_to_skill` |

## Recommended Workflow

### 1. Create the learning store and register it in AGENTS.md

Use a local `.learnings/` directory in the current project or workspace:

```text
.learnings/
├── LEARNINGS.md
├── ERRORS.md
├── FEATURE_REQUESTS.md
└── STATUS.md
```

If the files do not exist, create them from the templates in `assets/`.

Automation options:
- `scripts/ensure_store.py --store-dir .learnings`
- `scripts/ensure_store.sh .learnings`

These helpers create the store and starter files only. They do **not** edit `AGENTS.md` for you.

**Critical**: after creating `.learnings/`, add a section to the project's `AGENTS.md` (or `CLAUDE.md`, `.github/copilot-instructions.md` — whichever the project uses) so that future agent sessions know the store exists and which skill to use. Without this reference, agents will not consult `.learnings/` or apply this skill. Add at minimum:

```md
## Self-improvement

This project uses a `.learnings/` folder to track errors, corrections, discoveries, and session status.

- Before starting deep work, review `.learnings/STATUS.md` and scan relevant entries in `LEARNINGS.md` and `ERRORS.md`.
- After corrections, non-obvious failures, or session-end, log entries using the `self-improvement` skill.
- See the `self-improvement` skill for entry formats, brevity rules, and promotion guidelines.
```

If the project already references `.learnings/` in its instruction file, verify the reference is current and skip this step.

### 2. Review before deep work

Before starting a large feature, refactor, research task, or debugging pass:

1. read `.learnings/STATUS.md` first — it tells you where the last session left off
2. identify the area you are about to touch
3. search `.learnings/` for matching keywords, tags, files, or area values
4. read any still-relevant entries
5. keep the review short and task-specific

Use this pre-flight review especially for work that spans multiple sessions.

### 3. Log immediately after the signal appears

Log while context is still fresh. Write a **prevention rule**, not an incident report.

Each entry must answer exactly three questions:
1. **What is the rule?** (Summary — one sentence)
2. **Why does it matter?** (Details — 1–3 sentences, root cause only)
3. **What to do next time?** (Suggested Action — one imperative sentence)

If the entry needs code blocks, tables, architecture explanations, or multi-paragraph narratives, the content belongs in project documentation — not in `.learnings/`.

Automation options:
- `scripts/log_learning.py` for structured Python-based logging
- `scripts/log_learning.sh` for shell-only environments

### 4. Update instead of duplicating

If a similar entry already exists:
- add a `See Also` link
- increment recurrence metadata when appropriate
- raise priority only when the impact is now clearer
- avoid creating near-duplicate entries for the same pattern

### 5. Promote durable knowledge

Promote a learning when it should shape future behavior before the next failure happens.

Typical targets:
- `AGENTS.md` for repeatable agent workflow rules
- `CLAUDE.md` or `.github/copilot-instructions.md` for project conventions and coding reminders
- persistent memory files or repo-specific instruction systems, if your platform supports them
- a new reusable skill when the lesson is broadly applicable beyond one repository

Automation options:
- `scripts/promote_learning.py --target file ...` to append a distilled rule and mark the source entry as promoted
- `scripts/promote_learning.py --target skill ...` to scaffold a new skill and mark the source entry as `promoted_to_skill`
- matching `.sh` versions for POSIX shell environments without Python

### 6. Update status at session end

At the end of a significant task or work session, update `.learnings/STATUS.md`:
- move completed items to **Done**
- update **In Progress** with current state and any blockers
- list the most important next steps under **Next**
- record key **Decisions** that affect future work
- keep each item to one line — this is a handoff note, not documentation

Also in `.learnings/LEARNINGS.md` and `.learnings/ERRORS.md`:
- resolve entries that are now fixed
- mark promoted items clearly

## What to log

Log **prevention rules** — not incident histories. Each entry should help a future session avoid repeating a mistake or rediscovering a convention. If the entry reads like a story of what was fixed, rewrite it as a rule.

Log learnings (corrections, insights, knowledge gaps, best practices), non-obvious errors, and feature requests for missing capabilities. See `references/entry-formats.md` for full schemas and field constraints.

## Promotion and recurring patterns

Promote a learning when it is broader than one incident, verified by real work, and concise enough for project instructions. Extract a new skill when the lesson is broadly reusable and procedural. Treat repetition as signal — update recurrence fields instead of duplicating entries.

See `references/promotion-guidelines.md` for the full decision framework, recurring pattern thresholds, and skill extraction checklist.

## Brevity Rules

Every entry must pass this test: **can a future session extract the prevention rule in under 30 seconds?** If reading the entry feels like reading an incident report, it is too long.

Hard constraints:
- **Summary**: one sentence, max 120 characters
- **Details**: 1–3 short sentences explaining the root cause or the convention — not a narrative of what happened
- **Suggested Action**: one imperative sentence — what to do or avoid next time
- **Error** (error entries): only the most relevant 1–5 lines of output, not the full log
- **Total entry size**: aim for 10–20 lines including metadata; never exceed 30 lines
- **No implementation detail**: do not include code blocks, tables, architecture diagrams, or step-by-step implementation plans — those belong in project docs, references, or code comments
- **No resolved-task inventories**: do not list what was fixed or track implementation status — that belongs in issues, PRs, or changelogs

Anti-patterns — do NOT produce entries that:
- read like a changelog or postmortem
- contain tables mapping features to implementation status
- explain how a protocol or system works
- include multi-paragraph narratives of what happened chronologically
- duplicate information that belongs in project documentation

## Quality Rules

- log immediately, not from memory hours later
- be specific about files, commands, or tools
- keep examples factual and reproducible
- resolve, promote, or retire stale entries during natural review points
- do not store secrets, credentials, tokens, or sensitive data in learning files

## Resources

- `references/getting-started.md` — create the `.learnings/` store, choose tracking strategy, wire optional reminders, and automation command reference
- `references/entry-formats.md` — full entry schemas, enums, ID rules, area taxonomy, and resolution fields
- `references/examples.md` — malskill-oriented examples for learnings, errors, promotions, and extracted skills
- `references/promotion-guidelines.md` — decide what belongs in local logs versus project instructions or new skills
- `references/openclaw-integration.md` — optional OpenClaw-specific install and hook path
- `assets/LEARNINGS.md` — template and status glossary for the main learning log
- `assets/ERRORS.md` — starter structure for error log entries
- `assets/FEATURE_REQUESTS.md` — starter structure for feature request entries
- `assets/STATUS.md` — session handoff template for multi-session project tracking
- `references/skill-template.md` — template for turning a learning into a standalone skill
- `scripts/activator.py` — lightweight reminder output for prompt-submit style hooks
- `scripts/activator.sh` — shell fallback for the same reminder output
- `scripts/error_detector.py` — reminder output when command results contain real error signals
- `scripts/error_detector.sh` — shell fallback for the same error reminder logic
- `scripts/ensure_store.py` and `scripts/ensure_store.sh` — create the `.learnings/` store and starter files
- `scripts/log_learning.py` and `scripts/log_learning.sh` — append structured learning, error, or feature entries
- `scripts/promote_learning.py` and `scripts/promote_learning.sh` — promote a learning into project guidance or a new skill
- `scripts/extract_skill.py` and `scripts/extract_skill.sh` — scaffold a new skill from an explicit theme or source learning entry
- `scripts/run_in_wsl.ps1` — Windows bridge that invokes the `.sh` fallbacks through WSL with safe path conversion
- `hooks/openclaw/HOOK.md` and `hooks/openclaw/` handlers — optional OpenClaw bootstrap reminder resources
