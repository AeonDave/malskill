# Entry Formats

Use these formats to keep learnings searchable, consistent, and **concise**.

Every entry is a **prevention rule**, not an incident report. If reading an entry takes more than 30 seconds, it is too long.

## Size constraints

| Section | Max length |
|---|---|
| Summary | 1 sentence, ≤120 characters |
| Details | 1–3 sentences — root cause or convention, not narrative |
| Suggested Action / Suggested Fix | 1 imperative sentence |
| Error (error entries) | 1–5 most relevant lines only |
| Full entry | 10–20 lines; never exceed 30 lines |

Do not include tables, architecture explanations, or implementation plans in entries. Code blocks are allowed only for the short `Error` section in error entries. Everything else belongs in project docs, references, or code comments.

## ID format

Use `TYPE-YYYYMMDD-XXX`.

- `TYPE`: `LRN`, `ERR`, or `FEAT`
- `YYYYMMDD`: current date
- `XXX`: sequential value such as `001`, `002`, `003`

Examples:
- `LRN-20260323-001`
- `ERR-20260323-002`
- `FEAT-20260323-001`

## Allowed priorities

- `low`
- `medium`
- `high`
- `critical`

## Allowed statuses

- `pending`
- `in_progress`
- `resolved`
- `wont_fix`
- `promoted`
- `promoted_to_skill`

## Recommended sources

Use one of these values in metadata when possible:
- `conversation`
- `user_feedback`
- `error`
- `review`
- `research`
- `simplify-and-harden`

## Recommended areas

Use one primary area:
- `workflow`
- `repo-config`
- `docs`
- `tooling`
- `programming`
- `testing`
- `knowledge`
- `research`
- `offensive-tools`
- `bof`

## Learning entry

Append to `.learnings/LEARNINGS.md`:

```md
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: area

### Summary
One sentence: the rule or convention learned (max 120 chars)

### Details
1–3 sentences: why this matters — root cause, not chronological narrative

### Suggested Action
One imperative sentence: what to do or avoid next time

### Metadata
- Source: conversation | user_feedback | error | review | research | simplify-and-harden
- Related Files: relative/path.ext
- Tags: tag1, tag2

---
```

Optional metadata fields (add only when genuinely useful for future search):
- See Also, Pattern-Key, Recurrence-Count, First-Seen, Last-Seen

### Categories

Recommended values:
- `correction`
- `insight`
- `knowledge_gap`
- `best_practice`

## Error entry

Append to `.learnings/ERRORS.md`:

```md
## [ERR-YYYYMMDD-XXX] short_name

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: area

### Summary
One sentence: what failed

### Error
```text
1–5 most relevant lines of error output only
```

### Context
One sentence: command attempted and key assumption that was wrong

### Suggested Fix
One imperative sentence: practical next step or workaround

### Metadata
- Reproducible: yes | no | unknown
- Related Files: relative/path.ext
- Tags: tag1, tag2

---
```

## Feature request entry

Append to `.learnings/FEATURE_REQUESTS.md`:

```md
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 timestamp
**Priority**: medium
**Status**: pending
**Area**: area

### Requested Capability
One sentence: what is missing

### User Context
One sentence: why it matters

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
One sentence: practical idea for adding it

### Metadata
- Frequency: first_time | recurring
- Related Features: helper_name, workflow_name
- Tags: tag1, tag2

---
```

## STATUS.md — session handoff

`STATUS.md` is **not** a structured-entry file. It is a single document overwritten (not appended) at the end of each work session so the next session starts informed.

Keep each item to **one line**. This is a handoff note, not documentation.

```md
# Project Status

Session handoff file. Update at the end of each work session so the next session starts informed.

**Last updated**: ISO-8601 timestamp
**Area**: primary work area

## Done

- (completed items, one line each)

## In Progress

- (items started but not finished — note blocker if any)

## Next

- (priority items the next session should tackle first)

## Decisions

- (key decisions made during this session that affect future work)

## Blockers

- (anything that prevents progress — missing deps, unanswered questions, external factors)
```

Rules:
- One line per item; no sub-lists, tables, or code blocks.
- `Done` items may be pruned after two sessions to keep the file short.
- `Decisions` captures *what* was chosen and *why* in one sentence — not design docs.
- Delete a section's placeholder line when it has real entries; leave the heading.

## Resolution block

When an issue is fixed or intentionally closed, append:

```md
### Resolution
- **Resolved**: ISO-8601 timestamp
- **Commit/PR**: commit hash, PR number, or `N/A`
- **Notes**: concise outcome summary
```

## Promotion markers

Use these additions when applicable.

### Promoted into project guidance

```md
**Status**: promoted
**Promoted**: AGENTS.md
```

Other valid promotion targets include `CLAUDE.md`, `.github/copilot-instructions.md`, or another persistent instruction file.

### Promoted into a reusable skill

```md
**Status**: promoted_to_skill
**Skill-Path**: knowledge/skill-name
```

## Recurrence updates

When you encounter the same pattern again, prefer updating the existing entry:
- increment `Recurrence-Count`
- set `Last-Seen`
- add the new task or file to metadata
- add `See Also` only when the pattern spans multiple related entries
