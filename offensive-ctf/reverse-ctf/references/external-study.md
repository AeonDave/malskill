# External Study and Training — Reversing

Curated long-form learning material for reverse engineering. Use these to build
foundations and fill gaps between engagements. Workflow and decision logic stay
in the other `references/*.md` files; this list is for reading and labs.

## Foundations

- OST2 Arch1001 — x86-64 Assembly: https://ost2.fyi/Arch1001.html
  Free, full curriculum on x86-64 instruction set, encoding, calling conventions,
  and stack layout. Prerequisite for any deeper RE work.
- OST2 Arch2001 — User-mode debugging on Linux: https://ost2.fyi/Arch2001.html
  Companion to Arch1001 for GDB, ELF runtime, and live-program reasoning.
- guyinatuxedo — nightmare: https://guyinatuxedo.github.io/
  Long ordered set of pwn and RE challenges with full writeups. Use as study
  reference for technique patterns rather than for hint-leakage on live work.

## Reference data

- syscalls.w3challs (x86/x64 syscall reference): https://syscalls.w3challs.com/
  Per-arch syscall numbers, signatures, and registers. Keep open during stub
  identification, custom loader analysis, and ORW shellcode review.

## Talks and overviews

- gynvael — The Tragedy of Low-Level Exploitation:
  https://gynvael.coldwind.pl/?id=662
  Mitigation history; useful context when reading older RE writeups that assume
  pre-NX/ASLR/CFI behavior.
- CyberSecurityUP — Awesome Exploit Development:
  https://github.com/CyberSecurityUP/Awesome-Exploit-Development
  Curated index; many entries (anti-debug, packers, RE primers) are useful as
  RE study material even when not strictly exploit-dev.

## Heap and runtime structures (for RE of vulnerable code)

- ir0nstone — Binary Exploitation Notes: https://ir0nstone.gitbook.io/notes/
  Heap section gives the cleanest free explanation of glibc bin layout, useful
  when reversing allocator-heavy code or custom heap wrappers.
- shellphish — how2heap: https://github.com/shellphish/how2heap
  Source-level reference for what allocator metadata actually looks like at
  runtime; useful when matching dumps to glibc internals.

## Cross-links

- For exploitability handoff after RE confirms a vuln, see
  `references/binary-exploitation-capability.md` in
  `offensive-techniques/reversing-technique/` (or jump to
  `offensive-ctf/pwn-ctf/references/external-study.md` for the pwn-side reading
  list).
