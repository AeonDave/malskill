---
name: reverse-ctf
description: "Lab/CTF: reverse challenges; compiled binaries, bytecode, mobile/firmware, custom VMs, packed samples, anti-debug, validators."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Reverse CTF

Goal: solve reverse-engineering CTF tasks with professional methodology, curated challenge patterns, and reproducible evidence.

## When this skill applies

- compiled binaries, bytecode, mobile apps, firmware blobs, custom VMs, packed samples, obfuscated scripts, anti-debug logic, or validation algorithms
- tasks requiring static/dynamic analysis, algorithm extraction, patching, emulation, or symbolic execution

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load targeted references only for deep technique details.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `reversing-technique`
- `crypto-technique`
- `forensic-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and specialized reverse-CTF patterns.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `ghidra`
- `radare2`
- `binaryninja`
- `gdb`
- `x64dbg`
- `frida`
- `dnspy`
- `apktool`
- `jadx`
- `binwalk`
- `checksec`
- `strings`
- `objdump`
- `readelf`
- `upx`
- `patchelf`
- `strace`
- `ltrace`
- `capa`
- `sagemath`
- `openssl`

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
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

Each reference is one reversing lane. Load the file matching your immediate task; cross-links are for adjacent pivots after the first signal.

- [references/tools.md](references/tools.md) — tool routing across the whole loop: triage, Ghidra/radare2/Binary Ninja, GDB/lldb/x64dbg, Frida/angr/Triton, Unicorn/Qiling, oracle breakpoints, bytecode/managed tooling, packers/protectors, deobfuscation, diffing, patching.
- [references/languages.md](references/languages.md) — language-binary recognition and workflow: Go/Rust/Swift/D/C++, Kotlin/JVM/Haskell/Nuitka/.NET, Python bytecode/WASM/esolangs, GNU Make, UEFI.
- [references/platforms.md](references/platforms.md) — environment-specific reversing: Apple/Mach-O/iOS, firmware/embedded, kernel drivers, Android apps (JNI/DEX/Frida), desktop bundles (Electron/Tauri/SGX), game engines, exotic architectures.
- [references/anti-analysis.md](references/anti-analysis.md) — anti-debug/anti-VM/anti-DBI/code-integrity detection, anti-disassembly, the check→bypass playbook, and signal/handler runtime tricks.
- [references/patterns.md](references/patterns.md) — reusable reversing patterns: custom VMs, obfuscation/memory, byte transforms and keystreams, constraint/crypto recovery, runtime oracles and side-channels, hidden control flow.
