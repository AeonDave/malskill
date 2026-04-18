# Sanitizers and coverage

## Sanitizers (Clang/GCC)

From Clang sanitizer docs:
- Compile and link with `-fsanitize=address` (or `undefined`, `thread`)
- Add `-fno-omit-frame-pointer` for better stack traces
- Prefer `-O1 -g` for debug-friendly reports
- Run ASan/UBSan and TSan in separate builds (TSan is not combinable with ASan)

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
- TSan: https://clang.llvm.org/docs/ThreadSanitizer.html

## Coverage

Two common toolchains:
- Clang: `-fprofile-instr-generate -fcoverage-mapping` + `llvm-profdata` + `llvm-cov`
- GCC: `--coverage` + lcov/genhtml

Prefer target-level flags in CMake.

Collect coverage from stable, deterministic runs only; flaky tests distort signal.

## Suggested cadence

- Per PR: focused unit tests + ASan/UBSan build
- Nightly/periodic: full suite + TSan (where supported) + coverage trend
