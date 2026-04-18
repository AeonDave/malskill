# CMake / CTest for C tests

## Minimal CMake skeleton

```cmake
cmake_minimum_required(VERSION 3.20)
project(foo_tests C)
set(CMAKE_C_STANDARD 11)

enable_testing()

add_executable(test_module tests/test_module.c src/module.c)
target_include_directories(test_module PRIVATE include)
add_test(NAME test_module COMMAND test_module)
```

Use `include(CTest)` in top-level `CMakeLists.txt` to get `BUILD_TESTING` option and `enable_testing()` behavior.

## Sanitizer build preset

```cmake
option(SANITIZE "Enable ASan+UBSan" OFF)
if(SANITIZE)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer -g -O1)
  add_link_options   (-fsanitize=address,undefined)
endif()
```

Build and run:

```sh
cmake -B build -DSANITIZE=ON
cmake --build build
ctest --test-dir build -V
```

## Labels for unit vs integration

```cmake
add_test(NAME unit_parse   COMMAND test_parse)
set_tests_properties(unit_parse PROPERTIES LABELS "unit")

add_test(NAME integration_db  COMMAND test_db_integration)
set_tests_properties(integration_db PROPERTIES LABELS "integration")
```

Useful extra labels: `slow`, `flaky`, `sanitizer`, `fuzz-regression`.

Run only unit tests:

```sh
ctest -L unit -V
```

## Useful CTest flags

```sh
ctest --test-dir build -V          # verbose output
ctest -R test_parse                # run by name regex
ctest -L unit                      # run by label
ctest --rerun-failed               # only re-run failures
ctest -j4                          # parallel test execution
ctest --output-on-failure          # print stdout on failure only
ctest --rerun-failed               # rerun only previously failed tests
ctest --repeat until-fail:50       # detect flaky tests
ctest --schedule-random            # discover hidden test interdependencies
```

## Test properties that matter

```cmake
set_tests_properties(test_parse PROPERTIES
  LABELS "unit"
  TIMEOUT 10
)

set_tests_properties(test_expected_fail PROPERTIES
  WILL_FAIL TRUE
)
```

Notes:

- `TIMEOUT` takes precedence over default `CTEST_TEST_TIMEOUT`.
- Prefer per-test timeout over global timeout.

## Fixtures (setup/cleanup orchestration)

```cmake
add_test(NAME setup_env COMMAND test_setup_env)
set_tests_properties(setup_env PROPERTIES FIXTURES_SETUP env)

add_test(NAME test_parser COMMAND test_parser)
set_tests_properties(test_parser PROPERTIES FIXTURES_REQUIRED env)

add_test(NAME cleanup_env COMMAND test_cleanup_env)
set_tests_properties(cleanup_env PROPERTIES FIXTURES_CLEANUP env)
```

Use fixtures when tests share expensive setup, but keep normal unit tests independent.

## MinGW cross-compile example

```sh
cmake -B build-win -DCMAKE_TOOLCHAIN_FILE=toolchain-mingw.cmake
cmake --build build-win
# Run the PE binaries (on Linux with Wine or natively on Windows)
wine build-win/test_module.exe
```
