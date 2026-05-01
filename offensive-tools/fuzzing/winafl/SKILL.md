---
name: winafl
description: "Coverage-guided fuzzing framework for Windows binaries. Use when fuzzing desktop apps, DLL harnesses, or Windows services with DynamoRIO/TinyInst/Intel PT instrumentation and persistent-loop target functions."
license: Apache-2.0
compatibility: "Windows (primary), Visual Studio toolchain; supports DynamoRIO/TinyInst/Intel PT modes."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# winafl

Windows-focused AFL fork designed for black-box and harnessed binary fuzzing.

## Quick Start

```bash
# Typical shape (high-level)
afl-fuzz -i in -o out -- [instrumentation options] -- target_cmdline

# Example build (x64)
cmake -G"Visual Studio 16 2019" -A x64 .. -DDynamoRIO_DIR=C:\path\to\DynamoRIO\cmake -DINTELPT=1
cmake --build . --config Release
```

## Operator Flow

1. Choose instrumentation backend (DynamoRIO first, TinyInst/PT as needed).
2. Select a target function that opens/parses/closes input and returns normally.
3. Validate debug run before long fuzz sessions.
4. Launch campaign with stable timeout/memory bounds.
5. Periodically minimize corpus and verify reproductions.

## Core Concepts

- Select a target function that:
  - opens/parses/closes input each iteration,
  - returns normally (no hard process exit),
  - is reachable without manual UI interaction.
- Persistent loop behavior is central for throughput.
- Instrumentation choices: DynamoRIO, TinyInst, Intel PT, Syzygy.

## Practical Tricks

- Prefer shared-memory sample delivery (`-s`) when file locking causes rewrite failures.
- For services you cannot launch directly, use attach mode (`-A <module>`) with external process supervision.
- Use `winafl-cmin.py` to control corpus growth and speed up cycles.
- Keep target architecture aligned (32-bit vs 64-bit) across target, DLL, and instrumentation stack.

## Useful Options

| Flag | Purpose |
|------|---------|
| `-D <dir>` | DynamoRIO binaries path |
| `-w <dll>` | `winafl.dll` path |
| `-P` | Intel PT mode |
| `-s` | Shared-memory sample delivery |
| `-A <module>` | Attach mode for running processes/services |
| `-l <dll>` | Custom testcase processing/mutator DLL |

## Common Pitfalls

- Target function not closing input each iteration -> rewrite failures and false timeouts.
- Function exits process instead of returning -> broken persistent loop.
- Skipping debug mode before fuzzing -> difficult timeout diagnosis.
- Network-mode custom DLL workflows without restart hygiene -> unstable long runs.

## Resources

- https://github.com/googleprojectzero/winafl
- https://github.com/googleprojectzero/winafl/blob/master/README.md
- https://github.com/googleprojectzero/TinyInst
- https://dynamorio.org/
