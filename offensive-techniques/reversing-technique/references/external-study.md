# External Study and Training — Reversing Methodology

Long-form learning resources that support and refresh the methodology in this
skill. Use between engagements, not in the middle of one. Per-task workflow and
decision trees stay in the other `references/*.md` files.

## Foundations

- OST2 Arch1001 — x86-64 Assembly: https://ost2.fyi/Arch1001.html
  Free, full instruction-set curriculum. Mandatory baseline for anyone running
  the static and dynamic flows in `references/re-workflow.md`.
- OST2 Arch2001 — User-mode Linux debugging: https://ost2.fyi/Arch2001.html
  GDB and ELF runtime mechanics; complements `references/elf-rev.md`.
- guyinatuxedo — nightmare: https://guyinatuxedo.github.io/
  Walkthrough collection covering most static-RE and basic dynamic-RE patterns
  the methodology calls out.

## Anti-analysis and obfuscation context

- Awesome Exploit Development (anti-debug and packer sections):
  https://github.com/CyberSecurityUP/Awesome-Exploit-Development
  Curated entry point into packer and anti-debug literature when extending
  `references/anti-analysis.md`.

## Heap and allocator structures

- ir0nstone — Binary Exploitation Notes (heap chapter):
  https://ir0nstone.gitbook.io/notes/types/stack/heap
  Free reference for glibc bin internals; useful when reversing custom or
  wrapped allocators before passing the result to
  `references/binary-exploitation-capability.md`.
- shellphish — how2heap: https://github.com/shellphish/how2heap
  Source-level allocator metadata reference. Read alongside dumps when verifying
  RE assumptions about chunk layout.

## Exploitability handoff

- Pwn-side reading list (deeper exploit-dev material once RE confirms a vuln):
  `offensive-ctf/pwn-ctf/references/external-study.md`.

## Talks and framing

- gynvael — The Tragedy of Low-Level Exploitation:
  https://gynvael.coldwind.pl/?id=662
  Helpful when reasoning about why a target's mitigations make an older RE
  pattern obsolete or, conversely, still viable.

## Reference data

- syscalls.w3challs (x86/x64 syscall reference): https://syscalls.w3challs.com/
  Used during stub recovery, loader analysis, and stripped-binary syscall
  fingerprinting.
