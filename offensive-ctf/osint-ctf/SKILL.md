---
name: osint-ctf
description: "Challenge-solving methodology for open-source intelligence challenge solving. Integrates osint-technique, recon-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on open-source intelligence challenge solving tasks involving people, usernames, emails, domains, infrastructure, images, videos, geolocation, social-media clues, DNS history, or public records."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# OSINT CTF

Goal: solve open-source intelligence challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- people, usernames, emails, domains, infrastructure, images, videos, geolocation, social-media clues, DNS history, or public records
- research tasks requiring public-source correlation, confidence labels, and reproducible evidence trails

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `osint-technique`
- `recon-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/osint/sherlock`
- `offensive-tools/osint/maigret`
- `offensive-tools/osint/holehe`
- `offensive-tools/osint/ghunt`
- `offensive-tools/osint/theharvester`
- `offensive-tools/recon/shodan`
- `offensive-tools/recon/subfinder`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Define target entity and objective before searching: person, media, infrastructure, event, or organization.
- Use source independence and confidence labels to avoid false pivots.
- Archive exact URL, query, timestamp, and evidence artifact for reproducibility.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve source coverage: every imported file is mapped in `references/source-coverage.md` and available in `references/`.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/geolocation-and-media.md](references/geolocation-and-media.md) — preserved, debrandized imported technique material.
- [references/social-media.md](references/social-media.md) — preserved, debrandized imported technique material.
- [references/web-and-dns.md](references/web-and-dns.md) — preserved, debrandized imported technique material.
