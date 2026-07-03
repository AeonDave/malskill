---
name: writeup-ctf
description: "Lab/CTF: reproducible writeups; solved notes, command logs, artifacts, proof output, solver scripts, final reports, evidence checks."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Writeup CTF

Goal: produce reproducible challenge writeups with clear proof order, minimal noise, and reusable evidence.

## When this skill applies

- solved challenge notes, command logs, artifacts, proof output, exploit scripts, or final reports
- tasks requiring concise reconstruction, evidence-backed steps, and reusable lessons

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load the narrowest supporting reference only when the writeup task needs extra structure, packaging, or redaction guidance.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `forensic-technique`
- `evidence-before-claims`
- `verification-before-completion`

Use these as decision engines. This skill adds writeup structure, proof ordering, artifact packaging, and reproducibility discipline.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/structure-and-proof-order.md](references/structure-and-proof-order.md) — load when turning notes and solver output into one clean, reproducible proof path.
- [references/artifacts-redaction-and-packaging.md](references/artifacts-redaction-and-packaging.md) — load when deciding what scripts, screenshots, raw requests, hashes, and sanitized artifacts belong in the final package.
