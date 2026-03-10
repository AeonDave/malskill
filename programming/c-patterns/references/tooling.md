# Tooling for safer C

## Compiler warnings

```sh
# GCC / Clang
gcc -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror ...
# MSVC (Visual Studio)
cl /W4 /WX /analyze ...
# MinGW (GCC on Windows — same flags as GCC)
x86_64-w64-mingw32-gcc -Wall -Wextra -Wpedantic -Werror ...
```

## Sanitizers (Clang/GCC/MinGW)

Sanitizers work natively on Linux/macOS. On Windows, Clang-cl or MinGW-based ASan builds are limited — prefer Linux for full sanitizer coverage.

```sh
# AddressSanitizer
clang  -fsanitize=address -fno-omit-frame-pointer -g -O1 foo.c -o foo
# UndefinedBehaviorSanitizer
clang  -fsanitize=undefined -fno-omit-frame-pointer -g foo.c -o foo
# MinGW GCC (partial ASan support)
x86_64-w64-mingw32-gcc -fsanitize=address -g foo.c -o foo.exe
```

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html

## Static analysis

```sh
# clang-tidy
clang-tidy foo.c -- -std=c11 -Wall
# cppcheck
cppcheck --enable=all --std=c11 src/
# MSVC built-in (/analyze)
cl /analyze foo.c
```

## Binary inspection

### MinGW / binutils (Windows and Linux)

```sh
# Disassemble a PE/ELF
objdump -d -M intel foo.exe
# List symbols (name + address + section)
nm --demangle foo.exe
# Show sections and their sizes
objdump -h foo.exe
size foo.exe
# Search for strings in a binary
strings foo.exe | grep -i key
# Show imports (PE)
objdump -p foo.exe | grep -A20 'Import'
# Strip debug info for production
strip --strip-debug foo.exe
# Inspect resource sections (Windows RC data)
windres --verbose (for round-trip)
# Show all relocations
objdump -r foo.o
# Show PE headers (binutils)
objdump -p foo.exe
```

### Visual Studio / MSVC (Windows)

```sh
# Dump PE headers, exports, imports
dumpbin /headers foo.exe
dumpbin /exports foo.dll
dumpbin /imports foo.exe
dumpbin /disasm foo.exe
dumpbin /symbols foo.obj
# Generate PDB for better stack traces
cl /Zi /Fd:foo.pdb foo.c
# Analyze with WinDbg (CLI)
windbg -c "g; k; q" foo.exe
```

### Linux tools

```sh
# Inspect ELF headers
readelf -h foo
readelf -S foo            # sections
readelf -s foo            # symbol table
readelf -d foo            # dynamic section (shared deps)
# Shared library dependencies
ldd foo
# Process system calls (debug)
strace -e trace=memory ./foo
# Dynamic library calls
ltrace ./foo
# Performance counters
perf stat ./foo
perf record ./foo && perf report
# Memory errors
valgrind --tool=memcheck --leak-check=full ./foo
# Heap profiling
valgrind --tool=massif ./foo && ms_print massif.out.*
# Find undefined behaviour (compiled with UBSan + print_stacktrace=1)
UBSAN_OPTIONS=print_stacktrace=1 ./foo
```

## Useful compile-time checks

```c
// Assert struct layout / size expectations at compile time
_Static_assert(sizeof(uint32_t) == 4, "unexpected uint32_t size");
_Static_assert(offsetof(struct Foo, x) == 0, "unexpected layout");
```
