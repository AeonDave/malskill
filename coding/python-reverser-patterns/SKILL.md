---
name: python-reverser-patterns
description: "Reverse binaries and Python artifacts with Python: parse ELF/PE, disassemble with pwntools/capstone, instrument with Frida, recover .pyc and PyInstaller payloads. Use when analyzing malware, packed Python, stripped binaries, or runtime hooks — not for CPython language style (python-patterns)."
license: MIT
compatibility: "Python 3.11+ (guidance baseline; current stable CPython 3.14.7). Core: pwntools, capstone, pyelftools, pefile. Dynamic: Frida 17+ GumJS (Python is the host). Optional: xdis, pyinstxtractor-ng, LIEF."
metadata:
  author: AeonDave
  version: "1.1"
---

# Python Reverse Engineering

Hands-on reversing **with** Python: ELF/PE parsing, strings/imports/entropy, disassembly, Frida, and Python bytecode (`.pyc` / PyInstaller). Language idioms belong in `python-patterns`.

## When to activate

- Mapping why an ELF/PE fails, what malware does, or how a stripped binary is laid out.
- Extracting strings, imports, entropy regions, entrypoints, section flags.
- Instrumenting runtime with Frida (host Python, hooks in GumJS).
- Recovering logic from `.pyc`, `__pycache__`, or a PyInstaller/py2exe-style bundle.
- Diffing two binary versions (hardening, packing, payload change).

## Core principles

- **Triage before disassembly**: strings, imports, entropy, then hotspots.
- **Match interpreter to bytecode**: `marshal`/`dis` only on the same CPython version as the `.pyc`; otherwise `xdis`/`pydisasm`.
- **Do not execute recovered code** on the analysis host; `dis` is read-only, `exec` is not.
- **Frida injects GumJS**, not Python. Host API: `attach`/`spawn`/`create_script`.
- **Entropy flags packing**: high-entropy blobs are compressed/encrypted until proven otherwise.

## Outcome expectations

- File type, arch, and layout (sections, entry, imports) are known.
- Suspicious APIs and high-entropy regions are listed with offsets.
- `.pyc` payloads are disassembled with a version-matched tool; decompile is opportunistic.
- Frida hooks attach (or spawn) without using removed Frida 16 static `Module.*` APIs.

## Recommended workflow

1. **Triage**: ELF / PE / Mach-O / `.pyc` / PyInstaller overlay. Packed Python → `references/pyc-bytecode.md` first.
2. **Headers**: parse ELF/PE (or LIEF when you will rewrite). Load `references/binary-formats.md`.
3. **Sections / imports / strings / entropy**: `references/static-analysis.md`, `references/pwntools-reference.md`.
4. **Disassemble hotspots**: `references/capstone.md` (Capstone) or `ELF.disasm` (returns a string).
5. **Runtime**: Frida when static is insufficient — `references/frida-basics.md`. Spawn if the interesting path is before a stable attach.
6. **Custom scripts**: IAT dump, entropy map, section diff — `references/custom-tooling.md`.

Pyarmor, custom opcode maps, and Nuitka-as-native: keep the Python-API path here; load [reversing-technique languages.md](../../offensive-techniques/reversing-technique/references/languages.md) for those packer-specific recoveries.

## Quick review checklist

- Magic/arch parsed; file offsets vs VAs are not mixed.
- Imports enumerated; ordinal-only PE imports are not assumed to have names.
- Strings and entropy scanned before wide disassembly.
- `.pyc` magic matches the interpreter (or `pydisasm` was used).
- Frida scripts use `Process.getModuleByName` / `Module.getGlobalExportByName` (Frida 17+).

## Anti-patterns

- Blind Capstone over the whole file (alignment, data-in-code, packing).
- `marshal.loads` of a `.pyc` **including** the 16-byte header, or on the wrong Python version.
- Treating `uncompyle6` as valid past 3.8, or `pycdc` as guaranteed on 3.13–3.14.
- `Module.findExportByName` / static `Module.getExportByName` (removed in Frida 17).
- `Interceptor.replace` with `onEnter`/`onLeave` (that is `attach`; replace takes a `NativeCallback`).

## Resources

Load on demand:

- `references/binary-formats.md` — load when parsing or patching ELF/PE/Mach-O headers and sections
- `references/pwntools-reference.md` — load when using `ELF`, `search`, `read`, `disasm`, `context.binary`
- `references/static-analysis.md` — load for strings, imports, entropy, suspicious APIs
- `references/capstone.md` — load when decoding instructions or scanning gadgets
- `references/frida-basics.md` — load when attaching/spawning and hooking (Frida 17+ JS API)
- `references/pyc-bytecode.md` — load for `.pyc`, `marshal`/`dis`, xdis, PyInstaller unpack
- `references/custom-tooling.md` — load when writing a reusable IAT/entropy/diff script
