---
name: aflplusplus
description: "Auth/lab ref: Coverage-guided fuzzing framework for source and binary targets."
license: Apache-2.0
compatibility: "Linux, macOS, Windows (WSL/Cygwin paths vary)."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# aflplusplus

AFL++ is a modern AFL fork with stronger instrumentation, mutation strategies, and binary-only options.

## Quick Start

```bash
# Build target with AFL++ wrappers
CC=afl-cc CXX=afl-c++ ./configure --disable-shared --disable-werror
make -j"$(nproc)"

# Fuzz stdin target
afl-fuzz -i seeds -o out -- ./target_bin

# Fuzz file-based target
afl-fuzz -i seeds -o out -- ./target_bin @@
```

## Operator Flow (Recommended)

1. Compile with `afl-clang-lto` (or `afl-clang-fast` fallback).
2. Create a small valid seed set, then deduplicate (`afl-cmin`).
3. Start one main instance and multiple secondary instances on the same `-o` dir.
4. Add one sanitizer build and one cmp-guided setup (`CMPLOG`/Redqueen) in parallel.
5. Triage crashes with `afl-tmin`, replay under sanitizer, and bucket by stack/PC.

## Core Flags & Environment

| Flag | Description |
|------|-------------|
| `-i <dir>` | Seed corpus directory |
| `-o <dir>` | Output campaign directory |
| `-x <dict>` | Dictionary for structured tokens |
| `-m <mb>` | Memory limit |
| `-t <ms>` | Per-exec timeout |
| `-M` / `-S` | Parallel main/secondary instances |
| `-d` | Skip deterministic stage (faster starts) |

Useful env variables in real campaigns:

- `AFL_USE_ASAN=1` / `AFL_USE_UBSAN=1` for sanitizer build variants.
- `AFL_LLVM_CMPLOG=1` for compare tracing binary used with `-c`.
- `AFL_LLVM_LAF_ALL=1` for compare splitting (when needed).
- `AFL_IMPORT_FIRST=1` to sync-import queue items early.
- `AFL_TMPDIR=/dev/shm/...` to reduce disk I/O pressure.

## Practical Campaign Pattern

```bash
# 1) Corpus cleanup
afl-cmin -i seeds -o seeds_min -- ./parser @@

# 2) Main instance
afl-fuzz -M main -i seeds_min -o out -- ./parser @@

# 3) Secondary instances (example)
afl-fuzz -S fast -i seeds_min -o out -p fast -- ./parser @@
afl-fuzz -S explore -i seeds_min -o out -p explore -- ./parser @@

# 4) Resume campaign later
afl-fuzz -i - -o out -- ./parser @@

# 5) Minimize crash for triage
afl-tmin -i out/default/crashes/id:000000* -o crash.min -- ./parser @@
```

## Tricks That Matter

- Prefer persistent-mode harnesses whenever possible; throughput jump is often decisive.
- For checksum-heavy formats, use fuzz-build conditionals (`FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION`) to bypass blockers in harness builds.
- For short CI fuzz windows, use faster calibration settings and reuse prior corpus.
- For dlopen-heavy targets, preload instrumented libs so map coverage is visible from startup.

## Common Pitfalls

- Fuzzing network services over live sockets without harnessing: huge speed loss and weak reproducibility.
- Running all instances with identical profile/options: less strategy diversity.
- Skipping memory/time limits (`-m`, `-t`) on unstable targets: noisy campaigns.
- Treating corpus size as success metric; coverage and unique bug quality matter more.

## Binary / Service Notes

- Binary-only: use AFL++ binary-focused docs (QEMU/Frida/Unicorn workflows) and keep strict replay discipline.
- Services/daemons: adapt to file/stdin/shared-memory harnessing for realistic throughput.
- GUI applications: isolate parser logic into fuzzable non-UI entrypoints.

## Resources

- https://aflplus.plus/
- https://github.com/AFLplusplus/AFLplusplus
- https://aflplus.plus/docs/fuzzing_in_depth/
- https://aflplus.plus/docs/best_practices/
- https://google.github.io/oss-fuzz/
