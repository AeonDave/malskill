# Sanitizers and coverage

## Sanitizers (Clang/GCC)

- Compile and link with `-fsanitize=address` (or `undefined`, `thread`)
- Add `-fno-omit-frame-pointer` for better stack traces
- Prefer `-O1 -g` for debug-friendly reports
- Run ASan/UBSan and TSan in **separate builds** (TSan is not combinable with ASan)

```sh
# ASan + UBSan combined build
cmake -B build-asan -DCMAKE_BUILD_TYPE=Debug \
      -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1" \
      -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"
cmake --build build-asan && ctest --test-dir build-asan --output-on-failure
```

MSVC: `cl /fsanitize=address` (VS 2022+); no TSan — see `cpp-patterns/references/tooling-build.md`.

Runtime options:

```sh
ASAN_OPTIONS=detect_leaks=1:print_stacktrace=1 ./tests
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 ./tests
```

## Coverage (Clang)

```sh
cmake -B build-cov -DCMAKE_CXX_FLAGS="-fprofile-instr-generate -fcoverage-mapping" \
      -DCMAKE_EXE_LINKER_FLAGS="-fprofile-instr-generate"
cmake --build build-cov
cd build-cov && ctest
llvm-profdata merge -sparse default.profraw -o coverage.profdata
llvm-cov report ./unit_tests -instr-profile=coverage.profdata
llvm-cov show  ./unit_tests -instr-profile=coverage.profdata > coverage.txt
```

## Coverage (GCC)

Compile+link with `--coverage`, run the suite, then:

```sh
lcov --capture --directory . --output-file coverage.info
lcov --remove coverage.info '/usr/*' '*/third_party/*' -o coverage.info
genhtml coverage.info --output-directory out
```

Prefer target-level flags in CMake over global `CMAKE_CXX_FLAGS` when only test targets need them.

Collect coverage from stable, deterministic runs only; flaky tests distort signal.

## Suggested cadence

- Per PR: focused unit tests + ASan/UBSan build
- Nightly/periodic: full suite + TSan (where supported) + coverage trend
