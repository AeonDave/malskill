# Flaky tests and debugging

## Anti-flake rules

- No sleeps for synchronization; use latches/condition variables.
- No shared global mutable state across tests.
- Unique temp directories per test.
- Deterministic random seeds (seed via env variable).
- Avoid time-dependent assertions; use relative durations.

## Debugging workflow

1. Re-run the failing test only: `ctest -R TestName -V` or gtest filter `--gtest_filter=Suite.Test`.
2. Run under ASan/UBSan.
3. Reduce to a minimal reproducer.
4. Fix root cause, then run the full suite.

---

## Linux / macOS

### gdb

```sh
gdb ./test_foo
(gdb) run --gtest_filter=Suite.TestName
(gdb) bt
(gdb) frame 2
(gdb) print val
(gdb) watch *ptr      # break on write
```

### lldb

```sh
lldb ./test_foo -- --gtest_filter=Suite.TestName
(lldb) r
(lldb) bt
(lldb) p val
```

### Valgrind (Linux)

```sh
valgrind --tool=memcheck --leak-check=full --error-exitcode=1 \
  ./test_foo --gtest_filter=Suite.TestName
```

### perf (Linux — performance regression hunting)

```sh
perf stat ./test_suite
perf record -g ./test_suite && perf report
```

---

## Windows — MinGW

```sh
# Build with debug info (MinGW)
x86_64-w64-mingw32-g++ -g -O0 -o test_foo.exe test_foo.cpp

# Inspect imports/exports
objdump -p test_foo.exe | grep -A20 'Import'
objdump -d -M intel test_foo.exe
nm --demangle test_foo.exe | grep 'T '

# Run under gdb (MinGW gdb.exe)
gdb test_foo.exe
(gdb) run --gtest_filter=Suite.TestName
(gdb) bt
```

---

## Windows — Visual Studio / MSVC

Build in Debug configuration:

```cmake
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

Or with MSVC flags:

```sh
cl /Zi /Od /RTC1 /Fd:test_foo.pdb test_foo.cpp
```

`/RTC1`: stack overruns + uninitialized locals at runtime.

### dumpbin (MSVC toolchain)

```sh
dumpbin /headers  test_foo.exe
dumpbin /imports  test_foo.exe
dumpbin /disasm   test_foo.exe
dumpbin /symbols  test_foo.obj
```

### VS Debugger

- Attach to test process from **Test Explorer** (“Debug selected tests”).
- Use **Breakpoints** + **Locals** window to inspect state.
- **Diagnostic Tools**: memory/CPU snapshot during test run.
- **Memory window** (Debug → Windows → Memory): inspect raw bytes at pointer.

### WinDbg

```sh
# Run and auto-analyze crash
windbg -c "g; !analyze -v; q" test_foo.exe
# Break on C++ exception
windbg -c "sxe eh; g; k; q" test_foo.exe
```

---

## Sanitizer env variables

```sh
# ASan: rich stack traces
ASAN_OPTIONS=print_stacktrace=1 ./test_foo
# UBSan: halt and print stack
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 ./test_foo
# TSan: verbose race reports
TSAN_OPTIONS=verbosity=1 ./test_foo
```
