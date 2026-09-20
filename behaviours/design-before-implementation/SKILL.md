---
name: design-before-implementation
description: "Resolve design uncertainty before a substantial change. Use when requirements, interfaces, alternatives, or success criteria are unclear; skip a separate design phase for an already specified local fix."
license: MIT
compatibility: "Agent workflow guidance for coding, skill curation, and authorized security work."
metadata:
  author: AeonDave
  version: "1.1"
---

# Design Before Implementation

Identify the decisions that could cause rework before implementing them. Match the design effort to the uncertainty and consequences.

## Establish the contract

- Inspect the current implementation, applicable instructions, and relevant tests before proposing a replacement.
- State the requested outcome, affected interfaces, constraints, and how completion will be checked.
- Separate independent deliverables only when that clarifies ownership, dependencies, or validation.
- Ask about missing information only when it materially changes scope, authorization, data integrity, or a costly design choice. Continue independent work while waiting.

## Choose and execute

Compare alternatives when a real tradeoff remains; do not manufacture options for a settled requirement. Record the selected approach and the assumption that would invalidate it.

An implementation request can already authorize routine design decisions and reversible edits. Do not insert a new approval gate solely because several files change. Honor an explicit design-only request and any actual restricted action.

For a substantial design, summarize the outcome, approach, interfaces/artifacts, validation, and unresolved decisions. Omit empty sections. A short explanation may suffice for a local change.

Load [references/design-gates.md](references/design-gates.md) when reviewing a substantial design or resolving contradictory requirements. Use `implementation-planning` when dependencies or a handoff warrant an executable plan.
