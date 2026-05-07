---
name: design-before-implementation
description: "Use before creative or multi-file implementation work: new features, behavior changes, refactors, new skills, offensive tooling workflows, exploit chains, research pipelines, or architecture decisions. Clarifies intent, scope, alternatives, constraints, success criteria, and non-goals before coding or executing."
license: MIT
compatibility: "Agent workflow guidance for coding, skill curation, and authorized security work."
metadata:
  author: AeonDave
  version: "1.0"
---

# Design Before Implementation

Do not optimize the wrong plan. A short design prevents long rework.

## Hard gate

Before implementation, produce a design summary and get explicit or clearly implied approval unless the user gave exact step-by-step instructions or the change is a trivial single-edit fix.

## Design workflow

1. **Context scan**: inspect current structure, conventions, and constraints.
2. **Scope check**: split work that contains independent subsystems or targets.
3. **Clarify intent**: ask only the missing questions that affect design, safety, or data integrity.
4. **Options**: present 2-3 viable approaches with tradeoffs and a recommendation.
5. **Design summary**: architecture, data/control flow, touched areas, testing, risks, non-goals.
6. **Review gate**: resolve ambiguity, TODOs, contradictions, and scope creep before planning.

## Offensive and research focus

- Restate scope, allowed actions, noise/destructive limits, and evidence requirements.
- Prefer the smallest viable technique chain before expanding tooling.
- Separate reconnaissance, exploitability, tooling, validation, and reporting decisions.
- Stop when verification would require access or actions outside the approved boundary.

## Output shape

- **Goal**: one sentence.
- **Non-goals**: what this will not do.
- **Approach**: recommended option and why.
- **Interfaces/artifacts**: files, commands, reports, APIs, or evidence outputs.
- **Validation**: how success and failure will be proven.
- **Open questions**: only blockers or meaningful tradeoffs.

## Resources

Load on demand:

- `references/design-gates.md` — spec review checklist and common design failure modes.
