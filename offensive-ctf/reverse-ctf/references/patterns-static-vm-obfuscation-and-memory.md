# CTF Reverse - Static Patterns: VMs, Obfuscation, and Memory Tricks

Focused pattern reference for static-heavy reversing where the job is to recover structure, hidden control flow, or decryption layout before dynamic shortcuts become useful.

## Table of Contents
- [Custom VM Reversing](#custom-vm-reversing)
- [Anti-Debugging Techniques](#anti-debugging-techniques)
- [Nanomites](#nanomites)
- [Self-Modifying Code](#self-modifying-code)
- [Mixed-Mode x86-64 and x86 Stagers](#mixed-mode-x86-64-and-x86-stagers)
- [LLVM Control-Flow Flattening](#llvm-control-flow-flattening)
- [SECCOMP and BPF Filter Analysis](#seccomp-and-bpf-filter-analysis)
- [Exception Handler Obfuscation](#exception-handler-obfuscation)
- [Memory Dump Analysis](#memory-dump-analysis)

## Custom VM Reversing

First recover the VM contract:
1. state layout
2. opcode dispatch
3. operand encoding
4. bytecode format

If the ISA is too annoying statically, fuzz single instructions and build the instruction set from observed state changes.

## Anti-Debugging Techniques

Common families:
- `ptrace`, `IsDebuggerPresent`, `TracerPid`
- timing checks
- TLS callbacks or pre-main gates
- self-hash or breakpoint scans

Fastest static bypasses are usually patching the conditional or short-circuiting the check with a one-instruction return.

## Nanomites

If the child is “running” but the parent is actually interpreting traps or debug events, log the parent-side state mutations instead of reading the child as normal code.

## Self-Modifying Code

Known-plaintext recovery against decrypted blocks often beats full decryption reversal. Function prologues, opcodes, or block format markers are enough to derive per-stage keys.

## Mixed-Mode x86-64 and x86 Stagers

Watch for `retf`/`retfq`, 32-bit blobs, inherited XMM state, and flag-sensitive emulator handoff bugs.

## LLVM Control-Flow Flattening

Trace the state variable. Once you have state transitions, the flattened CFG collapses back into ordinary logic surprisingly quickly.

## SECCOMP and BPF Filter Analysis

When the filter *is* the checker, dump it, translate it into solver constraints, and solve externally.

## Exception Handler Obfuscation

VEH/SEH/signal-based flows hide execution in the handler rather than in the faulting instruction. The correct breakpoint is usually inside the handler registration or handler body.

## Memory Dump Analysis

If the binary dumps its own memory, assume the dump is post-transform evidence. Known plaintext against function prologues or file signatures can recover the transform key cheaply.
