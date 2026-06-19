# CTF Reverse - Reversing Patterns

Recurring, reusable reversing patterns and the shortest path to a validation signal for each. Recognition markers first; pick the cheapest oracle or inversion over full reverse engineering. For tool syntax see [tools.md](tools.md); for detection/evasion see [anti-analysis.md](anti-analysis.md).

## Table of Contents
- [Custom VMs](#custom-vms)
- [Obfuscation and Memory](#obfuscation-and-memory)
- [Byte Transforms and Keystreams](#byte-transforms-and-keystreams)
- [Constraint and Crypto Recovery](#constraint-and-crypto-recovery)
- [Runtime Oracles and Side-Channels](#runtime-oracles-and-side-channels)
- [Hidden Control Flow](#hidden-control-flow)

## Custom VMs

Recover the VM contract first: state layout (registers/memory/IP), opcode dispatch, operand encoding, bytecode format (often loaded from a command-line file). If the ISA is hostile statically, fuzz single instructions and build the instruction set from observed state changes.

- **Trace-diff over reimplementation** — log `(opcode, stack/regs)` at the dispatch point; the trace usually exposes the real algorithm faster than a full VM rewrite.
- **Lift to LLVM IR** — emit IR per opcode, then `opt -O3` (inlining, constant folding, DCE) collapses thousands of handler lines into the underlying algorithm.
- **Sequential key-chain brute-force** — when a VM validates input in small independent blocks (e.g. 3 bytes = 2^24) and each block's output keys the next, brute-force blocks in order; compile the solver with `gcc -O3 -march=native -fopenmp`.
- **Brute force is sometimes the design** — for intentionally one-way per-block transforms, byte/block brute force beats inversion.

## Obfuscation and Memory

- **Nanomites** — the parent interprets traps/debug events while the "child" runs; log parent-side state mutations instead of reading the child as normal code.
- **Self-modifying code** — known-plaintext against decrypted blocks (function prologues, opcodes, file-format markers) recovers per-stage keys without reversing the decryptor.
- **Mixed-mode x86-64/x86 stagers** — watch for `retf`/`retfq`, 32-bit blobs, inherited XMM state, and flag-sensitive emulator handoff bugs.
- **LLVM control-flow flattening** — trace the state variable; transitions collapse the flattened CFG.
- **SECCOMP/BPF as the checker** — dump the filter, translate to solver constraints, solve externally.
- **Memory dumps** — a binary that dumps its own memory leaves post-transform evidence; known plaintext against prologues/signatures recovers the transform key cheaply.

## Byte Transforms and Keystreams

- **Known-plaintext XOR** — with a known format prefix, test repeating-key and index-augmented XOR before assuming custom crypto. A 0–255 single-byte XOR sweep is cheap — run it before inventing an unpacker theory.
- **Keystream families** — recognize before reimplementing: xorshift32 (shifts 13,17,5), xorshift64 (12,25,27), magic constants `0x2545F4914F6CDD1D`, `0x9E3779B97F4A7C15`, Fisher-Yates layout, obvious multipliers/rotation schedules.
- **Uniform transforms** — if one input byte changes only one output byte, build the 256-value map once and invert it; not a symbolic-execution problem.
- **Position-based transforms** — when `i`, parity, or alternating rules appear, derive the inverse position-wise.
- **Mangle functions** — extract the target bytes from `.rodata`, write the inverse, walk the transform backward rather than simulating the validator.
- **Hex-encoded comparison** — input converted to hex before compare; decode the target constant (`xxd -r -p`). The nicest kind of fake complexity.
- **x86-64 gotchas** — sign-extension/32-bit-truncation pitfalls and loop-state updates on the wrong side of a branch. Re-check raw assembly when the decompiler looks too elegant.

## Constraint and Crypto Recovery

- **Hook the crypto API, not the math** — when keys are derived/hash-resolved at runtime, `LD_PRELOAD` a wrapper over `EVP_DecryptInit_ex`/`EVP_CipherInit_ex` (or hook via Frida) to capture the key directly.
- **Prefix-hash byte recovery** — if the binary hashes each prefix independently, recover one character at a time by matching per-position hashes (use the binary itself as the oracle).
- **Constrained printable linear systems = lattice** — `Ax=b` with printable-ASCII solutions is a CVP/LLL problem (SageMath); for mod-2^32 systems solve the linear system directly.
- **GF(2^8) / Gaussian elimination** — the `0x1b` reduction constant signals AES-field arithmetic (addition = XOR); matrix + augmentation vector usually sit in `.rodata`.
- **Multi-modulus CRT keygen** — `key mod n_i == r_i` constraints kill the key search instantly; the rest is deterministic table walking.
- **Auto-generated decision trees** — hundreds of `fN()` comparison functions: script extraction (Ghidra headless, collect `CMP` immediates) instead of reading each node.
- **ROPfuscation** — dump the gadget/return stream, compress the repetition, solve the real math; it's still an algorithm.
- **Staged decryptors** — stage 1 is often cheap crypto (RC4/XOR gate); the real validator lives in stage 2. Fork-per-candidate with COW isolation parallelizes self-decrypting-layer oracles.
- **Meet-in-the-middle** — splitting a hash/keyspace turns an infeasible brute force into a scriptable one.

## Runtime Oracles and Side-Channels

- **Timing** — validation time varies per correct character; measure elapsed time per candidate to recover the flag byte-by-byte.
- **Instruction count** — Pin/Unicorn counting; when the transform depends on how many instructions ran (a counter register feeding XOR/ROL/mul), byte-by-byte emulation beats algebra.
- **INT3 + coredump oracle** — patch a byte to `0xCC` after the transform, enable core dumps, brute-force each character and read the computed state from the coredump via `strings`.
- **Comparison/output breakpoints** — break on `strcmp`/`memcmp`/`putchar` to leak the target; see [tools.md](tools.md#oracle-and-side-channel-breakpoints).
- **Coverage/opcode-only traces** — even data-free traces leak branch structure (sorting comparisons reveal ordering); dedup, split into blocks, infer the algorithm.
- **Output-channel side effects** — treat keyboard LEDs (`KDSETLED` ioctl), signal counts, or rendered images as the real output, not a gimmick.
- **Batch automation** — when many binaries share one template (mass crackmes), script `objdump` to extract `CMP`/`add`/`sub` immediates and solve algebraically instead of solving each by hand.

## Hidden Control Flow

The real checker is rarely in an obvious `main`:

- **Global destructors** — if `main()` looks empty, check `__cxa_atexit`/global destructors.
- **Pre-main gates** — TLS callbacks (Windows) or constructor functions run before the entry point.
- **Signal handlers** — real logic in SIGSEGV/SIGILL/SIGFPE handlers; see [anti-analysis.md](anti-analysis.md#signal-and-handler-runtime-tricks).
- **printf `%hhn` VM** — a sequence of `%Nc%hhn` writes implements a byte-write bytecode VM; map writes to symbolic variables and solve the resulting equation system with Z3. Count unique format patterns to size the instruction set.
- **Fork + pipe + dead branch** — parent writes data and exits, child continues; real validation hides in an always-false branch. `strace` reveals the topology; patch the comparison constant to reach it.
- **Backdoored shared library** — works under GDB but fails when run normally? Check `ldd` for non-standard libc paths and `diff` the suspicious vs. system library strings.
- **ELF section-header corruption** — corrupted section headers crash tools while program headers still run the binary; zero `e_shoff` or use `readelf -l`. Real data often follows a magic marker + XOR.
- **MFC/event-driven UI** — event routing *is* the control-flow graph; break on `SendMessageW`/`DispatchMessage` and filter by message id.
- **Format-specific parsers** — proprietary image/compression formats are usually quadtrees, LZ77 variants, or Huffman streams: a short command byte followed by more commands or fixed-width leaf data. Prototype the parser by printing recursion depth/offset per call.
