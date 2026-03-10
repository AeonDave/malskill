# Sanitizers and coverage

## Sanitizers (Clang/GCC)

From Clang sanitizer docs:
- Compile and link with `-fsanitize=address` (or `undefined`, `thread`)
- Add `-fno-omit-frame-pointer` for better stack traces
- Prefer `-O1 -g` for debug-friendly reports

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
- TSan: https://clang.llvm.org/docs/ThreadSanitizer.html

## Coverage

Two common toolchains:
- Clang: `-fprofile-instr-generate -fcoverage-mapping` + `llvm-profdata` + `llvm-cov`
- GCC: `--coverage` + lcov/genhtml

Prefer target-level flags in CMake.
