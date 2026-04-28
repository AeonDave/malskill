---
name: python-reverse
description: "Binary reverse engineering with Python: analyze, parse, and disassemble ELF/PE executables using pwntools, capstone, Frida, and custom parsing tools. Use when understanding malware, debugging binary failures, analyzing section structure, extracting strings/entropy, or instrumenting runtime behavior."
license: MIT
compatibility: "Python 3.11+. Core libraries: pwntools, capstone, pyelftools, pefile, Frida (dynamic). Optional: pyinstaller-extractor, binwalk, upx."
metadata:
  author: AeonDave
  version: "1.0"
---

# Python Reverse Engineering

This skill focuses on **hands-on binary analysis** with Python: static parsing (headers, sections, strings, entropy) and dynamic instrumentation (Frida hooks, syscall tracing).

## When to activate

- You need to understand why an executable fails or crashes.
- Analyzing malware, unobfuscated binaries, or stripped ELFs for behavior/functionality.
- Extracting metadata (strings, imports, entropy regions, entrypoints, section layout).
- Instrumenting runtime behavior with Frida hooks or syscall analysis.
- Comparing binary versions or detecting hardening/packing.

---

## Core principles

- **Parse from scratch first**: Use Python structs or pwntools before automated tools.
- **Entropy identifies obfuscation**: High entropy ≈ encrypted/compressed; low entropy ≈ plaintext strings.
- **Imports reveal intent**: Suspicious API combos (VirtualAlloc + CreateRemoteThread) flag injection.
- **Strings are quick wins**: Often reveal C2 addresses, file paths, error messages without disassembly.
- **Frida is for behavior**: When you need to see what the binary *does* at runtime, not what it *says*.

---

## Outcome expectations

- Binary structure is mapped (sections, headers, entrypoints).
- Strings, imports, entropy regions, and suspicious API patterns are identified.
- Custom analysis scripts (IAT dump, entropy heatmap, section diff) are written and run.
- Runtime behavior is instrumented via Frida when static analysis is insufficient.

---

## Recommended workflow

1. **Triage**: File type (ELF/PE/Mach-O?), architecture, bitness, stripped/debug symbols.
2. **Headers**: Parse DOS/COFF headers, optional header, entry point, base address.
3. **Sections**: Extract .text, .data, .rodata, .relro; flag unusual sections.
4. **Strings**: Dump ASCII/UTF-8 strings; search for patterns (URLs, IPs, paths, error messages).
5. **Imports**: Enumerate DLLs and functions (PE) or dynamic symbols (ELF); flag suspicious APIs.
6. **Entropy**: Block-by-block analysis to identify encrypted/compressed regions.
7. **Disassembly** (if needed): Use capstone or pwntools to disassemble hotspots.
8. **Frida instrumentation**: Hook critical functions or syscalls to observe runtime behavior.
9. **Comparison**: Diff two binary versions for delta analysis (hardening, patching, payload changes).

---

## Quick review checklist

- Binary parsed without crashing; sections are readable.
- Entry point and imports are enumerated.
- Strings scanned for suspicious patterns (URLs, credentials, error messages).
- Entropy zones identified; high-entropy blobs are flagged.
- Frida hooks compile and attach without crashes.

---

## Anti-patterns

- **Blind disassembly without context**: Always check strings, imports, and entropy first.
- **Ignoring section flags**: RWX sections, missing RELRO, or executable heap are red flags.
- **Over-relying on automated tools**: Use IDA/Ghidra for complex cases; Python for automation and scripting.
- **Frida hooks without error handling**: Always wrap hooks in try/except; unhandled exceptions kill the session.

---

## Resources

Load on demand:

- `references/binary-formats.md` — ELF/PE parsing, headers, sections, symbols.
- `references/pwntools-reference.md` — ELF object, string search, section access, disassembly.
- `references/static-analysis.md` — strings, imports, entropy, IAT dumps, suspicious APIs.
- `references/capstone.md` — disassembly, instruction decoding, syntax options.
- `references/frida-basics.md` — attach, hooks, intercept calls, bytecode patching.
- `references/custom-tooling.md` — write entropy heatmaps, section diffs, API detectors.
