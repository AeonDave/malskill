---
name: forensics-ctf
description: >
  Challenge-solving methodology for forensics and steganography challenge solving. Integrates forensic-technique, network-technique, reversing-technique, and wireless-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use for disk images, memory dumps, PCAPs, event logs, archives, media files, firmware-like blobs, steganography, and evidence recovery.
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Forensics CTF

Goal: solve forensics and steganography challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- disk images, memory dumps, PCAPs, event logs, archives, media files, firmware-like blobs, steganography, signals, RF/SDR captures, CAD/G-code, or peripheral captures
- artifact recovery, timeline reconstruction, embedded data extraction, traffic carving, or hidden-message analysis

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
- `network-technique`
- `reversing-technique`
- `wireless-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/forensic/volatility3`
- `offensive-tools/forensic/sleuth-kit`
- `offensive-tools/forensic/autopsy`
- `offensive-tools/forensic/zeek`
- `offensive-tools/network/wireshark`
- `offensive-tools/rev/binwalk`
- `offensive-tools/cryptography/cyberchef`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Preserve first: identify format, hash evidence, then choose disk, memory, network, or file workflow.
- Use metadata and timeline pivots before deep carving everything.
- For stego and signal tasks, test format-native structures before brute-force extraction.

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
- [references/imported/3d-printing.md](references/imported/3d-printing.md) — preserved, debrandized imported technique material.
- [references/imported/disk-advanced.md](references/imported/disk-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/disk-and-memory.md](references/imported/disk-and-memory.md) — preserved, debrandized imported technique material.
- [references/imported/disk-recovery.md](references/imported/disk-recovery.md) — preserved, debrandized imported technique material.
- [references/imported/linux-forensics.md](references/imported/linux-forensics.md) — preserved, debrandized imported technique material.
- [references/imported/network-advanced.md](references/imported/network-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/network.md](references/imported/network.md) — preserved, debrandized imported technique material.
- [references/imported/peripheral-capture.md](references/imported/peripheral-capture.md) — preserved, debrandized imported technique material.
- [references/imported/signals-and-hardware.md](references/imported/signals-and-hardware.md) — preserved, debrandized imported technique material.
- [references/imported/steganography.md](references/imported/steganography.md) — preserved, debrandized imported technique material.
- [references/imported/stego-advanced-2.md](references/imported/stego-advanced-2.md) — preserved, debrandized imported technique material.
- [references/imported/stego-advanced.md](references/imported/stego-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/stego-image.md](references/imported/stego-image.md) — preserved, debrandized imported technique material.
- [references/imported/windows.md](references/imported/windows.md) — preserved, debrandized imported technique material.
