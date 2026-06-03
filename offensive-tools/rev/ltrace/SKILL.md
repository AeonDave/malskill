---
name: ltrace
description: "Auth/lab ref: Linux library-call tracer for glibc and dynamically linked userspace APIs."
compatibility: "Linux primary; best with dynamically linked binaries."
metadata:
  author: AeonDave
  version: "1.0"
---

# ltrace

If `strace` shows what the kernel saw, `ltrace` shows what userland asked its libraries to do.

## When to use ltrace

Use ltrace when you need to:

- watch libc/API usage such as `strcmp`, `fopen`, `memcpy`, or `system`
- infer control-flow choices from arguments and return values
- identify likely string checks, password comparisons, or parsing logic
- complement `strace` with a friendlier view of dynamic library behavior

## Quick Start

```bash
# Trace library calls
ltrace ./chall

# Follow children and save output
ltrace -f -o ltrace.log ./chall

# Show longer strings
ltrace -f -s 256 ./chall
```

## High-Value Workflows

### Focus on suspicious calls

```bash
ltrace -e strcmp+strncmp+memcmp ./chall
ltrace -e malloc+free+realloc ./chall
ltrace -e fopen+fread+fwrite+system ./chall
```

### Attach to an already running process

```bash
ltrace -p 1234
```

## Practical Notes

- Start here when you suspect a challenge is hiding comparisons or parser behavior in libc calls.
- Combine with `strings` to guess a secret check, then use `ltrace -e strcmp+memcmp` to confirm it.
- Pair with `strace` when you need both the high-level call and the final syscall effect.

## Caveats

- Static binaries, direct syscalls, or stripped custom runtimes reduce usefulness sharply.
- Some optimized calls inline away the exact function you hoped to observe.
- Anti-debug protections can interfere just as they do with other ptrace-based tools.

## Resources

No bundled `scripts/`, `references/`, or `assets/`.
Use the `ltrace` man page for expression filters, prototype handling, and timing output.
