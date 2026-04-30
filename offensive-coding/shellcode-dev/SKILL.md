---
name: shellcode-dev
description: "Design, build, test, and harden cross-platform shellcode workflows for Windows, Linux, and macOS across x64 and ARM64, with C/ASM/Python toolchains. Use when creating or reviewing shellcode stagers/loaders, PIC payloads, syscall-only routines, encoder/decoder stages, memory-permission transitions (mmap/mprotect/VirtualAlloc/Nt*), reflective loading paths, and emulator-based validation (Capstone/Keystone/Unicorn). Covers ABI constraints, calling conventions, bad-byte handling, staged execution, and practical debugging loops for exploit-dev and red-team R&D."
license: MIT
compatibility: "Windows 10/11 x64, Linux x64/aarch64, macOS x64/arm64. Architecture-specific syscall and ABI differences are mandatory."
metadata:
  author: malskill
  version: "1.0"
  category: offensive-coding
  language: asm,c,cpp,python,rust,go
---

# Shellcode Development (Windows/Linux/macOS)

Build shellcode as a constrained engineering problem: small PIC code, strict ABI behavior, reliable memory transitions, and reproducible test loops.

This skill is for **implementation and validation workflow**. It is not a vulnerability discovery skill.

## When to activate

- Writing or reviewing shellcode/stagers in ASM/C/Python pipelines
- Building cross-platform syscall-based payloads (Windows/Linux/macOS)
- Porting payloads between `x86_64` and `arm64`
- Handling bad-byte restrictions with encoder/decoder stages
- Implementing reflective/manual in-memory loading workflows
- Debugging crashes caused by calling-convention or stack-alignment mistakes
- Verifying payload behavior with emulator/disassembler tooling before runtime tests

If the task is specifically about BOFs, prefer `bof/c-bof` or `bof/cpp-bof` first. If it is specifically about stack masquerade or syscall gates, combine with `offensive-coding/stack-spoofing` or `offensive-coding/indirect-syscall`.

---

## Core workflow

1. **Define execution contract first**
   - Target OS + architecture + entry assumptions
   - Available registers, expected stack alignment, bad-byte set, max size
   - Whether network/file APIs are allowed or syscall-only is required

2. **Pick payload shape**
   - Single-stage (small, immediate execution)
   - Two-stage (tiny bootstrap + streamed body)
   - Reflective/in-memory loader path (PE/ELF/Mach-O aware)

3. **Implement ABI-correct stub**
   - Preserve required non-volatiles
   - Maintain alignment guarantees
   - Use position-independent data access only

4. **Validate in three layers**
   - Static: disassembly and byte checks
   - Emulation: deterministic instruction/memory behavior
   - Runtime: target OS debugger + telemetry sanity

5. **Harden incrementally**
   - Add only required obfuscation/encoding
   - Re-test after each hardening change
   - Keep a plain debug build to avoid blind debugging

---

## Platform rules that break payloads most often

### Windows x64

- Respect Microsoft x64 ABI and shadow space requirements.
- Syscall path expects `mov r10, rcx` before `syscall`.
- If using indirect syscalls, source `syscall;ret` from a clean `ntdll` gadget and keep SSN resolution runtime-based.
- Reflective loading must correctly parse PE exports/imports/relocations and section permissions.

### Linux x64/aarch64

- `mmap`/`mprotect` transitions are part of payload lifecycle; test all return paths.
- For x64 syscalls, syscall number/arg placement must match kernel ABI (`rax` + `rdi/rsi/rdx/r10/r8/r9`).
- For aarch64 syscalls, use `x8` for syscall number and `x0-x5` for args.
- Avoid assuming vDSO location or fixed helper addresses.

### macOS x64/arm64

- Syscall tables and calling details differ from Linux; validate against XNU sources/current targets.
- Treat Mach-O and dyld assumptions as version-sensitive.
- arm64 stack alignment and calling convention errors fail fast; emulate and runtime-test both.

---

## Encoder and polymorphism guidance

- Use encoding to satisfy transport/bad-byte constraints, not as a default.
- Keep decoder stubs minimal and architecture-appropriate.
- Polymorphism/metamorphism increases implementation risk and detection surface if overused.
- Prefer deterministic transforms you can regression-test over “clever” mutation logic.
- Map evasion assumptions to ATT&CK-style behavior expectations and verify with runtime telemetry.

---

## Python/C integration pattern

- Use Python (pwntools/Keystone/Capstone/Unicorn) for generation, assembly, disassembly, and emulation harnesses.
- Use C/C++ (or Rust/Go) wrappers for runtime loaders/injectors and platform APIs.
- Keep shellcode bytes and loader logic separable so you can swap payload versions quickly.
- Always retain one end-to-end harness that runs: `generate -> inspect -> emulate -> execute test`.

---

## Quality gates before shipping

- Byte-level constraints pass (`badchars`, size, null/newline policy)
- Stack/register invariants verified at entry/exit
- Memory permissions transitions are reversible and error-checked
- No hardcoded OS-build-specific syscall numbers unless explicitly pinned for research
- At least one emulator run and one real runtime debug pass on target architecture
- Crash artifacts and logs are reproducible with the same payload bytes

---

## Resources

- [references/platform-workflows.md](references/platform-workflows.md) — concrete Windows/Linux/macOS build and validation flows, including syscall and memory-transition checkpoints
- [references/tooling-and-labs.md](references/tooling-and-labs.md) — practical usage of pwntools, Capstone, Keystone, Unicorn, debugger loops, and test harness patterns
- [references/encoders-and-stagers.md](references/encoders-and-stagers.md) — staged payload patterns, bad-byte encoders, polymorphism trade-offs, and failure modes
- [references/evasion-patterns-from-projects.md](references/evasion-patterns-from-projects.md) — transferable shellcode-dev engineering patterns from real implementations (runtime SSN mapping, recycled syscall gates, DESYNC readiness checks, sleep masking pipelines, CFG-aware gadget handling)

### External references

- Microsoft x64 calling convention: `learn.microsoft.com/en-us/cpp/build/x64-calling-convention`
- Microsoft PE format: `learn.microsoft.com/en-us/windows/win32/debug/pe-format`
- ReflectiveDLLInjection: `github.com/stephenfewer/ReflectiveDLLInjection`
- Linux man-pages (`syscall`, `mmap`, `mprotect`, `vdso`): `man7.org`
- Apple XNU syscall source: `github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/syscalls.master`
- Pwntools docs: `docs.pwntools.com`
- Capstone/Keystone/Unicorn official docs and repos
- MITRE ATT&CK T1027.014 (Polymorphic Code)
