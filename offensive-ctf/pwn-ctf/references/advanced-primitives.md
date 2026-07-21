# Advanced Primitives and Edge Cases

Use this reference when the standard `overflow.md`, `rop.md`, `heap.md`, `heap-fsop.md`, `sandbox.md`, `kernel.md`, or `exotic-arch.md` references are not enough. It collects advanced pwn patterns that show up in VMs, JITs, seccomp-heavy binaries, unusual runtimes, data-reinterpretation bugs, and odd but repeatable exploit pivots.

## Table of Contents
- [Seccomp and syscall edge cases](#seccomp-and-syscall-edge-cases)
- [Runtime and dynamic-linker pivots](#runtime-and-dynamic-linker-pivots)
- [VM, JIT, and interpreter exploitation](#vm-jit-and-interpreter-exploitation)
- [Unusual memory-corruption and logic pivots](#unusual-memory-corruption-and-logic-pivots)
- [Hash, numeric, and data-reinterpretation tricks](#hash-numeric-and-data-reinterpretation-tricks)
- [Exotic runtime notes not yet split out](#exotic-runtime-notes-not-yet-split-out)

## Seccomp and syscall edge cases

Load `rop.md` for mainstream ORW/ret2libc/ret2csu chains first. Use this section for filters that are incomplete, stateful, or weirdly implemented.

### openat2 Bypass (New Age Pattern)

`openat2` (syscall 437 on Linux 5.6+) is often missing from seccomp policies that only block `open` and `openat`.

- `struct open_how { u64 flags; u64 mode; u64 resolve; }`
- Call shape: `openat2(AT_FDCWD, filename, &open_how, sizeof(open_how))`
- If a filter blocks classic ORW but forgets `openat2`, use it as the file-open primitive and keep the rest of the chain conventional.

### Conditional Buffer Address Restrictions

Some filters allow `read` or `write` only when the buffer address falls inside a range.

Typical pattern:
- `read()` dies if `buf <= code_region + X`
- `write()` dies if `buf >= code_region + Y`

Bypass pattern:
1. Read into a high, read-allowed region.
2. Copy with `rep movsb` into a low, write-allowed region.
3. Write from the copied buffer.

```nasm
lea rsi, [r14 + 0xc01]   ; read-allowed region
xor rax, rax             ; __NR_read
syscall
mov r13, rax             ; byte count
lea rsi, [r14 + 0xc01]
lea rdi, [r14 + 0x200]   ; write-allowed region
mov rcx, r13
rep movsb
mov rdi, 1
lea rsi, [r14 + 0x200]
mov rdx, r13
mov rax, 1               ; __NR_write
syscall
```

### Shellcode Construction Without Relocations (pwntools)

When `pwntools.asm()` chokes on forward references, use a manual `jmp`/`call`/`pop` layout so the shellcode discovers its own data at runtime.

```python
body = asm('''
    pop rbx
    mov r14, rbx
    and r14, -4096
    mov rsi, rbx
fail:
    mov rdi, 1
    mov rax, 60
    syscall
''')
call_offset = -(len(body) + 5)
call_instr = b'\xe8' + p32(call_offset & 0xffffffff)
jmp_instr = b'\xeb' + bytes([len(body)]) if len(body) < 128 else b'\xe9' + p32(len(body))
shellcode = jmp_instr + body + call_instr + b"filename.txt\x00"
```

Use this when the filter or loader forces shellcode into a single blob with embedded strings and no relocations.

### Seccomp Analysis from Disassembly

If the binary builds seccomp rules inline, decode the calling convention instead of guessing:

```c
seccomp_rule_add(ctx, action, syscall_nr, arg_count, ...)
```

Useful `scmp_arg_cmp` layout:
- `arg` at `+0x00`
- `op` at `+0x04`
- `datum_a` at `+0x08`
- `datum_b` at `+0x10`

Useful operator values:
- `NE=1`
- `LT=2`
- `LE=3`
- `EQ=4`
- `GE=5`
- `GT=6`
- `MASKED_EQ=7`

`0x7fff0000` is `SCMP_ACT_ALLOW`.

### Seccomp BPF X-Register Addressing Mode Bypass

Some filters compare `A == X` (JEQ X, opcode `0x1d`) instead of `A == constant`. Older tooling can miss that and show an incomplete policy.

Detection:
- Dump raw BPF, not only disassembler output.
- Look for opcode `0x1d`.
- Treat `???` in seccomp-tool output as a smell, not a conclusion.

Exploit idea:
- If the filter effectively permits `syscall_nr == rdx`, set both `rax` and `rdx` to the same syscall number before the `syscall` instruction.

```python
rop = flat(
    pop_rdx_rbx, 59, 0,
    pop_rax, 59,
    pop_rdi, binsh_addr,
    pop_rsi, 0,
    syscall_ret,
)
```

### Integer Truncation Bypass int32 to int16

Pattern:
- Input validated as non-negative `int32`
- Later cast to `int16_t` for bounds logic
- `65534` becomes `-2`, `65535` becomes `-1`

This turns a "positive" input into a negative array index or ring offset.

Practical follow-up: ORW chains in containerized or proxied environments should not hardcode `fd=3`. `open()` often returns 4 or 5.

Use `xchg rdi, rax` after `open()` so `read()` receives the actual returned file descriptor.

```python
rop.raw(pop_rdi)
rop.raw(flag_str_addr)
rop.raw(pop_rsi)
rop.raw(0)
rop.raw(libc.sym.open)
rop.raw(libc_base + 0x181fe1)  # xchg rdi, rax; cld; ret
rop.raw(pop_rsi)
rop.raw(buf_addr)
rop.raw(pop_rdx_xor_eax)
rop.raw(0x100)
rop.raw(libc.sym.read)
```

### FSOP + Seccomp Bypass via openat/mmap/write

When classic `open`/`read`/`execve` paths are filtered, combine an FSOP pivot with less-filtered syscalls:

1. Leak libc.
2. Build fake `FILE` / `_wide_data` / wide vtable.
3. Pivot via `mov rsp, rdx` or equivalent wide-path dispatch.
4. Use `openat`, `mmap`, `write`, `pread64`, `readv`, or `writev` instead of the blocked syscalls.

Useful substitutions:
- `open` → `openat` or `openat2`
- `read` → `mmap`, `pread64`, `readv`
- `write` → `writev`, `sendfile`

Use `heap-fsop.md` or `heap.md` for the full fake-`FILE` construction details; this section is the syscall-selection layer.

## Runtime and dynamic-linker pivots

### ret2dlresolve

Use when:
- you control a call into the PLT,
- you have writable memory,
- the target uses Partial RELRO,
- and you do not have a libc leak.

```python
rop = ROP(elf)
dlresolve = Ret2dlresolvePayload(elf, symbol="system", args=["/bin/sh"])
rop.read(0, dlresolve.data_addr)
rop.ret2dlresolve(dlresolve)
```

Key points:
- Forge `Elf64_Rela`, `Elf64_Sym`, and the string table entry for `system`.
- The dynamic linker resolves your forged symbol lazily on the next PLT call.
- This is a lazy-binding abuse, not a leak-driven libc attack.

Canonical details belong in `rop.md`; keep this as the reminder that ret2dlresolve is still the right answer when leaks are missing.

### Leakless Libc via Multi-fgets stdout FILE Overwrite

When you have ROP but no leak primitive, build a fake `stdout` on BSS via repeated `fgets(addr, 7, stdin)` calls.

Why 7 bytes?
- `fgets` appends a null byte.
- Canonical libc pointers already end with null high bytes.
- Writing 7 bytes lets the forced null land on a byte that was already safe to zero.

Pattern:
1. Write `_flags`.
2. Write `_IO_write_base` to a GOT entry.
3. Write `_IO_write_end` to GOT+8.
4. Flush the fake `stdout`.
5. Parse the 8-byte leak and derive libc base.

Use this when there is no format string, no unsorted-bin leak, and no obvious out-of-bounds read.

### RtlCaptureContext Deterministic Windows Stack Leak

If you need a stack leak on Windows and can call NT APIs, `RtlCaptureContext(&ctx)` writes a `CONTEXT` struct including `Rsp` into attacker-controlled memory.

```c
CONTEXT ctx;
RtlCaptureContext(&ctx);
printf("rsp = %p\n", (void*)ctx.Rsp);
```

This is a deterministic userland info leak disguised as an unwind helper.

### PIE Bypass via Consistent glibc Load Base 0x56555000

On some 32-bit environments, PIE is technically enabled but the loader places the executable at a stable base such as `0x56555000` across runs.

Exploit rule:
- check mappings first,
- do not assume a leak is required if the runtime keeps reusing the same base.

```python
PIE_BASE = 0x56555000
print_flag = PIE_BASE + 0x6dc
payload = cyclic(30) + p32(print_flag)
```

Use only after confirming the mapping empirically on the target runtime.

### Custom Printf Format Specifier Arginfo Overwrite

glibc's `register_printf_specifier()` stores a handler and an `arginfo` callback in heap data. If you can overwrite the `arginfo` function pointer with `system`, then `printf_info.precision` becomes attacker-controlled bytes passed as the first argument.

Trick:
- encode `"sh\0"` as the little-endian integer `26739`
- trigger `%.26739s`
- `arginfo(system)` receives a pointer whose first field contains `"sh\0"`

This is not a normal format-string write-up; it is a heap-pointer hijack on printf extension metadata.

### Format String with Encoding Constraints + RWX .fini_array Hijack

Pattern:
- input is encoded (for example Base85),
- decoded into a fixed RWX region,
- then handed to `printf()`.

Shortest path:
1. Write shellcode into the RWX mapping.
2. Use `%hn` writes to patch `.fini_array[0]` to that mapping.
3. Let normal process exit trigger the shellcode.

Key insight:
- stop thinking in libc offsets when the program already gave you fixed RWX memory.
- the real problem is argument numbering after decoding.

Use an argument-number convergence loop if the decoder changes payload length.

### ELF Code Signing Bypass via Program Header Manipulation

If a signing scheme hashes sections but not program headers, the verifier and the loader disagree about what code is authoritative.

Exploit pattern:
1. append payload data at a page-aligned offset,
2. retarget the executable `PT_LOAD` segment's `p_offset` and size fields toward that appended blob,
3. keep the section table and signed section content unchanged,
4. pass verification and execute attacker-controlled bytes.

This is a loader/verifier model mismatch, not a memory-corruption bug. Reach for it when the artifact is a signed ELF and the integrity story only talks about sections.

### Pointer-Guarded Exit-Handler Hijacks

Modern glibc protects several exit-time callback paths with the same pointer-guard family, including TLS destructors and `atexit` handlers.

Reusable recipe:
1. gain arbitrary read or a narrow-but-reliable heap overflow,
2. recover a pointer guard or a mangled-pointer/plaintext pair,
3. forge a valid mangled callback,
4. let normal exit machinery transfer control.

#### Signed/Unsigned Char Underflow to Heap Overflow

If a size field is stored as `signed char` but later consumed as `unsigned char`, a value such as `-112` becomes `144`, turning a bounded message buffer into a short but precise heap overflow.

What makes this pattern strong is the follow-on chain:
- deterministic XOR-keystream brute force can produce byte-precise writes,
- the first safe-linked tcache `fd` often reveals the heap page via `fd << 12`,
- forged `>= 0x420` sizes promote chunks into the unsorted bin for libc leaks,
- stdout-oriented FSOP can leak TLS and, with it, the pointer guard.

#### TLS Destructor Hijack via `__call_tls_dtors`

The destructor list stores pointer-guarded function pointers plus an object argument per node. Once the guard is known, forge nodes that call `setuid(0)`, `system("/bin/sh")`, or another final-stage target.

Encoding rule:
- `encoded = rol(target ^ pointer_guard, 0x11)`

Use this when hook-era glibc shortcuts are gone and exit-time dispatch is the cleanest remaining control-transfer path.

#### atexit PTR_MANGLE Secret Recovery via Arbitrary Read

If you can read a known mangled callback such as the initial `_dl_fini` registration, derive the secret and forge new `atexit` entries.

Useful formulas:
- `original = ror17(mangled) ^ secret`
- `forged = rol17(target ^ secret)`

## VM, JIT, and interpreter exploitation

### VM Signed Comparison Bug

A custom VM that checks `offset <= 0xfff` with a signed comparison but no lower-bound check lets negative offsets reach function-pointer tables or control metadata.

Typical exploit flow:
1. build constants with the VM's arithmetic,
2. derive a negative offset,
3. overwrite a handler or dispatch table entry,
4. trigger the modified opcode.

Always inspect VM bounds checks for `jle`/`jl` where the intended logic was unsigned.

### Bytecode Validator Bypass via Self-Modification

Pattern:
- validator checks the initial byte stream,
- runtime execution mutates the checked bytes into a forbidden instruction.

Classic example:
- `push fs` encodes as `0f a0`
- `syscall` encodes as `0f 05`
- preceding stack writes mutate the `a0` byte into `05`

Use this when the VM/sandbox only validates static byte sequences and then executes from mutable stack or JIT memory.

### BF JIT Unbalanced Bracket to RWX Shellcode

A Brainfuck-style JIT that uses the stack for bracket matching can turn an unmatched `]` into a jump through a stack value that points at RWX tape memory.

Exploit plan:
1. encode stage-1 shellcode onto the tape with `+` / `-`,
2. trigger unmatched `]`,
3. land on tape,
4. use stage 1 to `read()` a full stage-2 payload.

This is the JIT equivalent of turning a control-structure parser bug into a code pointer.

### JIT Compilation Exploits

Pattern:
- an encoding bug causes instruction misalignment,
- attacker-controlled immediates become executable bytes.

Reliable technique:
- split shellcode into 2-byte fragments,
- interleave them with `jmp $+3` (`eb 03`),
- pack the resulting 4-byte cells into attacker-controlled immediates.

This is the general recipe behind many "miscompiled JIT immediate becomes code" problems.

### JIT Sandbox Escape via Conditional Jump uint16 Truncation

If a JIT stores a 32-bit branch displacement but computes it as a `uint16_t`, code larger than 64 KiB can make the jump land inside a future immediate.

Exploit pattern:
1. emit a huge always-false branch,
2. make the truncated jump land inside immediate data,
3. fill those immediates with threaded 2-byte shellcode fragments,
4. stage into RWX memory and jump.

Use when the sandbox claims "structured" control flow but emits raw native code.

### Type Confusion in Interpreter

Pattern:
- the engine rewrites or trusts a type tag,
- fields from one variant are reinterpreted as pointers or sizes from another.

Red flags:
- unions or tagged structs with unused padding,
- normalisation passes that force a node type,
- pretty-printers that dump unknown variants as raw bytes.

Treat unused bytes as future pointers; in interpreters they often become the fastest route to disclosure or arbitrary dispatch.

### VM GC-Triggered UAF — Slab Reuse

A VM with slices/views can create two logical objects over one slab. If one view is freed and GC runs while the parent still holds the slab pointer, later allocations can reclaim that slab.

Reliable abuse pattern:
1. allocate a buffer in a size class shared with function objects,
2. create an aliasing slice,
3. drop the slice and force GC,
4. allocate a callable object into the reclaimed slab,
5. use the parent object as a UAF read/write against the new function object.

This is the "logical ownership bug becomes slab overlap" pattern.

### GC Null-Reference Cascading Corruption

A mark-compact GC that follows null references into a zeroed heap region can fabricate a fake object header. During compaction, the resulting `memmove` cascade corrupts real headers downstream.

Useful consequences:
- oversized logical lengths,
- out-of-bounds object access,
- fake-object preservation for one chosen allocation,
- libc leak followed by FSOP.

The important lesson is not the exact object graph; it is that GC metadata bugs amplify far better than raw heap overflows because every compaction step compounds the corruption.

### io_uring UAF with SQE Injection

When reclaimable userland objects back `io_uring` submission memory, a plain UAF can become a kernel-operation injection primitive.

Reliable sequence:
1. trigger a cleanup path that frees an object but leaves a dangling reference,
2. refill the same slab/bin with a different object type,
3. overwrite reclaimed memory with a forged `io_uring_sqe`,
4. wait for the worker thread to submit it unchanged.

The first clean win is often `IORING_OP_OPENAT`, because it converts a logic bug into file-open capability even when the main thread is syscall-constrained.

### CPU Emulator Print Opcode Python eval Injection

If an emulator's print opcode does `eval('"' + buffer + '"')` to process escape sequences, building `"+__import__("os").system("cmd")#` inside emulated memory turns output into host-side Python code execution.

This is not a guest escape via CPU semantics; it is a host-language injection bug hidden in a debug or output helper.

## Unusual memory-corruption and logic pivots

### Use-After-Free (UAF) Exploitation

Classic same-size reuse still matters.

Reliable pattern:
1. free an object with a callback or vtable pointer,
2. leave the pointer dangling,
3. allocate a different object of the same size,
4. overlap the reclaimed chunk,
5. overwrite the callback target,
6. trigger the stale object.

If two objects land in the same tcache bin, this remains one of the shortest paths from menu bug to win function.

### Off-by-One Index to Size Corruption

If `entries[0]` aliases `entries[-1]` or a nearby metadata slot, corrupt the logical length first, then use the larger length to leak canaries, saved RBP, or libc return addresses.

Treat index bugs as metadata bugs before treating them as raw OOB reads.

### Stack Variable Overlap / Carry Corruption OOB

Compilers sometimes pack a byte and a word so arithmetic on one carries into the other.

Example pattern:
- `offset` at `[rsp+0x48]` as a word
- `index` at `[rsp+0x49]` as a byte
- incrementing the word by `255` flips the high byte and changes the byte-sized variable

When two variables share stack storage, a numeric overflow becomes a logical-state bug, not just a math bug.

### ASAN Shadow Memory Exploitation

ASAN binaries are not automatically non-exploitable.

Useful rules:
- learn shadow-byte meanings (`0x00`, `0x01-0x07`, `0xF1`, `0xF3`, `0xF5`)
- distinguish real stack from fake stack before committing the exploit path
- use the format-string leak to classify the stack, then compute the OOB write distance

If fake-stack use is probabilistic, combine leak, classification, and overwrite in one interaction and reconnect until the real stack appears.

### Arbitrary Read/Write to Shell via GOT Overwrite

If the program already gives arbitrary read and arbitrary write, stop looking for cleverer bugs.

Fast path:
1. read a GOT entry,
2. derive libc base,
3. overwrite a string-taking function such as `strtoll`, `atoi`, `puts`, or `printf` with `system`,
4. send the command string.

The main question is not "can I exploit this?" but "which imported function is called later with attacker-controlled first argument?"

### Stack Leak via __environ and memcpy Overflow

With a read primitive but no direct write primitive:
1. leak libc,
2. read `__environ` to get a stack pointer,
3. place the future ROP chain inside an input buffer already on the stack,
4. abuse a `memcpy`-style overflow to copy that planted data over the saved return address,
5. trigger normal function return.

This is the standard pattern for turning a read primitive plus oversized copy into a write-to-return-address.

### Game AI Arithmetic Mean OOB Read

If a game or simulation computes a secondary move as the arithmetic mean of attacker input and previous state before validating bounds, the averaging step itself becomes the out-of-bounds primitive.

Use it when:
- validation happens after the computed move is used,
- you can submit roughly double the desired offset and let the mean divide it back down,
- the target leaks through rendering, AI logging, or score output.

This is a TOCTOU-flavoured logic bug disguised as harmless game math.

### Tree Data Structure Stack Underallocation

If the program sizes temporary stack storage under the assumption of a balanced tree, craft an imbalanced tree so traversal depth exceeds the allocation and clobbers the saved return path.

Look for recursive or stack-backed traversals that use `2^depth` heuristics or fixed node-count approximations.

### Heap Overlap via Base Conversion

When the same numeric value is re-rendered across bases, string length can grow dramatically.

Pattern:
1. store in a compact base,
2. convert to a verbose base,
3. longer representation overflows adjacent heap metadata,
4. use the overlap for the real target.

This is especially attractive when the program only accepts digits/letters and classic byte-wise writes are unavailable.

### Signed Integer Bypass (Negative Quantity)

If `scanf("%d")` feeds business logic that expects non-negative counts, negative quantities can make `quantity * price` negative and satisfy `balance >= total_cost`.

Use this when the bug gives access, balance, or inventory rather than memory corruption. In pwn-style challenge services it often becomes the shortest route to gated functionality or a hidden action.

### Custom Canary Preservation

If the canary is static, known, or separately leaked, preserve it literally inside the overflow.

Example pattern:
- buffer
- known canary bytes
- target field or return address after the canary

The exploit is not about bypassing the canary check; it is about writing through it without changing it.

### Double win() Call Pattern

Some helper functions gate success with `if (attempts++ > 0)` or equivalent post-increment logic.

Exploit rule:
- if the first call only arms the state, chain the same target twice in the return path.

### Path Traversal Sanitizer Bypass

If the sanitizer drops a bad character and then skips the next character, doubled separators survive:

- `../../etc/passwd` → `....//....//etc//passwd`

Related trick:
- if the flag file is already open but not closed, read it via `/proc/self/fd/N`.

### Signed Int Overflow to Negative OOB Heap Write + XSS-to-Binary Bridge

When a backend computes `y * width + x` in signed 32-bit arithmetic, large coordinates can wrap negative, satisfy a signed bounds check, and write backward into heap metadata or neighbouring object pointers.

The high-value version is layered:
1. a web-facing surface gives stored XSS or another privileged browser action,
2. the privileged browser or bot can reach a local-only native-management API,
3. the native process exposes a pixel, grid, or canvas write that naturally maps to a 24-bit or byte-group heap write,
4. the heap corruption retargets an in-memory data pointer,
5. `environ` or a similar libc symbol yields a stack leak,
6. the final write lands a ROP chain on the saved return path.

The lesson is broader than the exact stack: signed coordinate overflow plus API bridging can turn a modest client bug into full binary exploitation.

### Custom Shadow Stack Bypass via Pointer Overflow

Userland shadow stacks fail open if the shadow-stack pointer itself is never bounds-checked.

Exploit pattern:
1. recurse or iterate until the shadow index advances beyond the shadow array,
2. land the index on attacker-controlled `.bss` or heap memory,
3. write the same target return address there,
4. overwrite the hardware return address to match.

Both checks pass because both stacks now agree.

### DNS Compression Pointer Stack Overflow with Multi-Question ROP

Custom DNS parsers often understand compression pointers but forget to track total decompressed output length.

Exploit pattern:
1. build chained `0xC0xx` compression pointers that revisit packet data,
2. expand a small packet into a large logical domain name,
3. overflow the name buffer on the stack,
4. if per-question size is tight, spread the final ROP material across multiple question entries.

This is the decompression-amplification version of a stack overflow.

### Sign Extension Integer Underflow in Metadata Parsing

Manual `to_int32()` helpers that convert values `>= 0x80000000` into negative signed integers are a recurring parser hotspot.

If the converted value is later used as an offset or index, you often get a byte-at-a-time leak by walking the malicious value upward and observing output or parser diagnostics.

Treat custom sign-extension helpers as an audit smell, especially in media, archive, and metadata parsers.

### ROP Chain Construction with Read-Only Primitive

If the program only lets you read arbitrary memory, the missing write primitive changes the problem rather than ending the exploit.

General recipe:
1. leak libc and stack with the read primitive,
2. identify stack locations that will later receive copied input,
3. search libc or mapped data for byte sequences matching needed gadget bytes or constants,
4. import those bytes onto the stack indirectly by reading from the right source addresses,
5. assemble ORW or another minimal endgame from what you can import.

This is the right mindset whenever the read primitive is stronger than it first appears.

### 4-Byte Shellcode with Timing Side-Channel via Persistent Registers

When the shellcode window is tiny but the process reruns it in a large loop, persistent callee-saved registers become a staged state machine.

Use the repeated execution to:
- accumulate state in preserved registers,
- perform one byte or one tiny action per round,
- amplify timing differences enough to distinguish success and failure remotely.

This turns a laughably small shellcode budget into an iterative loader or oracle.

### Timing Attack for Character-by-Character Flag Recovery

If validation sleeps or otherwise delays per-correct-character, measure response time, average multiple samples, and grow the prefix one byte at a time.

Use when output is blocked but correctness affects runtime.

### 9-Byte test+je Timing Leak

If you only control a tiny shellcode slot, build a one-bit oracle instead of a full read primitive.

`test BYTE PTR [rip+0x2], imm8` followed by `je 0` can distinguish bit-equal vs bit-different by hang time versus crash time. Repeat per bit or per byte.

### Game Genie-Style 6-Char Code for Arbitrary Binary Patching

When a patching interface permutes bits from a tiny alphabet into `(offset, value)`, reverse the bit layout once and treat it as an arbitrary binary patch primitive.

The main job is to derive the encoder, not to exploit the game logic itself.

### Go Slice Capacity Aliasing via Struct-by-Value Copy

Copying a Go struct by value does not deep-copy slice backing arrays.

Exploit rule:
- make `cap > len` before the copy,
- let another subsystem append through the copied header,
- observe the in-place mutation through the original alias.

This is a clean logic/data-only exploit with no memory corruption in the C sense.

## Hash, numeric, and data-reinterpretation tricks

### MD5 Preimage Gadget Construction

If the program hashes attacker input and executes or interprets the digest, search for preimages whose digest begins with a jump prefix such as `eb 0c`, then treat bytes 14-15 or another reachable suffix as tiny gadget slots.

This turns a hash oracle into a code-synthesis oracle.

### IEEE 754 Double-as-Shellcode via Exponent Fixing

A double is an exact integer container when the exponent is fixed at `bias + mantissa_bits`.

Exploit pattern:
- force all doubles to exponent `0x4330` on 64-bit doubles,
- use their mantissas as lossless 52-bit payload chunks,
- pick the last value so the arithmetic average or sum reconstructs the target bytes exactly.

Use when the challenge only allows float input but later reinterprets arithmetic results as code or control data.

### CRC Oracle as Arbitrary Read Primitive

If a service computes CRC over memory reachable through a corrupted pointer, precompute the CRC of all 256 single-byte inputs and reverse the mapping.

Then:
1. point the CRC routine at the target byte,
2. observe the CRC result,
3. map it back to the original byte,
4. repeat for GOT, libc, stack, and canary data.

This is a classic example of a seemingly harmless checksum API becoming a byte oracle.

### Allocator-Residue Order Oracle (blind ASLR, no read primitive)

When the program never prints controllable memory (dispatcher emits only fixed strings), defeat ASLR with a
side channel over program state instead of a disclosure:

1. Get a hidden pointer into a **comparable** field. Leave a struct field as malloc **residue** the program
   then treats as a sort key / priority / index: a freed chunk's safe-linked `fd` (`= heap>>12`) or an
   unsorted-bin `bk` (`= a libc pointer`) that an uninitialized-read path adopts.
2. Insert known **cut** values around a guessed boundary, then trigger the ordering op (a sort, a min-heap
   pop sequence, a priority dequeue). **Count observable events** — pops before a sentinel surfaces, loop
   iterations, or which error fires — = the **rank** of the hidden value vs the cut = one bit.
3. Binary-search the ASLR page bit by bit; repeat per base (heap, then libc).

Any observable **order/count/branch** that depends on a hidden address is a leak. Fully blind and remote-safe
(no `/proc`, no disclosure). Reach for it whenever the target compares attacker-adjacent memory but never
prints it.

## Exotic runtime notes not yet split out

Load `exotic-arch.md` first for mainstream non-x86-64 architecture guidance. The two patterns below are worth keeping nearby because they appear in pwn corpora but are not yet split into their own dedicated reference.

### Motorola 68000 (m68k) Two-Stage Shellcode

When the shellcode budget is tiny, reuse the binary's own `read()` path to pull a larger second stage into the existing RWX mapping.

m68k reminders:
- syscall number in `d0`
- args in `d1`-`d3`
- `trap #0`
- `read=3`, `dup2=63`, `execve=11`

The first stage's only real job is to increase the read size and jump back into the program's existing read path.

### DOS COM Real Mode Shellcode

DOS COM programs run in writable 16-bit real-mode code segments. If you get any code-segment write primitive, you effectively get shellcode injection.

Useful DOS interrupts:
- `ah=0x3d` open
- `ah=0x3f` read
- `ah=0x09` print `$`-terminated string
- `ah=0x4c` exit

This is the rare case where an "arbitrary write into code" is literally enough because the runtime gives you no modern memory protections to fight.

## See also

- `overflow.md` — canonical stack/global/partial overflow patterns
- `rop.md` — canonical ret2libc, ret2dlresolve, SROP, `.fini_array`, and seccomp ROP
- `heap.md` — canonical glibc heap and House-family coverage
- `heap-fsop.md` — FILE-structure exploitation details
- `sandbox.md` — sandbox and restricted-environment escapes
- `kernel.md` — kernel exploitation setup and mitigation bypass
- `exotic-arch.md` — architecture-specific shellcode and ROP outside x86-64
