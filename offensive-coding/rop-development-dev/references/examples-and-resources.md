# Practical examples and learning resources for ROP development

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

## Learning resources

- **ROP Emporium guide**: Practical fundamentals, common pitfalls (`movaps` alignment), and challenge progression.
- **pwn.college**: Structured modules for exploitation practice and tooling discipline.
- **CS6265 Advanced ROP**: Leak-first two-stage flow, multi-call chains, alignment troubleshooting, and ifunc caveats.
- **pwntools ROP docs**: Reproducible chain building APIs (`ROP`, `ret2csu`, SROP support).
- **pwntools ret2dlresolve docs**: Automated payload generation and required staging (`read` to payload area).
- **HackTricks ROP page**: Broad technique map (ret2lib/ret2syscall/stack pivot).
- **Stanford ROP note**: Historic but useful mental model for code-reuse mechanics on x64 Linux.

## Common pitfalls and fixes

- **Alignment crashes**: Add `ret` gadget to align RSP to 16 bytes before SSE-using functions.
- **Ifunc confusion**: Resolve actual function addresses with custom C probe, not GDB symbols.
- **CET blocks**: Switch to JOP (jump-oriented) or syscall-only chains.
- **CFG fails**: Use allowed call targets or avoid indirect calls.
- **Leak instability**: Robust parsing; handle partial outputs, newlines.

## Curated external references

- https://ropemporium.com/guide.html
- https://tc.gtisc.gatech.edu/cs6265/tut/tut06-02-advrop.html
- https://notes.qazeer.io/binary-exploitation/elf64_rop_leaks
- https://blog.1nf1n1ty.team/hacktricks/binary-exploitation/rop-return-oriented-programing
- https://docs.pwntools.com/en/stable/rop/rop.html
- https://docs.pwntools.com/en/stable/rop/ret2dlresolve.html
- https://ir0nstone.gitbook.io/notes/binexp/stack/return-oriented-programming/stack-alignment
- https://ir0nstone.gitbook.io/notes/types/stack/ret2dlresolve
- https://gitlab.com/x86-psABIs/x86-64-ABI

Use externally authored blogs as practical complements; prefer ABI/vendor/course docs for normative behavior.