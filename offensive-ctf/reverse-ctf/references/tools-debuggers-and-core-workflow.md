# CTF Reverse - Debuggers, Decompilers, and Core Workflow Tools

Focused tool reference for the first-line reversing workflow: inspect the file, recover structure, decompile or disassemble, and script the debugging loop.

## Table of Contents
- [GDB](#gdb)
- [Radare2](#radare2)
- [Ghidra](#ghidra)
- [Binary Ninja](#binary-ninja)
- [dogbolt Decompiler Comparison](#dogbolt-decompiler-comparison)
- [Useful Baseline Commands](#useful-baseline-commands)

## GDB

Use GDB for breakpoint-driven extraction, memory inspection, and fast automation around known comparison points.

```bash
gdb ./binary
start
b *main+0x100
x/s $rsi
info registers
```

Best for:
- Linux crackmes and validators
- breakpoint oracles at `strcmp`, `memcmp`, `putchar`, `write`
- patching registers or flags to walk a success path

## Radare2

Use radare2 when you want quick disassembly plus scriptable JSON output.

```bash
r2 -d ./binary
aaa
afl
pdf @ main
```

Best for:
- fast structural triage
- custom VM handler mapping
- r2pipe automation over large or repetitive binaries

## Ghidra

Ghidra stays the best all-rounder for free decompilation plus scripting.

```bash
analyzeHeadless /path/to/project tmp -import binary -postScript script.py
```

Best for:
- type recovery and xref-driven reading
- headless extraction scripts
- emulator-assisted local decryption of isolated routines

## Binary Ninja

Use Binary Ninja when you want a fast scripting surface or a second opinion on decompiler output.

## dogbolt Decompiler Comparison

Cross-check one ugly function across multiple decompilers before trusting any single pseudocode rendering.

## Useful Baseline Commands

```bash
file binary
checksec -file=binary
strings binary | grep -iE "flag|secret"
readelf -S binary
objdump -M intel -d binary
```

These are your low-noise first pass before specialized tooling.
