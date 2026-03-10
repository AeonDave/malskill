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
```

## MinGW cross-compile example

```sh
cmake -B build-win -DCMAKE_TOOLCHAIN_FILE=toolchain-mingw.cmake
cmake --build build-win
# Run the PE binaries (on Linux with Wine or natively on Windows)
wine build-win/test_module.exe
```
