---
name: libfuzzer
description: "In-process, coverage-guided fuzzing engine integrated with Clang/LLVM. Use for fast unit-level fuzz targets, parser hardening, sanitizer-first bug discovery, and corpus-driven regression loops in C/C++ code."
license: NCSA
compatibility: "Clang/LLVM toolchains on Linux/macOS/Windows."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# libfuzzer

LLVM-native in-process fuzzer using `LLVMFuzzerTestOneInput` entrypoints.

## Quick Start

```bash
# Minimal target
# extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size)

# Build with libFuzzer + ASAN
clang++ -g -O1 -fsanitize=fuzzer,address fuzz_target.cc -o fuzz_target

# Run
./fuzz_target corpus/
```

## Operator Flow

1. Build a narrow, deterministic `LLVMFuzzerTestOneInput` harness.
2. Add ASAN/UBSAN first; add MSAN when dependency hygiene allows.
3. Seed with small valid/invalid corpus.
4. Run long enough to stabilize coverage features, then merge/minimize corpus.
5. Keep crashing artifacts as regression tests.

## Key Practice

- Keep fuzz target deterministic, fast, and side-effect-light.
- Prefer narrow targets per format/API instead of one giant dispatcher.
- Seed with small valid+invalid samples; then minimize via `-merge=1`.

## Useful Flags

| Flag | Purpose |
|------|---------|
| `-runs=N` | Bounded runs |
| `-max_total_time=N` | Time budget |
| `-dict=file` | Token dictionary |
| `-jobs` / `-workers` | Parallel campaigns |
| `-fork=N` | Crash/OOM/timeout-resistant subprocess mode |
| `-use_value_profile=1` | Stronger cmp-guided search |
| `-merge=1` | Corpus minimization/merge |

## Practical Tricks

- Use `FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION` to disable fuzz-hostile randomness/checksums in harness builds.
- Return `-1` for intentionally rejected inputs to reduce corpus pollution.
- Use `-artifact_prefix` / fixed artifact paths in CI pipelines for predictable collection.
- For very large corpora, use resumable merge workflows.

## Common Pitfalls

- Original authors shifted major innovation to Centipede; libFuzzer remains supported for bug fixes.
- Excellent fit for CI regression with saved crash artifacts.
- Non-deterministic harness behavior causes corpus bloat and noisy triage.
- Overly broad max lengths can waste cycles on low-value regions.
- Neglecting sanitizers in in-process mode delays detection of latent memory issues.

## Resources

- https://llvm.org/docs/LibFuzzer.html
- https://clang.llvm.org/docs/SanitizerCoverage.html
- https://google.github.io/oss-fuzz/
