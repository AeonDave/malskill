# CTF Reverse - Emulation and Side-Channel Tooling

Focused tool reference for cases where classic debugging is the wrong abstraction: cross-arch binaries, anti-debug-heavy targets, dynamic symbolic execution, and instruction-count or preload oracles.

## Table of Contents
- [Unicorn](#unicorn)
- [Qiling](#qiling)
- [Triton](#triton)
- [Intel Pin](#intel-pin)
- [Opcode-Only Trace Reconstruction](#opcode-only-trace-reconstruction)
- [LD_PRELOAD Time Freezing](#ld_preload-time-freezing)
- [LD_PRELOAD Comparison Oracles](#ld_preload-comparison-oracles)

## Unicorn

Use Unicorn when you want CPU-level control without needing full OS emulation.

Best for:
- isolated decryption loops
- mixed-mode stagers
- instruction-level hooks on small, contained routines

## Qiling

Use Qiling when Unicorn is too low-level and you need syscalls, filesystems, or cross-platform process semantics.

## Triton

Use Triton for single-path symbolic execution, taint, and solver extraction when full angr exploration is overkill.

## Intel Pin

Instruction counting turns sequential validators and movfuscated binaries into measurable oracles. When correctness increases executed work, Pin can brute-force structure without understanding semantics.

## Opcode-Only Trace Reconstruction

Even data-free traces leak branch structure. Sort, deduplicate, rebuild blocks, and infer the underlying algorithm from branch behavior.

## LD_PRELOAD Time Freezing

Freeze `time()` or `rand()` to make otherwise unstable validators deterministic and oracle-friendly.

## LD_PRELOAD Comparison Oracles

Hook `memcmp` or related APIs to return richer progress information than the original binary intended.
