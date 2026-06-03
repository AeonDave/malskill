---
name: honggfuzz
description: "Auth/lab ref: Feedback-driven, high-speed fuzzer with multi-process/thread execution and persistent fuzzing."
license: Apache-2.0
compatibility: "Linux, macOS, Android, BSD, Windows via Cygwin."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# honggfuzz

General-purpose evolutionary fuzzer with software/hardware coverage options and strong persistent-mode performance.

## Quick Start

```bash
# Compile with wrappers
./hfuzz_cc/hfuzz-clang -o target target.c

# Run with file placeholder
./honggfuzz -i seeds -- ./target ___FILE___

# Persistent mode
./honggfuzz -P -i seeds -- ./target
```

## Operator Flow

1. Start with a stable target invocation (`___FILE___` or `-s` stdin mode).
2. Use compile-time instrumentation first; move to hardware counters when appropriate.
3. Switch to persistent mode (`-P`) as soon as target design allows.
4. Run corpus minimization (`-M`) periodically.
5. Verify/replay findings with sanitizer builds and deterministic launch args.

## Core Flags

| Flag | Description |
|------|-------------|
| `-i <dir>` | Input corpus directory |
| `--output <dir>` | Output directory for dynamic/minimized corpus |
| `-P` | Persistent mode |
| `-n <threads>` | Number of fuzzing threads |
| `-M` | Corpus minimization mode |
| `-x` | Disable instrumentation feedback (static mode) |
| `-s` | Feed input via stdin |
| `--sanitizers` | Enable sanitizer-aware handling (build-dependent) |

## Practical Tricks

- Use `-dict` for highly structured input grammars.
- Tune timeout (`-t`) and mutation count per run (`-r`) before scaling threads.
- For constrained targets, use runtime limits (`--rlimit_*`) to prevent campaign collapse.
- In black-box cases, compare noinst (`-x`) baseline vs coverage-driven modes to validate benefit.

## Common Pitfalls

- Can start from empty corpus, but structured seeds improve depth.
- Persistent mode is usually the first optimization to unlock high exec/sec.
- Use with ASAN/UBSAN/MSAN builds for reliable crash triage.
- Ignoring output naming/signature patterns slows bucketing.
- Mixing unstable target startup logic with persistent mode can hide root causes.

## Triage Pattern

- Keep crash files plus command/args snapshot.
- Reproduce under sanitizer build of same target path.
- Cluster by signal + PC/stack signature, then minimize and bisect input deltas.

## Resources

- https://github.com/google/honggfuzz
- https://honggfuzz.dev/
- https://github.com/google/honggfuzz/blob/master/docs/USAGE.md
- https://google.github.io/oss-fuzz/
