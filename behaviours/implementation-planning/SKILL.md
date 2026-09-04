---
name: implementation-planning
description: "Use after an approved design, spec, issue, or requirement set and before multi-step implementation. Produces bite-sized tasks with exact files, commands, verification gates, review checkpoints, and stop conditions for coding, skill curation, offensive tooling, or research automation."
license: MIT
compatibility: "Agent workflow guidance for local repositories and authorized security work."
metadata:
  author: AeonDave
  version: "1.0"
---

# Implementation Planning

A plan is executable context for a future worker with no memory of the conversation.

## Planning workflow

1. **Re-read the design or requirements** and list acceptance criteria.
2. **Map files/artifacts**: exact paths to create, modify, validate, or avoid.
3. **Decompose tasks**: each task should be independently understandable and verifiable.
4. **Write steps**: test/reproducer first where possible, implementation second, verification third.
5. **Add stop conditions**: unclear requirement, failing baseline, scope expansion, unsafe action, or missing dependency.
6. **Self-review**: check coverage, placeholders, path accuracy, type/name consistency, and validation commands.

## Task shape

Each task should include:

- **Goal**: one behavior or artifact.
- **Files**: exact paths and intended responsibility.
- **Steps**: small actions in order; avoid “do the appropriate thing”.
- **Verification**: command, expected outcome, or artifact check.
- **Commit/review gate**: what must be true before moving on.

## Plan quality gates

- No unresolved placeholders ("similar to previous") or undefined functions/types.
- No task that requires reading the entire prior conversation.
- No cross-task file conflicts; tasks must not mutate shared files in ways that depend on execution order.
- No hidden assumptions about scope, credentials, targets, or destructive actions.
- No bundled unrelated cleanup.
- Review spec compliance before code quality when delegating implementation.
- Block only on wrong artifact, stuck worker, or scope overreach — not style or formatting.
