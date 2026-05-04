---
name: writeup-ctf
description: >
  Challenge-solving methodology for reproducible challenge writeup generation. Integrates forensic-technique, evidence-before-claims, verification-before-completion with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on reproducible challenge writeup generation tasks involving solved challenge notes, command logs, artifacts, proof output, exploit scripts, or final reports.
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Writeup CTF

Goal: solve reproducible challenge writeup generation tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- solved challenge notes, command logs, artifacts, proof output, exploit scripts, or final reports
- tasks requiring concise reconstruction, evidence-backed steps, and reusable lessons

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `forensic-technique`
- `evidence-before-claims`
- `verification-before-completion`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `coding/test-driven-development`
- `knowledge/evidence-before-claims`
- `knowledge/verification-before-completion`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Write from evidence, not memory: artifact, command, output, interpretation.
- Separate dead ends from final path so future agents can reproduce without noise.
- Include exact verification signal and minimal solver/run steps.
- Prefer one complete solve path and, when code is needed, one complete solver that starts from provided challenge data and ends at the recovered objective.
- Keep the main path to 1-3 short steps unless the proof genuinely needs more structure.
- Include tool versions or environment notes only when they affect reproducibility.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve source coverage: every imported file is mapped in `references/source-coverage.md` and available in `references/imported/`.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/agentic-workflow.md](references/agentic-workflow.md) — category workflow, tool routing, and technique handoff.
- [references/source-coverage.md](references/source-coverage.md) — no-loss map of preserved imported source files and topics.
- [references/imported/source-skill.md](references/imported/source-skill.md) — preserved, debrandized imported technique material.
