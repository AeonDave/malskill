# CTF Reverse - Tooling

Tool routing for the full reversing loop: triage, disassemble/decompile, debug, instrument, emulate, deobfuscate, diff, patch. Pick the smallest tool that yields a validation signal. Tool syntax lives in the dedicated tool skills; this file decides *when* each family fits.

## Table of Contents
- [Triage Baseline](#triage-baseline)
- [Disassemblers and Decompilers](#disassemblers-and-decompilers)
- [Debuggers](#debuggers)
- [Dynamic Instrumentation and Symbolic Execution](#dynamic-instrumentation-and-symbolic-execution)
- [Emulation](#emulation)
- [Oracle and Side-Channel Breakpoints](#oracle-and-side-channel-breakpoints)
- [Bytecode and Managed Runtimes](#bytecode-and-managed-runtimes)
- [Packers and Protectors](#packers-and-protectors)
- [Deobfuscation Frameworks](#deobfuscation-frameworks)
- [Binary Diffing](#binary-diffing)
- [Patching](#patching)

## Triage Baseline

Low-noise first pass before specialized tooling:

```bash
file binary
checksec --file=binary
strings -n 6 binary | grep -iE "flag|secret|key"
readelf -hSl binary        # -l (program headers) survives section-header corruption
objdump -M intel -d binary
```

## Disassemblers and Decompilers

- **Ghidra** — best free all-rounder: type recovery, xref reading, headless scripting, emulator-assisted local decryption. `analyzeHeadless <proj> tmp -import binary -postScript script.py`.
- **radare2 / Rizin + Cutter** — fast structural triage and scriptable JSON. `r2 -d binary; aaa; afl; pdf @ main`. `V!` panels are ideal for live VM tracing. Cutter bundles the Ghidra decompiler via r2ghidra.
- **Binary Ninja** — fast scripting surface and a strong second-opinion decompiler; official **Sidekick** plugin adds LLM-driven rename/summarize.
- **RetDec** — LLVM-based, multi-arch (x86/ARM/MIPS/PPC/PIC32), emits compilable C. Use for architectures Ghidra handles poorly.
- **dogbolt** — cross-check one ugly function across several decompilers before trusting any single rendering.
- **LLM-assisted decompilation** — for many small crackmes or unknown VM handlers, rapid rename/summarize is worth minutes: **Gepetto** (IDA), **aidapal** (IDA, local models), **GhidrAssist** / **GhidraChatGPT** (Ghidra), **r2ai** (radare2). Treat output as hypothesis, verify against raw disasm.

## Debuggers

- **GDB (+ pwndbg / GEF)** — breakpoint-driven extraction, register/flag patching to walk a success path, Python scripting for brute-force and tracing.
  ```bash
  b *main+0x100
  b *0x401234 if $rax == 0x41          # conditional
  watch *(int*)0x601050                # data watchpoint
  ignore 1 99                          # skip N hits
  ```
  - **rr** (`rr record` / `rr replay`) for reverse/deterministic debugging.
  - Python `gdb.Breakpoint.stop()` returning `False` logs comparison operands without halting.
- **lldb** — natural debugger for Mach-O, Swift, and Apple-heavy targets.
- **x64dbg** — quickest Windows-first GUI debugger; hardware breakpoints + ScyllaHide for automatic anti-debug patching.

## Dynamic Instrumentation and Symbolic Execution

- **Frida** — runtime truth faster than static certainty: hook `strcmp`/`memcmp`/crypto APIs, patch return values, hook Java methods, neutralize anti-debug. `frida -f ./binary -l hook.js`.
- **angr** — full symbolic exploration for validators with clear success/avoid states. Constrain input early (printable, known prefix); hook expensive crypto/IO to prevent path explosion.
- **Triton** — concrete+symbolic (DSE): follows one path, far less prone to explosion than angr. Best for single-path deobfuscation and taint, then simplify collected constraints.
- **Manticore** — angr-like; strongest for EVM and simpler Linux binaries.

## Emulation

- **Unicorn** — CPU-level control without OS emulation: isolated decryption loops, mixed-mode stagers, instruction hooks on small routines. Mixed-mode pitfall: 64→32-bit `retf` needs `UC_MODE_32` plus copied GPRs/EFLAGS/XMM.
- **Qiling** — Unicorn + OS layer (syscalls, filesystem, registry). Emulates Linux/Windows/macOS/ARM/MIPS/RISC-V; bypasses all anti-debug by default (no debugger artifacts). Hook syscalls/addresses/APIs in Python to short-circuit checks.

## Oracle and Side-Channel Breakpoints

- **strcmp / memcmp** — late-stage compares leak the entire target transform in one run; the final compare site is gold.
- **putchar / write** — break on output to turn fake delays into instant extraction.
- **Intel Pin** — instruction counting turns sequential validators and movfuscated binaries into oracles: more correct input ⇒ more executed work.
- **LD_PRELOAD** — freeze `time()`/`rand()` for deterministic validators; hook `memcmp` to return richer progress than intended.
- **libSegFault.so** — crash-time register snapshot with near-zero setup when GDB is blocked.

## Bytecode and Managed Runtimes

- **Python** — `marshal`+`dis` for disassembly (ground truth); `pycdc`/`uncompyle6` when version-compatible; `Pyarmor-Static-Unpack-1shot` for Pyarmor 8/9. Match the exact CPython version — opcode mismatches waste hours.
- **WASM** — `wasm-decompile` (wabt) for quickly readable pseudo-C; `wasm2c checker.wasm -o checker.c && gcc -O3 …` when you want to link/instrument; `wasm2wat`/`wat2wasm` to patch comparisons/constants.
- **.NET** — **dnSpyEx** (community fork, .NET 6/7/8/9 support — the original `dnSpy/dnSpy` is inactive since 2020), ILSpy, dotPeek. NativeAOT keeps .NET semantics but loses IL-level comfort.
- **RISC-V** — Capstone with compressed-instruction mode + QEMU user-mode when no native env exists.
- **boolector** — materially faster than Z3 on pure QF_BV bit-twiddling hash validators.

## Packers and Protectors

- **UPX** — `upx -d`; if it fails, verify section names/header/version markers, then patch tampered metadata.
- **PyInstaller** — extract the archive before bytecode triage.
- **VMProtect** — `.vmp0`/`.vmp1` sections, pushad-like VM entry, large indirect-jump handler table. For CTF, trace operations on the input rather than full devirtualization (VMPAttack, NoVmp/VTIL).
- **Themida / WinLicense** — `.themida`/`.winlice`, heavy kernel-level anti-debug. Run to OEP, dump with ScyllaHide+Scylla (Themida preset), fix IAT, analyze the dump as a normal binary.
- **Custom packers** — dump after OEP or stage transition; known-plaintext against decrypted prologues recovers per-stage keys.

## Deobfuscation Frameworks

- **D-810 (IDA)** / **GOOMBA (Ghidra)** — pattern-based MBA simplification, opaque-predicate removal, constant folding, partial CFG unflattening.
- **Miasm** — IR lifting + symbolic execution to simplify expression trees and trace data flow.
- **LLVM-IR lifting** — transpile a custom VM's bytecode to LLVM IR, then `opt -O3` (inlining, constant folding, DCE) collapses thousands of lines of handler IL into the underlying algorithm.

## Binary Diffing

Essential when a challenge ships patched+original or two versions. Export from IDA/Ghidra (BinExport), then **BinDiff** (similarity score per function, unmatched = new/removed) or **Diaphora** (free IDA/Ghidra plugin). Diff first to find the vulnerability or hidden code.

## Patching

```python
# pwntools — replace a check with an immediate return
elf = ELF('./binary'); elf.asm(elf.symbols.ptrace, 'xor eax,eax; ret'); elf.save('patched')
# Binary Ninja
bv = bn.open_view("binary"); bv.write(0x401234, b"\x90"*5); bv.save("patched")
# LIEF — format-level edits (entrypoint, sections)
b = lief.parse("binary"); b.header.entrypoint = 0x401000; b.write("patched")
```

In Ghidra, patch the conditional jump (`JNZ 0x75` ↔ `JZ 0x74`) or immediate, then export as Original File. Re-`chmod +x` after patching.
