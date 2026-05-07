# Weird Machines and Non-Canonical Primitives

Use this reference for exploit patterns where the execution model itself is unusual: emulators, interpreters, ML dispatch, Game of Life state machines, bit-flip interfaces, constrained shellcode validators, or data structures that become code or control flow.

## Table of Contents
- [Interpreter and emulator pivots](#interpreter-and-emulator-pivots)
- [Data reinterpretation attacks](#data-reinterpretation-attacks)
- [Incremental and constrained-code execution](#incremental-and-constrained-code-execution)
- [Allocator and dispatch oddities](#allocator-and-dispatch-oddities)

## Interpreter and emulator pivots

### Forth Interpreter Command Execution

If a Forth environment exposes `system`, treat it as direct command execution rather than a memory-corruption problem.

Typical form:
- `s" cat /flag" system`
- `s" /bin/sh" system`

Also audit adjacent dangerous words such as:
- `included`
- `open-file`
- `read-file`

In practice this is command-capability discovery, not exploit development — but it belongs in pwn because challenge services often hide it behind unusual interpreters.

### Chip-8 Emulator Out-of-Bounds Memory for ret2libc

A Chip-8 style emulator with 4 KiB guest memory but a wider `I` register is a classic host/guest boundary bug.

Exploit pattern:
1. use `LD [I], Vx` / `LD Vx, [I]` with an out-of-range `I`,
2. read beyond `mem[4096]` into host stack or saved state,
3. leak a libc return address,
4. write the chosen RIP or one-gadget back through the same guest-memory primitive.

Key idea:
- any emulator that exposes a narrower memory model than its addressing registers invites bounds-check gaps,
- once calibrated, the emulator becomes an arbitrary-read/write tool against the host process.

### Neural Network Output as Function Pointer Index OOB

If a model output is used directly as an index into a function-pointer table, parameter editing becomes a dispatch exploit.

Exploit pattern:
1. reverse the network path to the output neuron,
2. choose a target out-of-bounds index that lands on useful adjacent memory,
3. edit weights or biases so inference returns that index consistently,
4. let the program reinterpret the resulting bytes as a function pointer.

This turns model parameters into control-flow inputs. Treat learned weights as attacker-controlled metadata if the model file is modifiable.

### Game of Life Shellcode Evolution via Still-Lifes

When a program evolves a cellular automaton and then executes the final board as bytes, the challenge becomes state preservation rather than raw shellcode injection.

Practical pattern:
- place useful instruction rows in the board,
- surround them with still-life stabilizers,
- bridge non-code rows with jumps,
- if needed, keep the first-stage shellcode tiny and use it only to read a larger second stage.

The exploit lever is not memory corruption but the ability to encode executable structure inside a stable automaton state.

## Data reinterpretation attacks

### Double-Precision Float Quicksort Canary Repositioning

If a program reinterprets stack-frame data as `double` values, sorts them, and then returns through the same frame, the sort becomes the write primitive.

Exploit idea:
1. choose doubles whose bit patterns equal the target canary and return address bytes,
2. arrange values so `qsort` moves those bit patterns into the canary and RIP slots,
3. preserve the canary while changing the control-flow target.

This works because the original canary already exists in the frame; the sort only needs another identical representation to move into place.

### Bloom Filter `abs(INT_MIN)` Negative Index OOB Write

The dangerous line is not the bloom filter itself but the composition:
- `idx = abs(hash) % size`

If `hash == INT_MIN`, then `abs(INT_MIN)` often stays negative on common libc/runtime behaviour, making `idx` negative and indexing backward into adjacent structures.

Use this when:
- the hash is attacker-influenced,
- the bit array sits next to function pointers or list metadata,
- a negative index resolves into a stable write-what-where.

Mitigation logic to remember while auditing:
- cast to unsigned before modulo,
- or use power-of-two masking on unsigned values.

### Single-Bit-Flip Exploitation Primitive

A single-bit flip is enough when the binary lets you repeat it.

Reliable escalation sequence:
1. create a loop or re-entry path by mutating a branch or stack-adjust instruction,
2. mutate an existing control-transfer instruction into something more useful (`jmp rsp`, branch bypass, etc.),
3. widen a read size or retarget `mprotect`,
4. inject or synthesize final shellcode once the environment is more favourable.

Think cumulatively:
- one bit flip rarely wins directly,
- a series of bit flips mutates the program into one that is easy to exploit.

## Incremental and constrained-code execution

### Shellcode Unique-Byte Limit Bypass via Counter Overflow

If the shellcode validator caps the number of distinct bytes, attack the validator state instead of the shellcode itself.

Typical pattern:
1. first run uses very few unique bytes,
2. that payload sprays or corrupts the stack-resident `seen[256]` accounting structure,
3. execution returns to a path that reuses the corrupted counter without clearing it,
4. second run accepts a normally forbidden shellcode alphabet.

This is a great example of turning a validator into the target rather than the obstacle.

### OOB Dispatch Table Read via Attacker-Controlled `rdx` Index

If a dispatcher does:
- load function pointer from `base + rdx*8 + C`
- call it

but only checks that the loaded slot is non-null, then any attacker-controlled `rdx` becomes a function-pointer read primitive.

Fast path:
1. choose an out-of-range index that lands on a useful qword in nearby memory,
2. aim for a stack pivot or short ROP-enabling gadget,
3. make the pivot land on attacker-controlled message data.

This is a pure logic exploit: no overwrite required, just an unchecked table index feeding an indirect call.

### 4-Byte Shellcode with Timing Side-Channel via Persistent Registers

Some services execute only a handful of attacker bytes but do so in a long loop, preserving callee-saved registers across iterations.

Exploit strategy:
- use repeated runs to accumulate state in preserved registers,
- perform one tiny action per iteration,
- amplify timing differences enough to distinguish state remotely,
- turn the tiny budget into an incremental loader or oracle.

If the environment reruns your 4-byte stub thousands of times, think state machine, not conventional shellcode.

## Allocator and dispatch oddities

### GF(2) Gaussian Elimination for Multi-Pass Tcache Poisoning

When repeated deterministic XOR operations corrupt heap metadata, treat the problem as linear algebra over GF(2).

Recipe:
1. measure the XOR vector produced by each controllable seed or pass,
2. compute the target delta between current `fd` and desired `fd`,
3. solve for the subset of vectors whose XOR equals that delta,
4. apply those passes in any order.

This is the right model whenever:
- corruption is XOR-based,
- operations are repeatable,
- and the target pointer is safe-linking-mangled rather than raw.

### UAF via Menu-Driven `strdup`/`free` Ordering

If the "exit" path frees menu-owned `strdup()` buffers but lets the user cancel the exit, the program may resume with dangling pointers.

Exploit pattern:
1. allocate a validated field and an unvalidated field,
2. enter the exit path so both get freed,
3. cancel the exit and refill the freed chunks through the unvalidated field,
4. make the validated field's pointer now reference attacker-controlled bytes,
5. trigger a later `system()` or formatting path that trusts that field.

This is a heap-UAF version of cross-field validation bypass.

### `mmap`/`munmap` Size Mismatch UAF for Thread Stack Overlap

If allocation size is derived from one quantity (for example image dimensions) but `munmap()` uses a larger quantity (for example compressed file length), the deallocator can unmap neighbouring mappings.

Exploit chain:
1. place the mapping near a still-referenced global buffer,
2. over-unmap so both the original mapping and a neighbour disappear,
3. spawn a thread so its stack fills the freed gap,
4. write through the stale buffer pointer into the new thread stack.

This is a race-free mapping overlap trick, not a classic heap unlink.

### Premature Global Index Update for Out-of-Bounds Stack Write

If a function stores a user index into global state before checking whether it is in range, later operations may consume the invalid index even though the original request was rejected.

This gets especially dangerous when:
- the same array also stores stack or frame pointers,
- the later edit path trusts the cached index,
- the result is a direct stack write primitive without further corruption.

Think of it as a TOCTOU bug compressed into one function: the state update happens too early, the rejection happens too late.

### `strcspn` as Indirect Null Byte Injection

A common C pattern is:
1. build a filename or path with `snprintf`,
2. compute `strcspn(buf, "\r\n")`,
3. write `\0` at that offset.

If the attacker can inject a newline but not a raw null byte, this becomes a filename truncation primitive.

Use it for:
- removing forced suffixes such as `.cfg`,
- trimming wrappers around traversal strings,
- bypassing input layers that filter nulls but not newlines.

## See also

- `advanced-primitives.md` — general advanced pivots, runtime tricks, and pointer-guard notes
- `overflow.md` — conventional stack/global/OOB overflow families
- `sandbox.md` — restricted-environment escapes, `/proc` tricks, and command-execution notes
- `windows-pwn.md` — Windows-specific binary exploitation patterns
- `exotic-arch.md` — architecture-specific ARM, ARM64, MIPS, and RISC-V notes
