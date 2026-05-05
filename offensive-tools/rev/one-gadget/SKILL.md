---
name: one-gadget
description: "one-gadget: libc gadget finder for `execve`-style code execution opportunities under known register and stack constraints. Use when you already have a libc leak or version match and want candidate single-shot RCE offsets to test before building a longer ROP chain."
compatibility: "Linux and macOS host; Ruby gem; targets glibc-style libc binaries"
metadata:
  author: AeonDave
  version: "1.0"
---

# one-gadget

Fast libc post-leak shortcut finder. Great when it works, humbling when constraints bite back.

## When to use one-gadget

Use one-gadget when you need to:

- turn a libc base leak into candidate `execve` offsets
- compare several constraint-heavy RCE options quickly
- decide whether a short stack/register fix-up beats a full custom chain

## Quick Start

```bash
# Enumerate candidate gadgets in libc
one_gadget ./libc.so.6

# Show more gadgets and constraints
one_gadget -l 2 ./libc.so.6

# Raw offsets only
one_gadget --raw ./libc.so.6
```

## Practical Workflow

1. Identify the exact libc or a trustworthy build match.
2. Compute the libc base from your leak.
3. Run `one_gadget` on that libc file.
4. Read the printed constraints carefully.
5. Validate stack, registers, and writable memory in `gdb` before betting the exploit on one offset.

## Practical Notes

- Constraints are the whole game: `rsp` contents, `rax == NULL`, or writable memory requirements often decide feasibility.
- `one-gadget` is best after you already solved ASLR for libc.
- Keep a normal ROP fallback path ready; many stable exploits start with `one-gadget` as a probe, not as the final design.

## Caveats

- A valid offset does not imply a reachable or repeatable exploit path.
- Version drift between local and remote libc makes results meaningless.
- CET, seccomp, stack layout differences, or register clobbers often kill the magical one-shot path.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream gem README for installation, constraint-depth controls, and supported libc assumptions.
