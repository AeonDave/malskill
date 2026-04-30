# Tooling and workflow for ROP development

## Tool roles

- **ROPgadget**: fast broad gadget inventory, quick filtering by mnemonic/arch.
- **Ropper**: richer search/quality options and chain-helper modes.
- **pwntools.rop**: chain construction automation inside exploit scripts.
- **Debugger (gdb/windbg/x64dbg)**: ground truth for control flow and side effects.

Use at least two gadget tools, then verify bytes in debugger/disassembler.

## Practical workflow

1. Map binary protections (`checksec`, PE mitigations).
2. Confirm RIP control and controllable stack space.
3. Enumerate candidate pivots and argument-loading gadgets.
4. Build smallest possible objective chain (one function/syscall).
5. Add leak stage if ASLR/PIE present.
6. Convert to two-stage exploit with base recalculation.
7. Stress-run repeatedly with ASLR enabled.

## ABI reminders

### Linux x86-64 (SysV)

- Args: `rdi`, `rsi`, `rdx`, `rcx/r10`, `r8`, `r9` (function vs syscall differences)
- Syscall uses `rax` for syscall ID.

### Windows x64

- Args: `rcx`, `rdx`, `r8`, `r9`, then stack
- 32-byte shadow space required for many call patterns
- Keep stack aligned before indirect calls.

## Common failure signatures

- Crash on first gadget: bad pivot / wrong base.
- Crash on API boundary: misalignment or wrong calling convention.
- Works once then fails: hidden ASLR assumptions or gadget side effects.
- Leak stage unstable: output parsing or wrong symbol offset.

## Mitigations quick guide

- **NX/DEP**: prefer ROP/JOP over direct shellcode execution.
- **ASLR/PIE**: leak first, compute base, then chain.
- **RELRO**: avoid GOT overwrite dependence.
- **CET/Shadow Stack**: RET-chain may be blocked; reassess feasibility early.
- **CFG**: ensure indirect call targets are CFG-valid.
