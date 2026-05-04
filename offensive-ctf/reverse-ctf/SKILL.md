---
name: reverse-ctf
description: >
  Challenge-solving methodology for reverse-engineering challenge solving. Integrates reversing-technique, crypto-technique, forensic-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on reverse-engineering challenge solving tasks involving compiled binaries, bytecode, mobile apps, firmware blobs, custom VMs, packed samples, obfuscated scripts, anti-debug logic, or validation algorithms.
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Reverse CTF

Goal: solve reverse-engineering challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- compiled binaries, bytecode, mobile apps, firmware blobs, custom VMs, packed samples, obfuscated scripts, anti-debug logic, or validation algorithms
- tasks requiring static/dynamic analysis, algorithm extraction, patching, emulation, or symbolic execution

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
- `crypto-technique`
- `forensic-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/rev/ghidra`
- `offensive-tools/rev/radare2`
- `offensive-tools/rev/binaryninja`
- `offensive-tools/rev/gdb`
- `offensive-tools/rev/x64dbg`
- `offensive-tools/rev/frida`
- `offensive-tools/rev/dnspy`
- `offensive-tools/forensic/capa`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Triage format, language/runtime, packing, and anti-analysis before deep decompilation.
- Define objective: recover secret, reconstruct algorithm, bypass check, emulate VM, or extract config.
- Cross-check static hypotheses dynamically and document exact validation signal.

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
- [references/imported/anti-analysis-ctf.md](references/imported/anti-analysis-ctf.md) — preserved, debrandized imported technique material.
- [references/imported/anti-analysis.md](references/imported/anti-analysis.md) — preserved, debrandized imported technique material.
- [references/imported/field-notes.md](references/imported/field-notes.md) — preserved, debrandized imported technique material.
- [references/imported/languages-compiled.md](references/imported/languages-compiled.md) — preserved, debrandized imported technique material.
- [references/imported/languages-platforms.md](references/imported/languages-platforms.md) — preserved, debrandized imported technique material.
- [references/imported/languages.md](references/imported/languages.md) — preserved, debrandized imported technique material.
- [references/imported/patterns-ctf-2.md](references/imported/patterns-ctf-2.md) — preserved, debrandized imported technique material.
- [references/imported/patterns-ctf-3.md](references/imported/patterns-ctf-3.md) — preserved, debrandized imported technique material.
- [references/imported/patterns-ctf.md](references/imported/patterns-ctf.md) — preserved, debrandized imported technique material.
- [references/imported/patterns-runtime.md](references/imported/patterns-runtime.md) — preserved, debrandized imported technique material.
- [references/imported/patterns.md](references/imported/patterns.md) — preserved, debrandized imported technique material.
- [references/imported/platforms-hardware.md](references/imported/platforms-hardware.md) — preserved, debrandized imported technique material.
- [references/imported/platforms.md](references/imported/platforms.md) — preserved, debrandized imported technique material.
- [references/imported/tools-advanced-2.md](references/imported/tools-advanced-2.md) — preserved, debrandized imported technique material.
- [references/imported/tools-advanced.md](references/imported/tools-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/tools-dynamic.md](references/imported/tools-dynamic.md) — preserved, debrandized imported technique material.
- [references/imported/tools-emulation.md](references/imported/tools-emulation.md) — preserved, debrandized imported technique material.
- [references/imported/tools.md](references/imported/tools.md) — preserved, debrandized imported technique material.
