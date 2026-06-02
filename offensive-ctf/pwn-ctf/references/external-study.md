# External Study and Training — Pwn

Curated long-form learning material for binary exploitation. Use these to build
or refresh foundations between engagements; they are not in-engagement playbooks.
Topical pivots inside the repo stay in the other `references/*.md` files.

## Linux user-land

- ir0nstone — Binary Exploitation Notes: https://ir0nstone.gitbook.io/notes/
  Classic structured walk: ASLR/NX/canary, ROP, format strings, heap (tcache,
  fastbin, unsorted, large bins), house techniques, FSOP. Best free baseline.
- 0xxyc — binary-exploitation gitbook: https://0xxyc.gitbook.io/binary-exploitation/
  Companion to ir0nstone with extra worked examples.
- Karol Mazurek — Linux PWN methodology:
  https://karol-mazurek.medium.com/pwn-methodology-linux-2c9f1d3a6c97
  Compact decision-tree from triage to exploit; useful for review of own flow.
- PWN Tips & Tricks (Linux): https://gr4n173.gitbook.io/notes/pwn/pwn-tips-and-tricks
  Short snippets for recurring obstacles (small buffer, partial overwrite, libc
  fingerprinting, stack pivoting under FORTIFY).
- dayzerosec — getting started: https://dayzerosec.com/blog/2021/02/02/getting-started.html
  Roadmap and curated reading order across vuln research and exploit dev.

## Heap

- 0x434b — GLIBC heap exploitation overview (2025):
  https://0x434b.dev/glibc-heap-exploitation-overview-2025/
  Modern allocator state, tcache/safe-linking landscape, current chain choices.
- shellphish — how2heap: https://github.com/shellphish/how2heap
  Canonical PoC catalogue for every classical and modern house. Read source
  alongside `references/heap.md` and `offensive-coding/heap-exploitation-dev/`.
- heapwn cheatsheet: https://github.com/k0nrad/heapwn_Cheatsheet
  Bin layout, metadata, and check summary; handy printable.
- Research Innovations — Bypassing Safe-Linking:
  https://research.nccgroup.com/2022/03/16/bypassing-safe-linking/
  Pointer-mangling analysis and required leaks; complements
  `offensive-coding/heap-exploitation-dev/`.
- Azeria Labs — heap part 1 / part 2 / heap exploit dev (ARM focus):
  https://azeria-labs.com/heap-exploitation-part-1-understanding-the-glibc-heap-implementation/
  https://azeria-labs.com/heap-exploitation-part-2-glibc-heap-free-bins/
  https://azeria-labs.com/heap-exploit-development/
  Only solid free ARM heap reference; pair with `references/exotic-arch.md`.

## Linux kernel

- pawnyable — Linux Kernel Exploitation: https://pawnyable.cafe/linux-kernel/
  Step-by-step kernel pwn with full lab images; covers stack overflow, UAF,
  heap spray, KASLR/SMEP/SMAP/KPTI bypass, modprobe path, userfaultfd, FUSE,
  cred and modprobe pivots. Pair with `references/kernel.md`.

## Windows user-land and kernel

- Neuvik — Journey into Windows Kernel Exploitation (Basics):
  https://www.neuvik.com/post/journey-into-windows-kernel-exploitation-the-basics
  Driver model, IOCTL surface, HEVD start path.
- HackSys Extreme Vulnerable Driver (HEVD): https://github.com/hacksysteam/HackSysExtremeVulnerableDriver
  Reference vulnerable driver for stack overflow, UAF, type confusion, race,
  NULL deref, integer overflow — the standard Windows kernel training target.

## Specific techniques

- pepsipu — Nightmare: One Byte to ROP:
  https://nightmare.cs.unm.edu/2.5_one_byte_off.html
  Off-by-one to ROP under PIE/canary; reference walkthrough.
- v13td0x — ret2dlresolve writeup:
  https://syst3mfailure.io/ret2dlresolve/
  Modern ret2dlresolve template when no libc leak is available.
- gynvael — The Tragedy of Low-Level Exploitation (talk):
  https://gynvael.coldwind.pl/?id=662
  Mitigation history and effect on technique selection; useful framing.

## Curated indexes

- CyberSecurityUP — Awesome Exploit Development:
  https://github.com/CyberSecurityUP/Awesome-Exploit-Development
- Binary Exploitation Tutorials (community list):
  https://github.com/r0hi7/BinExp

## Training platforms and courses

- pwn.college: https://pwn.college/
  Free open dojo; covers shellcoding, ASM, debugging, kernel intro.
- guyinatuxedo — nightmare: https://guyinatuxedo.github.io/
  Long ordered intro to pwn and RE; many free reverse and pwn challenges with
  solutions. Use as reference, not for hint-leakage on live work.
- Max Kamper — Linux Heap Exploitation Part 1 (Udemy):
  https://www.udemy.com/course/linux-heap-exploitation-part-1/
  Paid; thorough tcache + fastbin path with reliable PoCs.
- ret2 wargames — Fundamentals of Software Exploitation:
  https://wargames.ret2.systems/
  Paid; modern Linux ROP, heap, and bypass labs.
- OST2 Vulns1001 / Vulns1002 — C-family vuln intro:
  https://ost2.fyi/Vulns1001.html
  https://ost2.fyi/Vulns1002.html
  Free; vuln-class taxonomy and root-cause practice in C/C++.
- OST2 Arch1001 — x86-64 Assembly: https://ost2.fyi/Arch1001.html
  Free assembly foundation; prerequisite for the above.

## Reference data

- syscalls.w3challs (x86/x64 syscall reference): https://syscalls.w3challs.com/
  Per-arch syscall numbers, signatures, and registers. Keep open during shellcode
  and ORW work.
