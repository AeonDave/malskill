---
name: misc-ctf
description: "Lab/CTF: misc challenges; jails, encodings, esolangs, VMs, DNS oddities, Linux puzzles, Unicode, QR/audio, multi-stage artifacts."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Misc CTF

Goal: solve miscellaneous multi-domain challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- jails, encodings, esolangs, games, VMs, RF/SDR, DNS oddities, Linux privilege escalation puzzles, unicode tricks, QR/audio artifacts, or multi-stage puzzles
- problems where no single category dominates at first triage

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load debrandized imported references only for deep technique details.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `crypto-technique`
- `reversing-technique`
- `forensic-technique`
- `post-exploit-technique`
- `wireless-technique`
- `network-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `cyberchef`
- `netcat`
- `wireshark`
- `aircrack-ng`
- `kismet`
- `coding/python-patterns`
- `coding/systematic-debugging`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Solving discipline

- Favor artifact-first triage, shortest reproducible path, and an explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Classify the primitive, not the category label: parser, sandbox, encoding, RF, protocol, game logic, or host privilege boundary.
- Use shortest deterministic transform chain first; avoid speculative brute force until representation is known.
- For jail and VM tasks, map constraints then build minimal escape or emulator.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/bashjails.md](references/bashjails.md) — preserved, debrandized imported technique material.
- [references/ctfd-navigation.md](references/ctfd-navigation.md) — preserved, debrandized imported technique material.
- [references/dns.md](references/dns.md) — preserved, debrandized imported technique material.
- [references/encodings-advanced.md](references/encodings-advanced.md) — preserved, debrandized imported technique material.
- [references/encodings.md](references/encodings.md) — preserved, debrandized imported technique material.
- [references/games-and-vms-2.md](references/games-and-vms-2.md) — preserved, debrandized imported technique material.
- [references/games-and-vms-3.md](references/games-and-vms-3.md) — preserved, debrandized imported technique material.
- [references/games-and-vms-4.md](references/games-and-vms-4.md) — preserved, debrandized imported technique material.
- [references/games-and-vms.md](references/games-and-vms.md) — preserved, debrandized imported technique material.
- [references/linux-privesc.md](references/linux-privesc.md) — preserved, debrandized imported technique material.
- [references/pyjails.md](references/pyjails.md) — preserved, debrandized imported technique material.
- [references/rf-sdr.md](references/rf-sdr.md) — preserved, debrandized imported technique material.
