---
name: solve-challenge-ctf
description: >
  Challenge-solving methodology for multi-category challenge triage and routing. Integrates recon-technique, forensic-technique, reversing-technique, web-exploit-technique, network-technique, wireless-technique, and crypto-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use for unknown bundles, remote services, partial hints, mixed artifacts, category-ambiguous tasks, ICS/OT traces, hardware captures, firmware, RF/SDR, or blockchain/Web3 artifacts; dispatches to dedicated category skills.
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Solve Challenge CTF

Goal: solve multi-category challenge triage and routing tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- unknown challenge bundles, remote services, partial hints, mixed artifacts, or category-ambiguous tasks
- dispatch involving blockchain/Web3, ICS/OT, hardware/embedded, RF/SDR, firmware, logic analyzer traces, industrial PCAPs, or smart-contract frontends
- work requiring first-pass triage and dispatch to the right specialized ctf skill

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `recon-technique`
- `forensic-technique`
- `reversing-technique`
- `crypto-technique`
- `web-exploit-technique`
- `network-technique`
- `wireless-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `ctf-solving/*-ctf`
- `ctf-solving/ics-ctf`
- `ctf-solving/hardware-ctf`
- `ctf-solving/blockchain-ctf`
- `ctf-solving/beginner-ctf`
- `coding/python-patterns`
- `coding/systematic-debugging`
- `knowledge/evidence-before-claims`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Use direct triage mode when the user provides concrete artifacts, URLs, endpoints, binaries, captures, or source.
- Use clarification mode when the prompt is abstract, the objective is unclear, or the user needs beginner-friendly first steps; dispatch to `ctf-solving/beginner-ctf` until the dominant category is clear.
- Classify by artifact and objective, not supplied category label.
- Route to one primary skill, keep secondary skills ready for pivots.
- Stop when objective proof is recovered and reproducible.
- Route Solidity/EVM/ABI/RPC/deployed addresses/contract frontends to `ctf-solving/blockchain-ctf`.
- Route ICS/SCADA/OT PCAPs, process logs, register dumps, setpoint histories, or isolated lab services to `ctf-solving/ics-ctf`.
- Route logic analyzer captures, UART/I2C/SPI/CAN/JTAG/SWD traces, firmware/SPI dumps, RF/SDR samples, CAD/G-code, side-channel data, or peripheral captures to `ctf-solving/hardware-ctf`.
- Keep `web-ctf`, `forensics-ctf`, and `misc-ctf` as secondary pivots when a task combines web UI, evidence recovery, or general puzzle transformations with these dedicated domains.
- When stuck, re-check the category assumption, inspect hidden files/metadata/comments/headers/alternate ports, and simplify to the smallest primitive before expanding the chain.
- Treat multiple recovered secret-like strings as candidates until validated by the intended workflow, corpus uniqueness, source path, or success oracle.

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
