---
name: reverse-ctf
description: "Lab/CTF: reverse challenges; compiled binaries, bytecode, mobile/firmware, custom VMs, packed samples, anti-debug, validators."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Reverse CTF

Goal: solve reverse-engineering CTF tasks with professional methodology, curated challenge patterns, and reproducible evidence.

## When this skill applies

- compiled binaries, bytecode, mobile apps, firmware blobs, custom VMs, packed samples, obfuscated scripts, anti-debug logic, or validation algorithms
- tasks requiring static/dynamic analysis, algorithm extraction, patching, emulation, or symbolic execution

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load targeted references only for deep technique details.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `reversing-technique`
- `crypto-technique`
- `forensic-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and specialized reverse-CTF patterns.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `ghidra`
- `radare2`
- `binaryninja`
- `gdb`
- `x64dbg`
- `frida`
- `dnspy`
- `apktool`
- `jadx`
- `binwalk`
- `checksec`
- `strings`
- `objdump`
- `readelf`
- `upx`
- `patchelf`
- `strace`
- `ltrace`
- `capa`
- `sagemath`
- `openssl`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Triage format, language/runtime, packing, and anti-analysis before deep decompilation.
- Define objective: recover secret, reconstruct algorithm, bypass check, emulate VM, or extract config.
- Cross-check static hypotheses dynamically and document exact validation signal.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

Each reference file is scoped to one reversing lane. Load the specific file that matches your immediate task; cross-links are only for adjacent pivots after the first signal is understood.

### Anti-Analysis Techniques

- [references/anti-analysis-detection-and-evasion.md](references/anti-analysis-detection-and-evasion.md) — anti-debug (ptrace, IsDebuggerPresent, TracerPid), anti-VM (CPUID, MAC addresses), anti-DBI (Frida, Pin), code-integrity checks.
- [references/anti-analysis-obfuscation-and-runtime.md](references/anti-analysis-obfuscation-and-runtime.md) — anti-disassembly techniques, opaque predicates, junk code, function chunking, bypass strategies, challenge-specific handler tricks.

### Language and Runtime Reversing

- [references/languages-core-scripting-and-esolangs.md](references/languages-core-scripting-and-esolangs.md) — Python bytecode (dis, constants, Pyarmor unpacking), UEFI, Unity IL2CPP, HarmonyOS HAP/ABC, esolangs (Brainfuck), FRACTRAN, GNU Make, transpilation to C.
- [references/languages-compiled-go-rust-and-native.md](references/languages-compiled-go-rust-and-native.md) — Go symbol recovery (GoReSym), Rust demangling and panic strings, Swift decompilation, D template recovery, C++ vtables, ABI-aware decompiler reading.
- [references/languages-compiled-managed-and-functional.md](references/languages-compiled-managed-and-functional.md) — Kotlin/JVM with jadx and CFR, Kotlin/Native ARC patterns, Haskell STG closures and GHC CMM, Nuitka Python-to-native workflows.
- [references/languages-platforms-mobile-and-apps.md](references/languages-platforms-mobile-and-apps.md) — Android JNI RegisterNatives, DEX runtime patching, .so loading bypass, Firebase Cloud Functions, Frida pinning bypass, root/debug detection, logcat key extraction, native JNI key recovery, Smali injection, Electron+native, Node.js introspection, Intel SGX enclaves.
- [references/languages-platforms-games-and-special-platforms.md](references/languages-platforms-games-and-special-platforms.md) — Roblox place file version diffing, Godot asset extraction, Rust serde_json schema recovery, Verilog state machines, prefix-by-prefix hash reversal, Ruby/Perl polyglot constraints, IBM AS/400 SAVF EBCDIC, Glulx interactive fiction, Game Boy Z80, KVM guest analysis, Coreboot ROM bit-flip patterns.

### Static Patterns and Analysis

- [references/patterns-static-vm-obfuscation-and-memory.md](references/patterns-static-vm-obfuscation-and-memory.md) — custom VM reversing, anti-debugging static patterns, nanomites, self-modifying code, mixed-mode x86-64/x86 stagers, LLVM control-flow flattening, seccomp/BPF filters, exception-handler obfuscation, memory dump analysis.
- [references/patterns-transforms-keystreams-and-signal-paths.md](references/patterns-transforms-keystreams-and-signal-paths.md) — known-plaintext XOR, S-box and keystream families, byte-wise uniform transforms, x86-64 gotchas (sign extension, branch ordering), custom mangle reversal, position-based transforms, hex-encoded comparisons, signal-based binary exploration.
- [references/patterns-runtime.md](references/patterns-runtime.md) — runtime-heavy patterns for emulation, instrumentation, and dynamic analysis that don't fit purely static recovery.

### CTF-Specific Patterns

- [references/patterns-ctf-analysis-and-extraction.md](references/patterns-ctf-analysis-and-extraction.md) — emulator opcodes + LD_PRELOAD key extraction, Spectre-RSB SPN ciphers, image XOR masks, shellcode mmap RWX, recursive execve subtraction, byte-at-a-time block ciphers, mathematical convergence bitmaps, Windows PE XOR bitmap OCR, two-stage RC4+VM, GBA ROM Meet-in-the-Middle hashing.
- [references/patterns-ctf-systems-and-vms.md](references/patterns-ctf-systems-and-vms.md) — Sprague-Grundy game theory binaries, kernel module maze solving, multi-threaded VMs with channels, backdoor detection via diffing, binfmt modules with RC4, hash-resolved imports, ELF header corruption, VM trace diffing.
- [references/patterns-ctf-constraint-and-crypto.md](references/patterns-ctf-constraint-and-crypto.md) — multi-layer self-decrypting binaries, embedded ZIP+XOR, stack strings from .rodata, prefix hash brute-force, CVP/LLL lattice solving, decision tree extraction, GF(2^8) Gaussian elimination, ROPfuscated chains.
- [references/patterns-ctf-runtime-and-ui.md](references/patterns-ctf-runtime-and-ui.md) — Z3 for single-line Python circuits, sliding-window popcount, keyboard LED Morse code, C++ destructor validation, syscall side-effects, MFC dialog handlers, VM sequential key chains, Burrows-Wheeler inversion, OpenType font ligatures.
- [references/patterns-ctf-graphics-firmware-and-automation.md](references/patterns-ctf-graphics-firmware-and-automation.md) — GLSL shader VMs, instruction counters as state, thread race conditions, ESP32/Xtensa ROM symbols, batch crackme automation via objdump, fork+pipe dead-branch anti-analysis, time-locked binaries, ARM in image pixels.
- [references/patterns-ctf-math-and-engine-exploits.md](references/patterns-ctf-math-and-engine-exploits.md) — x86 MBR psadbw constraint solving, TensorFlow DNN inversion, BPF JIT to x64 assembly, single-byte XOR sweeps, WebKit OOB exploitation, multi-modulus CRT keygens.

### Reverse-Engineering Tools

- [references/tools-debuggers-and-core-workflow.md](references/tools-debuggers-and-core-workflow.md) — GDB breakpoint scripting and memory inspection, radare2 disassembly and r2pipe automation, Ghidra headless analysis and emulator-assisted decryption, Binary Ninja rapid scripting, dogbolt multi-decompiler cross-checks, baseline file commands and CLI workflows.
- [references/tools-bytecode-mobile-and-managed.md](references/tools-bytecode-mobile-and-managed.md) — Python bytecode (marshal, dis, pycdc, uncompyle6, Pyarmor unpacking), WASM decompilation (wasm2c), Android APK toolchain (apktool, jadx, unzip), HarmonyOS HAP/ABC (abc-decompiler CLI), .NET analysis (dnSpy, ILSpy, NativeAOT), UPX unpacking, PyInstaller extraction, LLVM IR lifting, RISC-V Capstone analysis, boolector bitvector hash reversal.
- [references/tools-dynamic-analysis-and-instrumentation.md](references/tools-dynamic-analysis-and-instrumentation.md) — Frida runtime interception and return-value patching, angr symbolic execution and managed state, lldb for Apple targets, x64dbg Windows debugging with hardware breakpoints, register/output side-channel breakpoints, radare2 VM tracing panels, libSegFault crash dumps, r2pipe constraint extraction, strcmp/memcmp oracle breakpoints.
- [references/tools-emulation-and-side-channels.md](references/tools-emulation-and-side-channels.md) — Unicorn CPU-level emulation for isolated routines and mixed-mode stagers, Qiling full-system emulation with OS syscalls, Triton single-path symbolic execution and taint, Intel Pin instruction counting for sequential validators and movfuscated binaries, opcode-only trace reconstruction, LD_PRELOAD time freezing and comparison oracles.
- [references/tools-advanced.md](references/tools-advanced.md) — VMProtect analysis and deobfuscation strategies, Themida/WinLicense recognition and approach, binary diffing (BinDiff, Diaphora), Triton symbolic-execution workflows, DebugBreak scripting patterns, custom packer-specific techniques.

### Platform-Specific Reversing

- [references/platforms-apple-firmware-and-kernel.md](references/platforms-apple-firmware-and-kernel.md) — Mach-O format, code signing and entitlements, Objective-C runtime introspection (class-dump), Swift demangling and runtime functions, iOS app decryption and jailbreak detection bypass, dyld and dynamic linking, firmware extraction (binwalk), unpacking (unsquashfs, cpio), ARM/MIPS/RISC-V QEMU workflows, Linux kernel modules, eBPF programs, Windows kernel drivers.
- [references/platforms-games-hardware-and-special-cases.md](references/platforms-games-hardware-and-special-cases.md) — Unreal Engine blueprint bytecode, Unity IL2CPP (Il2CppDumper), anti-cheat bypass, Lua decompilation, automotive CAN bus, RISC-V custom extensions, ARM64/AArch64 calling conventions, MIPS64 Cavium CP2 crypto, microcontroller MMIO, MBR/bootloader QEMU+GDB, Game Boy Z80, KVM ioctl patterns, Coreboot ROM analysis.

### Quick Reference

- [references/field-notes.md](references/field-notes.md) — quick triage checklist and cross-links for common reverse-CTF patterns and decision trees.
