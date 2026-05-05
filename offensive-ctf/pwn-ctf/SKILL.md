---
name: pwn-ctf
description: "Challenge-solving methodology for binary-exploitation challenge solving. Integrates reversing-technique, vuln-exploit-technique, fuzzing-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on binary-exploitation challenge solving tasks involving native binaries, remote services, memory corruption, format strings, heap bugs, ROP/SROP, shellcode, seccomp, kernel primitives, or sandbox escapes."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Pwn CTF

Goal: solve binary-exploitation challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- native binaries, remote services, memory corruption, format strings, heap bugs, ROP/SROP, shellcode, seccomp, kernel primitives, or sandbox escapes
- tasks requiring controlled crash reproduction, primitive upgrade, mitigation bypass, and exploit harnesses

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `reversing-technique`
- `vuln-exploit-technique`
- `fuzzing-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/network/pwntools`
- `offensive-tools/rev/gdb`
- `offensive-tools/rev/radare2`
- `offensive-tools/rev/ghidra`
- `coding/asm-patterns`
- `coding/asm-testing`
- `offensive-coding/rop-development-dev`
- `offensive-coding/heap-exploitation-dev`
- `offensive-coding/shellcode-dev`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Triage binary and mitigations first; prove exact controlled primitive before payload engineering.
- Build exploit in stages: local repro, info leak, base calculation, control-flow/data-only effect, remote adaptation.
- Keep offsets, libc/loader assumptions, and environment drift explicit.

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
- [references/imported/advanced-exploits-2.md](references/imported/advanced-exploits-2.md) — preserved, debrandized imported technique material.
- [references/imported/advanced-exploits-3.md](references/imported/advanced-exploits-3.md) — preserved, debrandized imported technique material.
- [references/imported/advanced-exploits-4.md](references/imported/advanced-exploits-4.md) — preserved, debrandized imported technique material.
- [references/imported/advanced-exploits-5.md](references/imported/advanced-exploits-5.md) — preserved, debrandized imported technique material.
- [references/imported/advanced-exploits.md](references/imported/advanced-exploits.md) — preserved, debrandized imported technique material.
- [references/imported/advanced.md](references/imported/advanced.md) — preserved, debrandized imported technique material.
- [references/imported/field-notes.md](references/imported/field-notes.md) — preserved, debrandized imported technique material.
- [references/imported/format-string.md](references/imported/format-string.md) — preserved, debrandized imported technique material.
- [references/imported/heap-fsop.md](references/imported/heap-fsop.md) — preserved, debrandized imported technique material.
- [references/imported/heap-techniques-2.md](references/imported/heap-techniques-2.md) — preserved, debrandized imported technique material.
- [references/imported/heap-techniques.md](references/imported/heap-techniques.md) — preserved, debrandized imported technique material.
- [references/imported/kernel-bypass.md](references/imported/kernel-bypass.md) — preserved, debrandized imported technique material.
- [references/imported/kernel-techniques.md](references/imported/kernel-techniques.md) — preserved, debrandized imported technique material.
- [references/imported/kernel.md](references/imported/kernel.md) — preserved, debrandized imported technique material.
- [references/imported/overflow-basics.md](references/imported/overflow-basics.md) — preserved, debrandized imported technique material.
- [references/imported/rop-advanced.md](references/imported/rop-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/rop-and-shellcode.md](references/imported/rop-and-shellcode.md) — preserved, debrandized imported technique material.
- [references/imported/sandbox-escape.md](references/imported/sandbox-escape.md) — preserved, debrandized imported technique material.
