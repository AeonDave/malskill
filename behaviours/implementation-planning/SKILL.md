---
name: implementation-planning
description: "Turn settled requirements into an executable plan. Use for work with dependencies, shared-file ownership, or a handoff; skip a separate plan for a straightforward local edit."
license: MIT
compatibility: "Agent workflow guidance for local repositories and authorized security work."
metadata:
  author: AeonDave
  version: "1.1"
---

# Implementation Planning

Make the next action and its completion condition clear without prescribing mechanics the implementer can choose.

## Build the plan

1. Extract acceptance criteria and constraints from the request or agreed design.
2. Identify the actual files and interfaces involved. Mark paths still to be discovered instead of inventing them.
3. Group work into verifiable outcomes; specify ordering only for real dependencies.
4. Assign one writer to shared files during concurrent work. Sequence dependent edits and recheck shared state before integration rather than declaring all shared-file work invalid.
5. Attach a proportionate check to each outcome. Use a reproducer for a bug fix when practical; use diff and structural checks for editorial changes.
6. Record consequential unknowns and the conditions requiring a scope or authorization decision.

For each task, include the outcome, affected files, dependencies, and acceptance check. Add commands only after checking their definitions or installed help. Include commit, review, or deployment steps only when requested or required by repository policy.

## Execute and maintain

An implementation request does not become a plan-only task merely because a plan is useful. Continue authorized work unless the user requested planning only or a material dependency is unresolved.

Update the remaining plan when evidence changes it. A failing baseline requires diagnosis and attribution, not automatic abandonment; continue independent safe tasks. Avoid splitting trivial actions into ceremony or treating a formatting preference as a blocker.
