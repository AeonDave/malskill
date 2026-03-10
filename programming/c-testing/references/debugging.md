# Debugging failing C tests

## General workflow

1. Re-run the single failing test in isolation.
2. If a crash, run under ASan/UBSan first — they give the most context.
3. Reduce to a minimal reproducer.
4. Fix root cause, then run the full suite.

---

## Linux / macOS

### gdb

```sh
gdb ./test_foo
(gdb) run          # run until crash
(gdb) bt           # backtrace
(gdb) frame 2      # switch to frame
(gdb) print val    # inspect variable
(gdb) watch *ptr   # watchpoint for corruption
(gdb) rwatch *ptr  # break on read
```

### lldb

```sh
lldb ./test_foo
(lldb) r           # run
(lldb) bt          # backtrace
(lldb) frame select 2
(lldb) p val
(lldb) watchpoint set variable ptr
```

### Valgrind (Linux)

```sh
# Find use-after-free, uninitialized reads, leaks
valgrind --tool=memcheck --leak-check=full --error-exitcode=1 ./test_foo
# Track origins of uninitialized values
valgrind --track-origins=yes ./test_foo
```

---

## Windows — MinGW

MinGW produces PE or ELF binaries with DWARF debug info.

```sh
# Compile with debug info
x86_64-w64-mingw32-gcc -g -O0 -o test_foo.exe test_foo.c

# Inspect binary for clues (missing imports, symbols)
objdump -d -M intel test_foo.exe     # disassemble
objdump -p test_foo.exe              # PE headers, imports
nm     --demangle test_foo.exe       # symbol table
strings test_foo.exe                 # literal strings
objdump -h test_foo.exe              # section headers

# Debug with gdb (MinGW provides gdb.exe)
gdb test_foo.exe
(gdb) r
(gdb) bt

# Objdump a specific address (after crash output)
objdump -d test_foo.exe | grep -A5 '<crash_addr>'
```

---

## Windows — Visual Studio / MSVC

Build with debug information:

```sh
cl /Zi /Od /RTC1 /Fd:test_foo.pdb test_foo.c
```

`/RTC1` enables runtime checks (stack-frame overruns, uninitialized locals).

### dumpbin — PE inspection without opening VS

```sh
dumpbin /headers  test_foo.exe
dumpbin /imports  test_foo.exe
dumpbin /exports  test_foo.dll
dumpbin /disasm   test_foo.exe
dumpbin /symbols  test_foo.obj
```

### VS Debugger (IDE)

- Set breakpoints in source; inspect locals/registers in the Locals window.
- **Memory window**: Debug → Windows → Memory to inspect raw bytes.
- **Call Stack** window for crash context.
- **Diagnostic Tools**: CPU/memory timeline during test runs.

### WinDbg (standalone)

```sh
windbg -c "g; k 20; q" test_foo.exe   # run, print 20-frame stack, quit
```

Useful WinDbg commands for memory corruption:
- `!analyze -v` — automated crash analysis
- `dd esp` — dump stack
- `dt <type> <addr>` — dump struct at address

---

## Sanitizer-guided debugging

```sh
# ASan: detailed crash with allocation/deallocation site
ASAN_OPTIONS=print_stacktrace=1 ./test_foo
# UBSan: print stack on UB
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 ./test_foo
```
