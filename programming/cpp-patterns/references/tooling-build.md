# Tooling and build hygiene

## Compiler warnings

```sh
# GCC / Clang
g++ -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wnon-virtual-dtor -Werror ...
# MSVC (Visual Studio)
cl /W4 /WX /std:c++20 /analyze ...
# MinGW (GCC on Windows)
x86_64-w64-mingw32-g++ -Wall -Wextra -Wpedantic -std=c++20 -Werror ...
```

## Sanitizers (Clang/GCC/MinGW)

Full sanitizer support is best on Linux/macOS. Clang-cl on Windows supports ASan since VS 2022.

```sh
# AddressSanitizer
clang++ -fsanitize=address -fno-omit-frame-pointer -g -O1 foo.cpp -o foo
# UndefinedBehaviorSanitizer
clang++ -fsanitize=undefined -fno-omit-frame-pointer -g foo.cpp -o foo
# ThreadSanitizer (not compatible with ASan)
clang++ -fsanitize=thread -g foo.cpp -o foo
# MSVC /fsanitize (VS 2022+)
cl /fsanitize=address /Zi foo.cpp
# MinGW
x86_64-w64-mingw32-g++ -fsanitize=address -g foo.cpp -o foo.exe
```

References:
- ASan: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
- TSan: https://clang.llvm.org/docs/ThreadSanitizer.html

## Static analysis

```sh
# clang-tidy (integrates with CMake via CMAKE_EXPORT_COMPILE_COMMANDS)
clang-tidy foo.cpp -- -std=c++20
# cppcheck
cppcheck --enable=all --std=c++20 src/
# MSVC built-in
cl /analyze foo.cpp
# Include-What-You-Use (IWYU)
iwyu foo.cpp 2>&1 | fix_include -- src/
```

## Binary inspection

### MinGW / binutils (Windows and Linux)

```sh
# Disassemble
objdump -d -M intel foo.exe
# List symbols
nm --demangle foo.exe
# Show section sizes
size foo.exe
objdump -h foo.exe
# Inspect PE imports
objdump -p foo.exe | grep -A20 'Import'
# String search
strings foo.exe | grep -i password
# Strip debug info
strip --strip-debug foo.exe
# Relocations in object file
objdump -r foo.o
```

### Visual Studio / MSVC (Windows)

```sh
# PE headers, exports, imports, disassembly, symbols
dumpbin /headers foo.exe
dumpbin /exports foo.dll
dumpbin /imports foo.exe
dumpbin /disasm    foo.exe
dumpbin /symbols   foo.obj
# Generate PDB for debuggable builds
cl /Zi /Fd:foo.pdb foo.cpp
# WinDbg quick session
windbg -c "g; k; q" foo.exe
# VS Test Explorer / CTest integration
ctest --test-dir build -C Debug -V
```

### Linux tools

```sh
# ELF inspection
readelf -h foo           # ELF header
readelf -S foo           # sections
readelf -s foo           # symbols
readelf -d foo           # dynamic dependencies
ldd    foo               # shared library deps
# Debugging
gdb    foo
lldb   foo
# System call tracing
strace -e trace=memory,file ./foo
ltrace ./foo
# Memory errors
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all ./foo
# Heap profile
valgrind --tool=massif ./foo
ms_print massif.out.* | head -50
# Performance
perf stat ./foo
perf record -g ./foo && perf report
```

## CMake hygiene

Prefer target-based settings; avoid polluting global flags.

```cmake
target_compile_options(mylib PRIVATE -Wall -Wextra)
target_compile_features(mylib PUBLIC cxx_std_20)
# Expose compile commands for clang-tidy
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

## Compile-time assertions

```cpp
static_assert(sizeof(uint32_t) == 4, "unexpected uint32_t size");
static_assert(std::is_trivially_copyable_v<MyHeader>);
```
