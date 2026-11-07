# GoogleTest with CMake/CTest

## Quickstart (FetchContent)

```cmake
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/releases/download/v1.18.0/googletest-1.18.0.tar.gz
  URL_HASH SHA256=<pin-the-sha256-here>
)
# Prevent overriding the host project's compiler/linker settings on Windows
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)
```

Key points:
- GoogleTest ≥ 1.17 requires **C++17** (v1.16.0 was the last C++14-capable release).
- Use a pinned archive/hash for reproducibility.
- Use `gtest_force_shared_crt` on Windows to avoid overriding CRT settings.
- Prefer `gtest_discover_tests()` over regex-based static discovery for parameterized tests.

## Typical CMake skeleton

```cmake
enable_testing()

add_executable(unit_tests parser_test.cpp ../src/parser.cpp)
target_compile_features(unit_tests PRIVATE cxx_std_20)
target_link_libraries(unit_tests GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(unit_tests)
```

- `GTest::gtest_main` supplies `main()`; no hand-written runner needed.
- `gtest_discover_tests(<tests>)` registers each test case as a CTest test (post-build query).

## Practical integration tips

- Use one test executable per module/domain to keep link times manageable.
- Set test labels/properties in CTest for fast selective runs (e.g., `unit`, `integration`, `slow`).
- Keep CTest as suite orchestrator; GoogleTest remains the test framework inside binaries.
- Test selection: `ctest -R <regex>` (CTest level) or `--gtest_filter=Suite.Test` (binary level).

## FetchContent vs find_package

- `find_package(GTest CONFIG)` — when the toolchain already provides GTest (vcpkg, Conan, system package); avoids network at configure time.
- `FetchContent` — self-contained; pin the URL hash. Do not mix both in one build tree.

## References

- GoogleTest CMake quickstart: https://google.github.io/googletest/quickstart-cmake.html
- Primer: https://google.github.io/googletest/primer.html
- Advanced guide (fixtures, matchers): https://google.github.io/googletest/advanced.html
