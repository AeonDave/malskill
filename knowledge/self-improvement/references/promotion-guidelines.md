# Promotion Guidelines

Promote a learning only after distilling it into a preventive rule.

## Promotion decision

Ask these questions in order:

1. Is the lesson broader than one incident?
2. Will another session benefit before repeating the mistake?
3. Can the rule be written in one or two concise bullets?
4. Has the lesson been verified by real work?

If the answer is no to any of these, keep the detail in `.learnings/` for now.

## Good promotion targets

### `AGENTS.md`

Use for:
- repeatable agent workflow rules
- validation, packaging, or review steps that should happen every time
- sequencing guidance for multi-step tasks

Example:
- After editing a skill, validate it with `quick_validate.py` before finishing.

### `CLAUDE.md` or `.github/copilot-instructions.md`

Use for:
- repository conventions
- project-specific commands
- coding habits or gotchas that should be known early in a session

Example:
- Use folder-level project structure sections only; do not turn them into file inventories.

### Persistent memory or repo memory

Use for:
- facts that are stable across tasks
- concise reminders that do not belong in full project instructions

Prefer short, durable facts rather than workflow prose.

### New skill

Create a skill when the lesson is:
- reusable across repositories
- strongly procedural
- easier to apply with a dedicated workflow, examples, or scripts
- too detailed to fit cleanly in general instructions

## What not to promote

Do not promote:
- raw error logs
- one-off local environment mistakes
- speculative advice not backed by a successful run
- long incident narratives that belong in `.learnings/` only

## Promotion workflow

1. distill the incident into a prevention rule
2. choose the smallest durable target
3. update the target file with concise wording
4. mark the original learning as `promoted` or `promoted_to_skill`
5. record the promotion target or skill path

Automation helpers:
- `scripts/promote_learning.py`
- `scripts/promote_learning.sh`

## Recurring pattern threshold

A repeated issue is a strong promotion candidate when:
- it has recurred at least three times
- it appeared in two or more tasks or sessions
- the prevention rule is short and actionable

## Skill extraction checklist

Before extracting a skill, confirm all of the following:
- the learning is resolved or otherwise well understood
- the description can stand alone without the original chat
- examples are portable and not full of repo-specific assumptions
- helper scripts, if any, have safe defaults
- the resulting skill is useful to future agents, not just to one conversation

If the answer is yes, use `scripts/promote_learning.py --target skill ...` or the shell fallback to scaffold the new skill and update the source entry.
