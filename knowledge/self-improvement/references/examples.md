# Examples

These examples use malskill-flavored scenarios, but the structure is portable.

## Learning: correction

```md
## [LRN-20260323-001] correction

**Logged**: 2026-03-23T09:15:00Z
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
Skill changes must be validated with quick_validate.py before finishing

### Details
While updating a skill, the work was reviewed before the validator was run.
The repository workflow expects quick validation after skill edits, and the
missed step increases the chance of shipping bad frontmatter or lingering TODOs.

### Suggested Action
After changing any skill, run the repository validator before closing the task.

### Metadata
- Source: user_feedback
- Related Files: AGENTS.md, knowledge/skill-creator/scripts/quick_validate.py
- Tags: skills, validation, workflow

---
```

## Learning: knowledge gap

```md
## [LRN-20260323-002] knowledge_gap

**Logged**: 2026-03-23T10:05:00Z
**Priority**: medium
**Status**: resolved
**Area**: bof

### Summary
C BOF and C++ BOF guidance live in different skill roots and should not be merged casually

### Details
A BOF-related task initially assumed the same guidance applied equally to the
C and C++ skill folders. The repository keeps them separate because build,
patterns, and examples differ in important ways.

### Suggested Action
Check the specific BOF skill folder before reusing patterns across languages.

### Metadata
- Source: review
- Related Files: bof/c-bof/SKILL.md, bof/cpp-bof/SKILL.md
- Tags: bof, c, cpp, skill-boundaries

### Resolution
- **Resolved**: 2026-03-23T10:20:00Z
- **Commit/PR**: N/A
- **Notes**: Knowledge aligned; no code change required

---
```

## Error entry

```md
## [ERR-20260323-001] skill_validator

**Logged**: 2026-03-23T11:10:00Z
**Priority**: high
**Status**: pending
**Area**: tooling

### Summary
Skill packaging blocked because unresolved TODO markers remained in reference files

### Error
```text
[WARNING] Unresolved TODO in references/examples.md — resolve before packaging
```

### Context
- Command: `python knowledge/skill-creator/scripts/package_skill.py knowledge/self-improvement`
- The validator runs before packaging
- A copied template still contained placeholder content

### Suggested Fix
Resolve placeholder text first, then rerun validation before packaging.

### Metadata
- Reproducible: yes
- Related Files: knowledge/self-improvement/references/examples.md
- Tags: validator, packaging, skills

---
```

## Feature request entry

```md
## [FEAT-20260323-001] learning-entry-validator

**Logged**: 2026-03-23T12:00:00Z
**Priority**: medium
**Status**: pending
**Area**: workflow

### Requested Capability
Validate `.learnings/` entries for required fields and enum values

### User Context
Long-running sessions accumulate a lot of notes. A lightweight validator would
keep the log consistent and easier to review across sessions.

### Complexity Estimate
medium

### Suggested Implementation
Add a Python helper that scans the three markdown files and checks headings,
status values, priority values, and required sections.

### Metadata
- Frequency: recurring
- Related Features: self-improvement scripts
- Tags: validation, learnings, automation

---
```

## Promoted learning

```md
## [LRN-20260323-003] best_practice

**Logged**: 2026-03-23T12:30:00Z
**Priority**: high
**Status**: promoted
**Promoted**: AGENTS.md
**Area**: workflow

### Summary
Validate changed skills before finishing the task

### Details
This repository treats skill validation as a required closeout step.
Skipping it causes preventable review churn.

### Suggested Action
Run the validator after every skill edit and fix any warnings before packaging.

### Metadata
- Source: review
- Related Files: AGENTS.md, knowledge/skill-creator/scripts/quick_validate.py
- Tags: workflow, skills, validation

---
```

## Promoted to skill

```md
## [LRN-20260323-004] best_practice

**Logged**: 2026-03-23T13:05:00Z
**Priority**: high
**Status**: promoted_to_skill
**Skill-Path**: knowledge/self-improvement
**Area**: workflow

### Summary
Long multi-session coding work benefits from structured learning capture and review

### Details
Repeated sessions were spending time rediscovering earlier fixes, conventions,
and workarounds. A dedicated skill provides a repeatable workflow for logging,
reviewing, promoting, and extracting durable knowledge.

### Suggested Action
Use a shared self-improvement workflow whenever long tasks span multiple sessions.

### Metadata
- Source: conversation
- Related Files: knowledge/self-improvement/SKILL.md
- Tags: workflow, memory, sessions, skills

---
```
