# CTF Reverse - Language and Runtime Reversing

How to read a binary once you know what produced it. For app/OS/hardware environments (Android, iOS, firmware, kernel, game engines, exotic arch) see [platforms.md](platforms.md). For toolchain choice see [tools.md](tools.md).

## Table of Contents
- [Go](#go)
- [Rust](#rust)
- [Swift](#swift)
- [D](#d)
- [C++](#c)
- [Kotlin and JVM](#kotlin-and-jvm)
- [Haskell](#haskell)
- [Nuitka-Compiled Python](#nuitka-compiled-python)
- [Python Bytecode](#python-bytecode)
- [WASM](#wasm)
- [Esolangs](#esolangs)
- [Build-System and Source-Like Interpreters](#build-system-and-source-like-interpreters)

## Go

Metadata-rich even when stripped. Recognition: `go.buildid`, `runtime.gopanic`, very large static output, Go-toolchain source paths.

1. Run `GoReSym` or `redress` first; load recovered names into Ghidra (golang-loader plugin).
2. Model layouts: `string{ptr,len}` (not null-terminated), `slice{ptr,len,cap}`, `iface{type,data}`.
3. Trace `main.main`, crypto packages, `embed.FS` artifacts, channel validators.
4. `-ldflags -X` strings are patchable in-place (same length).

## Rust

Noisy decompilation, but panic strings and demangled names are generous. Recognition: `/rustc/` paths, `core::panicking`, `.rustc` section, `_ZN…` symbols.

1. `strings | grep panicked` (panic messages leak source paths and line numbers — fastest lead).
2. `nm | rustfilt` to demangle.
3. Model `Option`/`Result` (discriminant byte: 0=None/Err, 1=Some/Ok), `Vec`, `String`, `&str`.
4. Read iterator-fused loops as stateful pipelines, not compiler junk. For hidden literal buffers, dump `.rodata`/xmmword constants before full CFG recovery.

Also a version-driven exploitation surface: lifetime/soundness bugs in pinned compiler versions, and `#[no_mangle] extern "C"` symbol shadowing against sandbox harnesses.

## Swift

Use Swift metadata and demangling before generic pseudocode. `swift demangle '<mangled>'`. Look for `__swift5_*` sections, protocol witness tables (dispatch), and runtime helpers (`swift_allocObject`, `swift_release`). Enable Ghidra's Swift analyzer.

## D

Unique mangling (`_D` prefix, not C++ style); template-heavy with many near-duplicate variants. Script the function family instead of reading each by hand.

## C++

Recovery anchors: vtables / virtual dispatch, RTTI/typeinfo chains, `std::string` SSO, `std::vector` triplets, `std::map`/`std::unordered_map` storage shapes.

## Kotlin and JVM

`jadx`, CFR, or Fernflower with Kotlin-aware output. Coroutines compile into explicit state machines: `invokeSuspend` drives states; `Companion`/data-class helpers are naming anchors; ignore `Intrinsics.checkNotNull` noise. **Kotlin/Native** drops JVM reflection and looks like C++/LLVM output — markers `konan`, ARC-like ownership flows.

## Haskell

Closures are the unit of execution. Identify `hs_main`; use `hsdecomp` when available; reason about info tables, thunks, and closure payloads; replace `Main_main_info` only when static recovery stalls. If a `.cmm` artifact ships, it is usually the cleanest route — solve exponential recursive string builders with memoized size + indexed access, not materialization.

## Nuitka-Compiled Python

Even compiled to native, the import system stays hookable. Drop CWD stub modules to hijack import resolution and log decrypted runtime behavior before deep binary RE.

## Python Bytecode

`dis.dis()`-style validators leak constants, tuple targets, loop structure, and transforms. Use `LOAD_CONST`/`BUILD_TUPLE`/`BINARY_XOR`/`ord` call sites as the reconstruction spine. Interleaved even/odd XOR tables are common. If a bundled interpreter remaps opcodes, recover or reuse that interpreter (diff `opcode.pyc` against stock CPython) before fighting decompilers. Treat disassembly as evidence; decompiled output is convenience.

## WASM

PE-free, near-native logic behind packaging. `wasm2c` to compile and analyze; `wasm2wat`/`wat2wasm` to patch (flip comparisons, change constants). See [tools.md](tools.md#bytecode-and-managed-runtimes).

## Esolangs

- **Brainfuck** — count `+`/`-` after `,` to derive expected bytes; count read ops as a correctness oracle; pattern-match known comparison idioms instead of full interpretation.
- **FRACTRAN** — invert by swapping numerator/denominator, run backward; I/O encoded as prime-factorization exponents.
- **Functional pipelines (e.g. OPAL)** — build inverse functions stage-by-stage; brute-force only aggregate effects when a transform depends on unknown prior state.
- **Non-bijective substitution tables** — build reverse buckets and disambiguate with format knowledge, side channels, or re-encryption checks.

## Build-System and Source-Like Interpreters

- **GNU Make** — a `Makefile` can hide a full state machine: extract the transition table and simulate externally rather than tracing recursive `$(eval)`.
- **UEFI** — payloads are PE32+; extract firmware volumes, identify DXE/boot components, follow boot-service callbacks.
- **Transpilation to C** — for hostile bytecode or weird mini-ISAs, transpile opcodes to C and let the optimizer remove the fog.
- **Coverage side-channel** — coverage artifacts expose which branch-dependent crypto states ran, turning coverage JSON into a key/plaintext oracle.
