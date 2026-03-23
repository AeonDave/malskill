---
name: self-improvement
description: "Capture errors, corrections, discoveries, and recurring patterns so future sessions start smarter. Use when a user corrects the agent, a non-obvious failure is diagnosed, a project convention is discovered, a requested capability is missing, or before starting long multi-session work in an area that may already have learnings."
license: MIT
compatibility: "Python 3.11+ for full helper automation, a POSIX shell for fallback .sh scripts, or WSL on Windows via the included PowerShell bridge."
metadata:
  author: malskill
  version: "1.1"
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
| Repeated issue or repeated workaround | update existing entry first | recurring pattern |
| Broadly reusable lesson | promote beyond `.learnings/` | `promoted` or `promoted_to_skill` |

## Recommended Workflow

### 1. Create or locate the learning store

Use a local `.learnings/` directory in the current project or workspace:

```text
.learnings/
├── LEARNINGS.md
├── ERRORS.md
└── FEATURE_REQUESTS.md
```

If the files do not exist, create them from the templates in `assets/`.

Automation options:
- `scripts/ensure_store.py --store-dir .learnings`
- `scripts/ensure_store.sh .learnings`

### 2. Review before deep work

Before starting a large feature, refactor, research task, or debugging pass:

1. identify the area you are about to touch
2. search `.learnings/` for matching keywords, tags, files, or area values
3. read any still-relevant entries first
4. keep the review short and task-specific

Use this pre-flight review especially for work that spans multiple sessions.

### 3. Log immediately after the signal appears

Log while context is still fresh. Prefer one precise entry over a long narrative.

Capture:
- what happened
- why it mattered
- what to do differently next time
- which files, tools, or commands were involved

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

### 6. Re-check after completion

At the end of a significant task:
- resolve entries that are now fixed
- mark promoted items clearly
- link commits, PRs, or changed files when useful
- note whether the pattern should be reviewed again later

## What to log

Log learnings (corrections, insights, knowledge gaps, best practices), non-obvious errors, and feature requests for missing capabilities. See `references/entry-formats.md` for full schemas, categories, area taxonomy, and status values.

## Promotion and recurring patterns

Promote a learning when it is broader than one incident, verified by real work, and concise enough for project instructions. Extract a new skill when the lesson is broadly reusable and procedural. Treat repetition as signal — update recurrence fields instead of duplicating entries.

See `references/promotion-guidelines.md` for the full decision framework, recurring pattern thresholds, and skill extraction checklist.

## Quality Rules

- log immediately, not from memory hours later
- be specific about files, commands, or tools
- prefer concise prevention guidance over long incident reports
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
- `assets/ERRORS-template.md` — starter structure for error log entries
- `assets/FEATURE-REQUESTS-template.md` — starter structure for feature request entries
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
