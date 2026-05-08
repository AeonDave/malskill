---
name: pwn-ctf
description: "Challenge-solving methodology for binary-exploitation challenge solving. Integrates reversing-technique, vuln-exploit-technique, fuzzing-technique, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on binary-exploitation challenge solving tasks involving native binaries, remote services, memory corruption, format strings, heap bugs, ROP/SROP, shellcode, seccomp, kernel primitives, or sandbox escapes."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Pwn CTF

Goal: solve binary-exploitation challenge solving tasks with professional offensive methodology and reproducible evidence.

## When this skill applies

- native binaries, remote services, memory corruption, format strings, heap bugs, ROP/SROP, shellcode, seccomp, kernel primitives, or sandbox escapes
- tasks requiring controlled crash reproduction, primitive upgrade, mitigation bypass, and exploit harnesses

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load the closest top-level reference for the dominant primitive (`overflow.md`, `rop.md`, `heap.md`, `heap-fsop.md`, `sandbox.md`, `kernel.md`, `exotic-arch.md`, `advanced-primitives.md`, `weird-machines.md`, `windows-pwn.md`).
4. Load only top-level references in `references/`.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `reversing-technique`
- `vuln-exploit-technique`
- `fuzzing-technique`

Use these as decision engines. This skill adds challenge-oriented triage and time-boxing.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `pwntools`
- `gdb`
- `radare2`
- `ghidra`
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
- Preserve coverage by using the top-level references in `references/` and keeping cross-links between them consistent.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/advanced-primitives.md](references/advanced-primitives.md) — advanced edge cases: seccomp oddities, VM/JIT/interpreter bugs, runtime pivots, and data-reinterpretation tricks that do not fit cleanly under the core references.
- [references/exotic-arch.md](references/exotic-arch.md) — RISC-V, ARM32, ARM64, and MIPS exploitation notes: register conventions, shellcode, gadget patterns, and architecture-specific pitfalls.
- [references/field-notes.md](references/field-notes.md) — compact exploit playbook with fast pivots and cross-links to deeper references.
- [references/format-string.md](references/format-string.md) — format-string exploitation workflow: leaks, arbitrary writes, staged loops, and hardened-binary pivots.
- [references/heap.md](references/heap.md) — heap exploitation core: bins, safe-linking bypass strategy, modern chains, and allocator-specific notes.
- [references/heap-fsop.md](references/heap-fsop.md) — FSOP-focused heap chains and modern glibc stream abuse patterns.
- [references/kernel.md](references/kernel.md) — kernel exploitation notes: primitives, mitigation-aware pivots, and practical escalation paths.
- [references/overflow.md](references/overflow.md) — stack/global/OOB overflow patterns and mitigation-aware exploitation flow.
- [references/rop.md](references/rop.md) — x86-64 ROP and shellcode flow: leaks, pivots, chain assembly, and constrained environments.
- [references/sandbox.md](references/sandbox.md) — restricted-environment escapes, proc-based pivots, and command-execution constraints.
- [references/weird-machines.md](references/weird-machines.md) — emulator, interpreter, ML-dispatch, bit-flip, constrained-shellcode, and data-reinterpretation exploitation patterns.
- [references/windows-pwn.md](references/windows-pwn.md) — Windows-native exploitation notes: SEH/DEP bypass, CFG-aware call-target hijacks, PEB-walk shellcode, and privilege-abuse pivots after code execution.
- [references/wasm-pwn.md](references/wasm-pwn.md) — WASM binary exploitation under wasmtime/wasmer: linear memory OOB, shadow stack overflow, function table index overwrite.
