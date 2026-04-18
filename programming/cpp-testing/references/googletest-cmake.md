# GoogleTest with CMake/CTest

## Quickstart (FetchContent)

GoogleTest documents a CMake quickstart using `FetchContent` and `gtest_discover_tests()`.

Key points:
- GoogleTest requires at least C++17.
- Use a pinned archive/hash for reproducibility.
- Use `gtest_force_shared_crt` on Windows to avoid overriding CRT settings.
- Prefer `gtest_discover_tests()` over regex-based static discovery for parameterized tests.

References:
- GoogleTest CMake quickstart: https://github.com/google/googletest/blob/main/docs/quickstart-cmake.md
- Primer: https://github.com/google/googletest/blob/main/docs/primer.md

## Typical CMake skeleton

- `enable_testing()`
- `add_executable(<tests> ...)`
- `target_link_libraries(<tests> GTest::gtest_main)`
- `include(GoogleTest)`
- `gtest_discover_tests(<tests>)`

## Practical integration tips

- Use one test executable per module/domain to keep link times manageable.
- Set test labels/properties in CTest for fast selective runs (e.g., `unit`, `integration`, `slow`).
- Keep CTest as suite orchestrator; GoogleTest remains the test framework inside binaries.
