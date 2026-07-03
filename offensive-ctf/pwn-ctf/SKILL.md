---
name: pwn-ctf
description: "Lab/CTF: pwn/binary challenges; native binaries, memory corruption, format strings, heap/ROP/SROP, shellcode artifacts, seccomp, kernel labs."
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
3. Load the closest top-level reference for the dominant primitive (`overflow.md`, `rop.md`, `heap.md`, `heap-fsop.md`, `relro-aslr-relocations.md`, `sandbox.md`, `kernel.md`, `exotic-arch.md`, `advanced-primitives.md`, `weird-machines.md`, `windows-pwn.md`).
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

## Category-specific quick pivots

- Triage binary and mitigations first; prove exact controlled primitive before payload engineering.
- Build exploit in stages: local repro, info leak, base calculation, control-flow/data-only effect, remote adaptation.
- Keep offsets, libc/loader assumptions, and environment drift explicit.
- For stateful exploits, keep leaks, allocator shaping, staging, and the trigger on one connection unless process boundaries are proven irrelevant. Load `references/stateful-exploit-campaigns.md` when later stages depend on earlier menu actions, sort order, allocator history, or live stack state.
- Treat emulators, permutation models, and offline address calculations as candidate generators. Promote a candidate only after a live breakpoint snapshot proves the exact call site, register arguments, target memory, return state, and next reachable stage.
- If `_dl_fixup`, `link_map`, dynamic tags, forged symbols, or an unresolved PLT entry become an endgame, load `references/dynamic-linker-resolver-pivots.md`. Prove a reachable lazy call in the final process state before building resolver metadata.
- Harness reliability: anchor each response parser on a *stable* token (the menu reprint), not the input prompt the previous step already consumed — a swallowed delimiter desyncs the next `recvuntil` and reads as a flaky exploit, usually papered over with long timeouts instead of fixed. Parse binary leaks over raw pipes or the live socket, never a pty (a pty mangles non-printable bytes).
- For local ground truth during development — PIE/heap/libc bases and arbitrary R/W to validate offsets before wiring the leak — read `/proc/<pid>/{maps,mem}` directly instead of trusting the exploit's own parsed values.
- If RELRO, GOT/PLT, relocation tables, or leakless partial overwrites appear, load `references/relro-aslr-relocations.md` before deciding the final target.
- If shellcode has a byte blacklist (filter function rejecting specific bytes), load `references/shellcode-filtering.md` first — decode the blacklist semantics, find safe XOR/ADD encoding, use register-based string construction to avoid blocked opcodes and string literals.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve coverage by using the top-level references in `references/` and keeping cross-links between them consistent.
- Keep challenge/platform/competition names out of notes and generated reports.

## Failure modes to avoid

- **Never declare a vector "impossible" or "dead" by reasoning.** Impossibility and reachability are decided by dynamic evidence only — code-path enumeration is always incomplete, so deductive impossibility proofs are almost always wrong. A "dead vector" claim requires a *failing live test*, not an argument. If you write "X can't work leaklessly/deterministically" or "nothing reaches Y", rewrite it as "X untested — run the discriminating experiment," then run it. Repeated impossibility arguments are the signal to hook everything and fuzz, not to write a longer proof.
- **Prove reachability by hook + fuzz, not deduction.** For "does anything call Y", "can malloc return Z", "is this slot/gadget reached": breakpoint Y (and every candidate call site at once) and vary inputs — huge/boundary numeric tokens, error paths, allocation/scratch-buffer thresholds, locale. Internal parser and buffer growth introduce calls absent from normal input. Only "no hit after adversarial fuzzing" counts as unreachable.
- **Drive to end-to-end execution early, then fix the latest crash.** After components verify in isolation, fire the *whole* chain and iterate: at each fault read `x/i $pc`, `rsp & 0xf`, and the faulting field, fix that one point, re-run. Late bugs — resolver-vs-`call` stack parity (`movaps`), controlled bytes overlapping a lock/pointer/terminator field, parser overwriting your string — surface only in a full run, never in isolated tests.
- **Keep a facts ledger and re-apply every proven fact to each later sub-chain.** Carry forward every runtime fact (live offsets, register snapshots, alignment quirks, call-site parity, deterministic pointers). A fix found in one context is usually needed again in the final chain; forgetting your own earlier finding is a self-inflicted loss.
- **Re-read this skill's own pivots when the endgame matches one.** If loader/`_dl_fixup`/forged-symbol, stateful, or partial-overwrite signals appear, load the matching reference *before* concluding the path fails — the guidance to prove reachability lives there, not in your head.

## Resources

- [references/advanced-primitives.md](references/advanced-primitives.md) — advanced edge cases: seccomp oddities, VM/JIT/interpreter bugs, runtime pivots, and data-reinterpretation tricks that do not fit cleanly under the core references.
- [references/dynamic-linker-resolver-pivots.md](references/dynamic-linker-resolver-pivots.md) — load when a leakless chain redirects loader metadata, forges dynamic symbols, triggers lazy resolution through a library path, or chains multiple resolver calls.
- [references/exotic-arch.md](references/exotic-arch.md) — RISC-V, ARM32, ARM64, and MIPS exploitation notes: register conventions, shellcode, gadget patterns, and architecture-specific pitfalls.
- [references/format-string.md](references/format-string.md) — format-string exploitation workflow: leaks, arbitrary writes, staged loops, and hardened-binary pivots.
- [references/heap.md](references/heap.md) — heap exploitation core: bins, safe-linking bypass strategy, modern chains, and allocator-specific notes.
- [references/heap-fsop.md](references/heap-fsop.md) — FSOP-focused heap chains and modern glibc stream abuse patterns.
- [references/kernel.md](references/kernel.md) — kernel exploitation notes: primitives, mitigation-aware pivots, and practical escalation paths.
- [references/overflow.md](references/overflow.md) — stack/global/OOB overflow patterns and mitigation-aware exploitation flow.
- [references/relro-aslr-relocations.md](references/relro-aslr-relocations.md) — ELF RELRO, GOT/PLT, relocation addends, ASLR-invariant partial overwrites, and multi-run reliability gates.
- [references/rop.md](references/rop.md) — x86-64 ROP and shellcode flow: leaks, pivots, chain assembly, and constrained environments.
- [references/sandbox.md](references/sandbox.md) — restricted-environment escapes, proc-based pivots, and command-execution constraints.
- [references/shellcode-filtering.md](references/shellcode-filtering.md) — byte-blacklist bypass: blacklist semantic analysis, XOR/ADD register-based encoding, alternative syscall construction, blocked instruction substitutions, and ORW shellcode template for filtered execve.
- [references/stateful-exploit-campaigns.md](references/stateful-exploit-campaigns.md) — load when an exploit depends on same-process state, allocator/call-site drift, deterministic data permutations, staged pivots, or probabilistic remote retries.
- [references/weird-machines.md](references/weird-machines.md) — emulator, interpreter, ML-dispatch, bit-flip, constrained-shellcode, and data-reinterpretation exploitation patterns.
- [references/windows-pwn.md](references/windows-pwn.md) — Windows-native exploitation notes: SEH/DEP bypass, CFG-aware call-target hijacks, PEB-walk shellcode, and privilege-abuse pivots after code execution.
- [references/wasm-pwn.md](references/wasm-pwn.md) — WASM binary exploitation under wasmtime/wasmer: linear memory OOB, shadow stack overflow, function table index overwrite.
