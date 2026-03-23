# Entry Formats

Use these formats to keep learnings searchable and consistent.

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
**Area**: workflow | repo-config | docs | tooling | programming | testing | knowledge | research | offensive-tools | bof

### Summary
One-line description of the learning

### Details
What happened, what was incorrect or missing, and what is now known

### Suggested Action
What to do differently next time

### Metadata
- Source: conversation | user_feedback | error | review | research | simplify-and-harden
- Related Files: relative/path.ext
- Tags: tag1, tag2
- See Also: LRN-YYYYMMDD-XXX
- Pattern-Key: stable.pattern.name
- Recurrence-Count: 1
- First-Seen: YYYY-MM-DD
- Last-Seen: YYYY-MM-DD

---
```

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
**Area**: workflow | repo-config | docs | tooling | programming | testing | knowledge | research | offensive-tools | bof

### Summary
Brief description of the failure

### Error
```text
Actual error output or the most relevant lines
```

### Context
- Command or operation attempted
- Inputs or assumptions
- Environment notes when relevant

### Suggested Fix
Practical next step or best known workaround

### Metadata
- Reproducible: yes | no | unknown
- Related Files: relative/path.ext
- See Also: ERR-YYYYMMDD-XXX
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
**Area**: workflow | repo-config | docs | tooling | programming | testing | knowledge | research | offensive-tools | bof

### Requested Capability
What is missing

### User Context
Why it matters and who would benefit

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
How the capability could be added

### Metadata
- Frequency: first_time | recurring
- Related Features: helper_name, workflow_name
- Tags: tag1, tag2

---
```

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
