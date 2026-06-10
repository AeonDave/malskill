# ROP quick chain templates and failure fixes

Load when you need a compact chain sketch or a fast fix for common reliability failures.

## Example chains

### Basic ret2libc (Linux x64)
- Gadget: `pop rdi; ret`
- Chain: leak addr -> compute libc base -> pop rdi (/bin/sh) -> system@libc
- Ensure stack alignment: add `ret` before system if needed.

### Windows VirtualProtect ROP
- Load RCX (addr), RDX (size), R8 (protect=0x40), R9 (oldprotect ptr)
- Call VirtualProtect; shadow space (32 bytes) on stack.
- Gadgets from kernel32.dll or non-ASLR modules.

### SROP for full register control
- Sigreturn syscall (rax=15) sets all regs from stack frame.
- Fake frame: rip points to next chain after sigreturn.
- Gadget: `syscall; ret`

### ret2dlresolve outline
- Fake link_map, reloc_offset.
- Invoke _dl_runtime_resolve with crafted args.
- Resolves arbitrary functions without prior leak.

## Common pitfalls and fixes

- **Alignment crashes**: Add `ret` gadget to align RSP to 16 bytes before SSE-using functions.
- **Ifunc confusion**: Resolve actual function addresses with custom C probe, not GDB symbols.
- **CET blocks**: Switch to JOP (jump-oriented) or syscall-only chains.
- **CFG fails**: Use allowed call targets or avoid indirect calls.
- **Leak instability**: Robust parsing; handle partial outputs, newlines.
