# CTF Reverse - Core Scripting and Esolang Techniques

Focused language reference for scripting runtimes, bytecode formats, esolangs, and source-like interpreters where the fastest path is usually extraction or semantic lifting instead of raw binary RE.

## Table of Contents
- [Python Bytecode Reversing](#python-bytecode-reversing)
- [Python Opcode Remapping](#python-opcode-remapping)
- [Pyarmor 8/9 Static Unpack](#pyarmor-89-static-unpack)
- [DOS Stub Analysis](#dos-stub-analysis)
- [Unity IL2CPP Games](#unity-il2cpp-games)
- [HarmonyOS HAP/ABC Reverse](#harmonyos-hapabc-reverse)
- [Brainfuck and Other Esolangs](#brainfuck-and-other-esolangs)
- [UEFI Binary Analysis](#uefi-binary-analysis)
- [Transpilation to C](#transpilation-to-c)
- [Code Coverage Side-Channel](#code-coverage-side-channel)
- [Functional Language Reversing (OPAL)](#functional-language-reversing-opal)
- [Python Version-Specific Bytecode](#python-version-specific-bytecode)
- [Non-Bijective Substitution Tables](#non-bijective-substitution-tables)
- [FRACTRAN Program Inversion](#fractran-program-inversion)
- [GNU Make Turing Machine Simulator](#gnu-make-turing-machine-simulator)

## Python Bytecode Reversing

Typical `dis.dis()`-style validators leak everything you need: constants, tuple targets, loop structure, and transforms.

```python
flag = [''] * flag_length
for i in range(len(p1)):
    flag[2*i] = chr(p1[i] ^ key1)
    flag[2*i+1] = chr(p2[i] ^ key2)
print(''.join(flag))
```

Use `LOAD_CONST`, `BUILD_TUPLE`, `BINARY_XOR`, and `ord` call sites as the reconstruction spine.

## Python Opcode Remapping

If a bundled interpreter changes opcode numbering, recover or reuse that interpreter before fighting decompilers.

- Look for modified `opcode.pyc` in PyInstaller output.
- Diff remapped opcodes against stock CPython.
- Prefer using the challenge's own interpreter with `uncompyle6`/`pycdc` when possible.

## Pyarmor 8/9 Static Unpack

Use `Pyarmor-Static-Unpack-1shot` when the artifact is armored but still ships a compatible runtime.

```bash
python /path/to/shot.py /path/to/scripts
```

Treat disassembly as ground truth; decompiled output is convenience, not evidence.

## DOS Stub Analysis

Large PE DOS stubs can contain the real checker. Load the stub as 16-bit DOS or run it in DOSBox before assuming the PE body matters.

## Unity IL2CPP Games

IL2CPP still leaks symbols and metadata through `global-metadata.dat`, dumper output, and native loader behavior.

- Primary native targets: `GameAssembly.dll`, `libil2cpp.so`
- First pass: `Il2CppDumper`
- If metadata is encrypted, reverse the metadata-loading path and recover the decryption first

## HarmonyOS HAP/ABC Reverse

`.hap` packages are ZIP-like containers; extract `.abc` and decompile with the CLI entrypoint, not GUI mode.

```bash
java -cp "./jadx-dev-all.jar" jadx.cli.JadxCLI -m simple -log-level ERROR -d out modules.abc
```

## Brainfuck and Other Esolangs

Fastest recovery patterns:
- count `+`/`-` after `,` to derive expected bytes
- count read operations as an oracle when correct characters advance execution
- pattern-match known BF comparison idioms instead of fully interpreting control flow

## UEFI Binary Analysis

UEFI payloads are still PE32+ images. Extract firmware volumes, identify DXE/boot components, and follow boot-service callbacks.

## Transpilation to C

For hostile bytecode or weird mini-ISAs, transpile opcodes into C, then let the optimizer remove the fog.

## Code Coverage Side-Channel

Coverage artifacts can expose which branch-dependent crypto states occurred, turning coverage JSON into a plaintext or key oracle.

## Functional Language Reversing (OPAL)

Pure pipelines are often easier to invert than to decompile. Build inverse functions stage-by-stage and brute-force only aggregate effects when a transform depends on unknown prior state.

## Python Version-Specific Bytecode

Exact interpreter version matters. Alpha/beta bytecode mismatches waste hours; build the matching CPython when opcodes look wrong.

## Non-Bijective Substitution Tables

If the lookup table collides, build reverse buckets and disambiguate with format knowledge, side channels, or re-encryption checks.

## FRACTRAN Program Inversion

Swap numerators and denominators, run the target backward, then factor the result into prime exponents to recover symbols.

## GNU Make Turing Machine Simulator

A `Makefile` can hide a full state machine. Extract the transition table, decode it, and simulate externally rather than tracing recursive `$(eval)` by hand.
