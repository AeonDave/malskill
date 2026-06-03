---
name: ropgadget
description: "Auth/lab ref: gadget discovery utility for ELF, PE, Mach-O, and raw binaries."
compatibility: "Linux, macOS, Windows; Python 3."
metadata:
  author: AeonDave
  version: "1.0"
---

# ROPgadget

Fast gadget discovery for exploit development and mitigations-aware binary triage.

## When to use ROPgadget

Use ROPgadget when you need to:

- enumerate `pop`, `ret`, pivot, syscall, or call-oriented gadgets
- filter gadgets around bad-byte, depth, or architecture constraints
- get a fast first-pass view before building a manual chain
- compare gadget availability across the main binary and loaded libraries

## Quick Start

```bash
# Basic gadget dump
ROPgadget --binary ./chall

# Common x86-64 stack-control gadgets
ROPgadget --binary ./chall --only "pop|ret"

# Try automatic chain generation when the target is simple
ROPgadget --binary ./chall --ropchain
```

## High-Value Workflows

### Focus on useful gadget families

```bash
ROPgadget --binary ./chall --only "pop|ret"
ROPgadget --binary ./chall --only "syscall|sysenter|int 0x80"
ROPgadget --binary libc.so.6 --only "mov|call|jmp"
```

### Reduce noisy results

```bash
ROPgadget --binary ./chall --depth 6
ROPgadget --binary ./chall --badbytes "00|0a|0d"
ROPgadget --binary ./chall --range 0x400000-0x401000
```

### Cross-check a suspected pivot area

```bash
ROPgadget --binary ./chall --only "leave|xchg|add rsp|sub rsp|ret"
```

## Practical Notes

- Treat `--ropchain` as a convenience feature, not a proof of exploitability.
- Build from ABI requirements first, then search for the minimum gadget set that satisfies them.
- Re-verify gadget addresses after PIE/libc-base calculations; static addresses are rarely the final story.
- Pair with `one-gadget` for libc post-leak options and with `gdb` for runtime validation.

## Caveats

- Gadget quality still needs human review for side effects, clobbers, and alignment.
- Very noisy binaries benefit from tighter `--only`, `--range`, or smaller depth settings.
- CET, Shadow Stack, CFG, or tight seccomp policies can make a nice gadget list operationally irrelevant.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream README for architecture support, output formats, and advanced filters.
