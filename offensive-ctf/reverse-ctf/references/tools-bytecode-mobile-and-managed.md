# CTF Reverse - Bytecode, Mobile, and Managed Tooling

Focused tool reference for non-ELF/PE-native artifacts: bytecode, APKs, managed runtimes, packed outputs, and architecture-specific helpers.

## Table of Contents
- [Python Bytecode Tools](#python-bytecode-tools)
- [WASM Analysis](#wasm-analysis)
- [Android APK Toolchain](#android-apk-toolchain)
- [HarmonyOS HAP/ABC](#harmonyos-hapabc)
- [.NET Analysis](#net-analysis)
- [Packed Binaries](#packed-binaries)
- [LLVM IR](#llvm-ir)
- [RISC-V Analysis Helpers](#risc-v-analysis-helpers)
- [boolector for Bitvector Hash Reversal](#boolector-for-bitvector-hash-reversal)

## Python Bytecode Tools

- `marshal` + `dis` for quick disassembly
- `pycdc` / `uncompyle6` when version-compatible
- Pyarmor 8/9: `Pyarmor-Static-Unpack-1shot`

## WASM Analysis

```bash
wasm2c checker.wasm -o checker.c
gcc -O3 checker.c wasm-rt-impl.c -o checker
```

Use when the browser/runtime hides simple native-like logic behind WASM packaging.

## Android APK Toolchain

```bash
apktool d app.apk -o decoded
jadx app.apk
unzip app.apk -d extracted
```

Use this stack to split resources, Java/Kotlin code, DEX, and native libraries before deeper JNI work.

## HarmonyOS HAP/ABC

Prefer the CLI entrypoint of `abc-decompiler` and start with `-m simple`.

## .NET Analysis

Primary stack:
- dnSpy
- ILSpy
- dotPeek

NativeAOT deserves its own suspicion: it keeps .NET semantics but loses familiar IL-level comfort.

## Packed Binaries

- UPX: unpack first
- custom packers: dump after OEP or stage transition
- PyInstaller: extract archive before bytecode triage

## LLVM IR

Lift `.ll` into assembly or object code when you need a lower-noise view of the actual optimizer-facing program.

## RISC-V Analysis Helpers

Use Capstone with compressed-instruction support and QEMU user-mode when no native environment exists.

## boolector for Bitvector Hash Reversal

For custom bit-twiddling hash validators, boolector is often materially faster than Z3 on pure QF_BV workloads.
