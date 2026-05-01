# Reliability patterns for ROP engineering

These are reusable engineering patterns for making ROP chains stable across rebuilds, targets, and environments.

## 1) Deterministic gadget selection beats gadget lottery

Gather candidates, score them, sort them, then pick deterministically.

Apply to ROP:
- Use stable ranking criteria (side effects, length, clobbers, alignment impact).
- Keep randomization out of production chain selection.
- Log candidate counts and rejection reasons.

## 2) Unwind-aware validation as a gadget quality filter

When stack-walk plausibility matters, prefer candidates in well-formed functions with coherent unwind metadata.

Apply to ROP:
- Reject candidates tied to unstable unwind/call-stack behavior.
- Prefer gadget locations that remain valid across minor binary updates.

## 3) Fallback cascades prevent hard-fail fragility

Do not rely on a single ideal gadget source.

Apply to ROP:
- Define fallback search domains up front (main module -> runtime library -> secondary modules).
- Keep explicit “last resort” branches instead of aborting when one source lacks ideal gadgets.

## 4) Safety floors for stack math

Use explicit minimum bounds for pivots and stack argument regions.

Apply to ROP:
- Define minimum safe pivot displacement and argument area boundaries.
- Fail closed when chain geometry violates these bounds.

## 5) Separate transfer logic from execution logic

Keep leak/resolve, pivoting, and call/syscall invocation modular.

Apply to ROP:
- Easier debugging and portability between targets.
- You can replace one primitive without rewriting the full chain.

## 6) Instrumentation-first debugging

Reliability work needs counters and one-shot diagnostics.

Apply to ROP:
- Log selected gadgets, rejected candidates, and mitigation-relevant decisions.
- Keep first-run diagnostics to quickly classify failures.

## 7) Advanced chain patterns for hardened targets

When basic ret2libc fails due to missing gadgets or mitigations:

- **ret2dlresolve**: No libc leak needed; craft fake relocation entries to have dynamic linker resolve `system`. Most practical when RELRO is not full and resolver path is still exploitable in the target setup.
- **SROP (Sigreturn ROP)**: Set all registers in one go via `sigreturn` syscall. Need `syscall; ret` gadget, fake signal frame on stack. Useful when register-loading gadgets are scarce.
- **ret2main/ret2plt**: Continue execution after leak; jump back to `main` or PLT stub to restart process without ASLR re-randomization.
- **Stack pivot with mprotect (Linux)**: Chain to make stack RWX, then jump to shellcode. Use `pop rdi; pop rsi; pop rdx; ret` for mprotect args.
- **VirtualProtect/NtProtectVirtualMemory (Windows)**: Load registers for API call, respect x64 shadow space (32 bytes before call). Prefer non-ASLR DLL gadgets.

Fallback order (typical): leak-first ROP > ret2dlresolve (when RELRO/setup permits) > SROP > JOP if RET blocked by CET.

## 8) Mitigation-specific reliability floors

- **CET/Shadow Stack**: Test with `ret` gadgets in CET-compatible binaries; avoid if blocked.
- **CFG**: Verify indirect call targets are CFG-allowed; use syscall paths as fallback.
- **PIE + ASLR**: Always leak and compute bases; no hardcoded offsets.
- **Full RELRO**: Assume GOT overwrite paths are closed; pivot to leak/call-oriented alternatives.
- **Stack alignment**: Add dummy `ret` before calls to ensure 16-byte RSP alignment (SSE requirement in libc).