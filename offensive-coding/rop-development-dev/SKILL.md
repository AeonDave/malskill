---
name: rop-development
description: "Build, debug, and harden practical Return-Oriented Programming chains for x86-64 Linux and Windows targets: gadget discovery, calling-convention-correct chain construction, stack pivoting, leak-first ASLR bypass workflows, NX/DEP bypass via ret2libc/ret2syscall/VirtualProtect-NtProtectVirtualMemory, and mitigations-aware reliability tuning (PIE, RELRO, CET/Shadow Stack, CFG). Use when triaging crashes into exploitability, assembling first-stage infoleaks, selecting between ROP/JOP/SROP, validating gadget quality with Ropper/ROPgadget/pwntools, or porting chains across binaries/builds. Includes reliability-focused guidance on unwind-aware gadget vetting, deterministic selection over random gadget lottery, safety floors for stack math, and fallback cascades when ideal gadgets are absent."
license: MIT
compatibility: "x86-64 Linux (glibc) and x86-64 Windows user-mode. ARM64, kernel ROP, and browser JIT-ROP are out of scope."
metadata:
  author: AeonDave
  version: "1.0"
  category: exploitation
  language: c,cpp,rust,go,python,asm
---

# ROP Development

Goal: produce **reliable, reproducible chains** — not one-shot lucky payloads. Build from ABI facts, memory disclosures, and deterministic gadget policies.

## When to activate

- You need a chain for `ret2libc`, `ret2syscall`, `ret2csu`, SROP, or Windows API-call ROP (`VirtualProtect`, `NtProtectVirtualMemory`)
- Exploit crashes exist but NX/DEP + ASLR/PIE prevent direct shellcode
- Gadget discovery returns too many noisy candidates and chain stability is poor
- A working chain breaks across OS versions or minor binary rebuilds
- You must reason about CET/Shadow Stack / CFG feasibility before investing in ROP

## Core operating model

1. **Establish control primitive**: RIP control + controllable stack window.
2. **Choose objective**:
   - Leak addresses (stage 1) for ASLR/PIE
   - Invoke function/syscall with controlled arguments (stage 2)
   - Change memory perms (RW->RX) or pivot to existing executable pages
3. **Collect gadgets deterministically** (Ropper/ROPgadget/pwntools), score, then freeze selection.
4. **Assemble chain using exact ABI** (register args, stack alignment, shadow space on Windows x64).
5. **Validate under debugger and rerun multiple times** against same binary + randomized layouts.
6. **Generalize** by replacing hardcoded addresses with leak-derived bases and symbol offsets.

### Agentic execution loop (recommended)

1. **Survey pass**: protections, ABI, candidate primitives, chain budget (input length / bad chars).
2. **Hypothesis**: pick the shortest viable route (e.g., `ret2libc` vs `ret2csu` vs `ret2dlresolve` vs SROP).
3. **Prototype**: build the smallest chain that proves one objective (single leak or single call).
4. **Instrument**: log gadget addresses, leak bytes, parsed base, and alignment state (`rsp % 16`).
5. **Replan**: if a gate fails (canary, full RELRO, CET/CFG), switch route early rather than extending a broken chain.
6. **Stabilize**: replay locally with randomization, then with remote-like libc/loader parity.

## Chain patterns that actually survive

### Leak-first (preferred)

- Stage 1: call a known print/write primitive (`puts@plt`, `write`, etc.) on GOT/IAT pointer.
- Compute module base from leak.
- Stage 2: build final chain from base + offsets.

Use this by default on ASLR/PIE targets instead of guessing static offsets.

### ret2libc / ret2syscall (Linux)

- `pop rdi; ret` -> `/bin/sh` -> `system`, or
- syscall chain: set `rax=59`, `rdi=/bin/sh`, `rsi=0`, `rdx=0`, then `syscall; ret`.

### ret2csu (ELF with limited gadgets)

Use `__libc_csu_init` sequences to load multiple registers when clean `pop` gadgets are missing.

### Windows API-call ROP

- Build register/stack state for `VirtualProtect` or `NtProtectVirtualMemory`.
- Respect x64 calling convention and stack alignment.
- Prefer module-backed return sites/gadgets for better call-stack plausibility.

## Mitigation-aware decisions

- **NX/DEP on, no leak yet**: prioritize infoleak stage.
- **PIE + full ASLR**: absolute gadget addresses are disposable; keep only relative offsets.
- **Full RELRO**: avoid GOT overwrite plans; use call-oriented chains/leaks instead.
- **No/Partial RELRO**: `ret2dlresolve` can be a strong option when direct libc resolution/leaks are constrained.
- **CET Shadow Stack**: classic RET-chain often non-viable without a compatible bypass primitive.
- **CFG (Windows)**: indirect call targets must pass CFG checks; prefer allowed call edges or syscall-oriented paths.

If CET/CFG blocks your intended path, pivot early to alternate technique (JOP/SROP/data-only).

## Gadget quality rules

- Prefer shortest side-effect-free gadgets.
- Reject gadgets that clobber required registers unless immediately restored.
- Avoid random candidate picking: **sort + score + choose deterministically**.
- Preserve a strict fallback cascade (module A -> B -> C) when ideal gadget not found.
- Re-verify every selected gadget after binary/toolchain updates.

## Reliability checklist

- Stack 16-byte aligned at each call boundary.
- Bad bytes filtered at payload generation time.
- Chain survives repeated runs (at least 20 local iterations).
- Leak parsing robust to partial output / newline differences.
- All hardcoded bases removed before finalization.
- Local environment mirrors target runtime (`libc`/loader parity) before remote claims.
- Ifunc-sensitive offsets (`mem*`, `str*` families) validated at runtime when relevant.

## Debug loop

1. Build minimal chain (single call objective).
2. Break before first gadget; inspect stack and registers.
3. Single-step gadget transitions; confirm intended side effects only.
4. Expand chain one block at a time.
5. Record failure class: bad pivot, alignment, clobber, wrong base, mitigations.

## Anti-patterns

- Treating ROP as static addresses under ASLR/PIE.
- Overlong chains when a shorter call-oriented path exists.
- Mixing conventions (SysV vs Windows x64) in cross-platform exploits.
- Ignoring tool disagreement (Ropper vs ROPgadget) without byte-level verification.
- Shipping chains not tested under randomized layouts.

## Resources

- [references/tooling-and-workflow.md](references/tooling-and-workflow.md)
- [references/reliability-patterns.md](references/reliability-patterns.md)
- [references/examples-and-resources.md](references/examples-and-resources.md)
