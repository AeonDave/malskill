# CTF Reverse - Managed, Functional, and Hybrid Compiled Runtimes

Focused language reference for runtimes that compile away source structure but still leak enough metadata, layout, or intermediate behavior to stay tractable.

## Table of Contents
- [Kotlin and JVM Binaries](#kotlin-and-jvm-binaries)
- [Kotlin/Native](#kotlinnative)
- [Haskell via STG Closures](#haskell-via-stg-closures)
- [Haskell via GHC CMM](#haskell-via-ghc-cmm)
- [Nuitka-Compiled Python](#nuitka-compiled-python)

## Kotlin and JVM Binaries

Use `jadx`, CFR, or Fernflower with Kotlin-aware output. The key structural clue is that coroutines compile into explicit state machines.

- `invokeSuspend` drives coroutine states
- `Companion` objects and data-class helpers are naming anchors
- `Intrinsics.checkNotNull` noise can be ignored once you understand the data path

## Kotlin/Native

Kotlin/Native drops JVM reflection comfort and looks more like C++/LLVM output.

Recognition markers:
- `konan`
- Kotlin native runtime helpers
- ARC-like ownership flows rather than GC-driven ones

## Haskell via STG Closures

Haskell binaries are easier once you accept that closures are the unit of execution.

- identify `hs_main`
- use `hsdecomp` when available
- reason about info tables, thunks, and closure payloads
- monkey-patch or replace `Main_main_info` only when static recovery stalls

## Haskell via GHC CMM

If a `.cmm` artifact is present, it is usually the cleanest route to the algorithm. Exponentially growing recursive string builders should be solved with memoized size computation and indexed access, not by materializing the structure.

## Nuitka-Compiled Python

Even when Python is compiled into a native binary, the import system often remains hookable.

Drop CWD stub modules to hijack import resolution and log decrypted runtime behavior before attempting deep binary-level reversing.
