---
name: strace
description: "Auth/lab ref: Linux syscall tracer for observing file, process, network, memory, and signal behavior at runtime."
compatibility: "Linux primary; requires ptrace capability; not a native Windows tool."
metadata:
  author: AeonDave
  version: "1.0"
---

# strace

Runtime truth serum for Linux programs: if the kernel saw it, `strace` can usually tell you.

## When to use strace

Use strace when you need to:

- see opened files, sockets, child processes, and exec chains
- debug missing libraries, bad paths, permission failures, or seccomp kills
- observe exact syscall arguments around exploit or malware activity
- confirm environment assumptions before touching the target in a debugger

## Quick Start

```bash
# Trace a process and its syscalls
strace ./chall

# Follow children and save output
strace -f -o trace.log ./chall

# Show more string data
strace -f -s 256 ./chall
```

## High-Value Workflows

### Scope the trace to what matters

```bash
strace -f -e trace=file ./chall
strace -f -e trace=network,process ./chall
strace -f -e trace=openat,execve,connect ./chall
```

### Attach to an existing process

```bash
strace -p 1234
strace -f -p 1234 -e trace=file,network
```

### Timing and descriptor-aware logging

```bash
strace -ff -tt -yy -o trace ./chall
```

## Practical Notes

- Start with `-f -s 256 -o trace.log` for a readable baseline that survives noisy runs.
- `-e trace=file` is excellent for loader and path debugging.
- `-yy` helps map file descriptors and socket addresses to something human-friendly.
- Pair with `ltrace` when libc-level behavior matters more than raw syscalls.

## Caveats

- `strace` slows programs down and can perturb timing-sensitive targets.
- Anti-debug or ptrace-restricted environments may block attach or distort behavior.
- Syscall visibility does not automatically reveal higher-level intent; correlate with binary context.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the `strace` man page for class filters, decoding controls, and fault-injection features.
