# Examples

Each entry is a **prevention rule**, not an incident report. Aim for 10–20 lines total.

## Learning: correction

```md
## [LRN-20260323-001] correction

**Logged**: 2026-03-23T09:15:00Z
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
Validate changed skills with quick_validate.py before finishing the task

### Details
Skipping validation after skill edits causes preventable review churn and bad frontmatter.

### Suggested Action
Run `quick_validate.py <skill-dir>` after every skill edit.

### Metadata
- Source: user_feedback
- Related Files: knowledge/skill-creator/scripts/quick_validate.py
- Tags: skills, validation

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
C BOF and C++ BOF skills have different build patterns and must not be mixed

### Details
The repository keeps them separate because compiler flags, DFR patterns, and examples differ.

### Suggested Action
Check the specific BOF skill folder before reusing patterns across C and C++.

### Metadata
- Source: review
- Related Files: bof/c-bof/SKILL.md, bof/cpp-bof/SKILL.md
- Tags: bof, c, cpp

---
```

## Learning: best practice (protocol-specific)

```md
## [LRN-20260323-003] best_practice

**Logged**: 2026-03-23T11:00:00Z
**Priority**: high
**Status**: pending
**Area**: offensive-tools

### Summary
DOWNLOAD and RUN responses must use type 2 (Job) messages, not type 1 (Command)

### Details
The server routes type 1 and type 2 differently; type 1 DOWNLOAD frames are silently dropped.

### Suggested Action
Check `pl_main.go` to verify expected message type before implementing any multi-frame command.

### Metadata
- Source: error
- Related Files: pl_main.go, Commander.cpp
- Tags: spectre, wire-format, download

---
```

## Error entry

```md
## [ERR-20260323-001] packaging_blocked

**Logged**: 2026-03-23T11:10:00Z
**Priority**: high
**Status**: pending
**Area**: tooling

### Summary
Skill packaging fails when unresolved TODO markers remain in reference files

### Error
```text
[WARNING] Unresolved TODO in references/examples.md — resolve before packaging
```

### Context
Ran `package_skill.py` before clearing template placeholders.

### Suggested Fix
Resolve all TODO markers before running the packager.

### Metadata
- Reproducible: yes
- Related Files: knowledge/self-improvement/references/examples.md
- Tags: validator, packaging

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
Validate `.learnings/` entries for required fields and allowed enum values

### User Context
Long sessions accumulate inconsistent entries; a lightweight validator would catch drift early.

### Complexity Estimate
medium

### Suggested Implementation
Add a Python script that scans the three markdown files and checks headings, statuses, and required sections.

### Metadata
- Frequency: recurring
- Tags: validation, learnings

---
```

## STATUS.md: session handoff

```md
# Project Status

Session handoff file. Update at the end of each work session so the next session starts informed.

**Last updated**: 2026-03-24T18:30:00Z
**Area**: offensive-tools

## Done

- Implemented Tier 1 commands (SHELL, RUN, PS) in C++ agent
- Fixed type 2 message framing for DOWNLOAD handler

## In Progress

- Rust agent Tier 1 stubs — SHELL and RUN done, PS pending

## Next

- Finish Rust PS handler
- Integration-test both agents against staging listener

## Decisions

- Use type 2 (Job) framing for all multi-frame responses; type 1 is command-only

## Blockers

- Staging listener cert expires 2026-03-28; renewal ticket filed
```

## Anti-pattern: what NOT to write

The following is **too verbose** for `.learnings/`. It reads like a postmortem, not a prevention rule:

```md
## BAD — do not write entries like this

### Summary
After generating C++ and Rust agents with the spectre protocol, the scaffold
compiles clean but ~40–65% of command handlers are stubs...

### Details
| Feature | C++ file | C++ status | Rust file | Rust status | Win32 API |
|---------|----------|------------|-----------|-------------|-----------|
| COMMAND_SHELL | Commander.cpp | resolved | commander.rs | stub | CreatePipe... |
| COMMAND_RUN | Commander.cpp | resolved | commander.rs | stub | CreateProcess... |
(... 20 more rows ...)

### What to do next time
After generating any new C++ or Rust spectre agent:
1. Read this entry immediately.
2. Work through Tier 1 top-to-bottom...
3. Use the reference beacon at D:\Sources\...
```

Problems: feature-status table (belongs in issues/docs), implementation details (belongs in code/references), local paths, reads like a project tracker instead of a reusable rule.

**Better version of the same knowledge:**

```md
### Summary
Generated spectre agents have stub-only command handlers; treat scaffold as non-functional until Tier 1 is implemented

### Details
Every generation leaves SHELL, RUN, PS, DOWNLOAD, and PROFILE as stubs. This is by design but easy to forget.

### Suggested Action
After generating a new agent, implement Tier 1 commands before any testing or deployment.
```
