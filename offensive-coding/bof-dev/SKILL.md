---
name: bof-dev
description: "BOF (Beacon Object File) engineering for C and C++. DFR (Dynamic Function Resolution), linker limits, runtime safety, and COFF constraints."
---

# bof-dev

**Goal**: Write stealthy, production-ready Beacon Object Files (BOFs) in C or C++ for Cobalt Strike, Sliver, Havoc, or custom COFF loaders.

## Cognitive Stance

A BOF is just an unlinked object file (`.o` / `.obj`). 
The loader maps sections into memory and links it at runtime. It has no OS loader, no runtime (CRT/STL), and exits via `go()`.

## Strict Rules

1. **No Standard Library / Runtime**: No `printf`, `malloc`, `new`, `std::string`, `try/catch`. 
2. **DFR (Dynamic Function Resolution)**: You must declare `DECLSPEC_IMPORT` and use `KERNEL32$VirtualAlloc` format so the loader can resolve Win32 APIs statically. Do *not* link against `kernel32.lib`.
3. **Global State**: Global initialized variables (`int x = 5;`) are mapped but remain persistent across BOF executions in the same process. Use them cautiously. Global C++ constructors (`Foo f;`) will fail to link.
4. **C++ Specifics**: Strip all C++ features that require runtime support. Disable RTTI (`-fno-rtti`) and exceptions (`-fno-exceptions`). The entry point `go` must be declared `extern "C"`. 
5. **Memory Safety**: You are executing inside the C2 agent's process. A segfault kills the payload. Check all pointers. Use `BeaconPrintf` for output.

## Framework Constraints (Mingw-w64)

```bash
# Compilation for C
x86_64-w64-mingw32-gcc -c bof.c -o bof.o -Os -Wl,--exclude-libs,msvcrt.a

# Compilation for C++
x86_64-w64-mingw32-g++ -c bof.cpp -o bof.o -Os -fno-exceptions -fno-rtti -fno-threadsafe-statics
```

## References
- [references/dfr-strategies.md](references/dfr-strategies.md) — Load when building Win32 API calls manually or fighting linker errors like `__imp_`.
- [references/anti-patterns.md](references/anti-patterns.md) — Load when troubleshooting BOF crashes or unexplained C2 disconnects.
