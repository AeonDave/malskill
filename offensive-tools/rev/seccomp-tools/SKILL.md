---
name: seccomp-tools
description: "Auth/lab ref: seccomp BPF inspection toolkit for dumping, disassembling, assembling, and emulating Linux syscall filters."
compatibility: "Linux primary; Ruby gem; targets seccomp-bpf workflows."
metadata:
  author: AeonDave
  version: "1.0"
---

# seccomp-tools

Sandbox policy visibility for pwn and Linux-reversing work.

## When to use seccomp-tools

Use seccomp-tools when you need to:

- dump a process or challenge binary's seccomp filter
- disassemble BPF policy logic into something readable
- confirm which syscalls are allowed, trapped, or killed
- adapt shellcode, ROP, or post-exploitation plans to the sandbox

## Quick Start

```bash
# Dump seccomp filter from a local binary under execution
seccomp-tools dump ./chall

# Dump from a running PID
seccomp-tools dump -p 1234

# See available subcommands
seccomp-tools --help
```

## High-Value Workflows

### Core subcommands

```bash
seccomp-tools dump ./chall
seccomp-tools disasm policy.bpf
seccomp-tools asm policy.asm
seccomp-tools emu policy.bpf
```

### Exploit-planning workflow

1. Dump the filter with `dump`.
2. Identify allowed syscalls and argument constraints.
3. Decide whether `open`, `execve`, `mprotect`, `socket`, or `read/write` paths survive.
4. Adjust your chain toward the permitted syscall surface.

## Practical Notes

- This tool is most valuable before wasting time on a payload that the sandbox will kill instantly.
- Pair with `strace` to see the exact failing syscall and with `gdb` for runtime state.
- Even a tiny allowlist can still leave enough room for ORW, dup-and-read, or SROP-style recovery.

## Caveats

- Dumping policies may require a cooperative execution path or ptrace-friendly environment.
- A readable filter still needs human interpretation for architecture and argument semantics.
- Kernel behavior and container layers can add constraints beyond the visible seccomp policy.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the upstream README for exact subcommand syntax, architecture support, and examples.
