# Pwn Field Notes

Detailed pwn notes that support [`SKILL.md`](../SKILL.md). Read this file after confirming the challenge really needs exploitation.

## Table of Contents

- [Heap Exploitation](#heap-exploitation)
- [Additional Exploit Notes](#additional-exploit-notes)
  - [talloc Pool Header Forgery](#talloc-pool-header-forgery)
  - [JIT Compilation Exploits](#jit-compilation-exploits)
  - [Type Confusion in Interpreters](#type-confusion-in-interpreters)
  - [Off-by-One Index / Size Corruption](#off-by-one-index-size-corruption)
  - [Double win() Call](#double-win-call)
  - [Arbitrary Read/Write to Shell via GOT Overwrite]
  - [Stack Leak via __environ and memcpy Overflow]
  - [JIT Sandbox Escape via uint16 Jump Truncation](#jit-sandbox-escape-via-uint16-jump-truncation)
  - [DNS Compression Pointer Stack Overflow]
  - [ELF Code Signing Bypass via Program Headers](#elf-code-signing-bypass-via-program-headers)
  - [Game Level Format Signed/Unsigned Coordinate Mismatch](#game-level-format-signedunsigned-coordinate-mismatch)
  - [File Descriptor Inheritance via Missing O_CLOEXEC](#file-descriptor-inheritance-via-missing-o_cloexec)
  - [Sign Extension Integer Underflow in Metadata Parsing]
  - [ROP Chain Construction with Read-Only Primitive](#rop-chain-construction-with-read-only-primitive)
  - [Esoteric Language GOT Overwrite]
  - [Protocol Stack Bleeding](#protocol-stack-bleeding)
  - [Timing Attack Flag Recovery]
  - [DNS Record Buffer Overflow]
  - [ASAN Shadow Memory Exploitation](#asan-shadow-memory-exploitation)
  - [Format String.fini_array Loop for Multi-Stage Exploitation](#format-stringfini_array-loop-for-multi-stage-exploitation)
  - [Format String with RWX.fini_array Hijack](#format-string-with-rwxfini_array-hijack)
  - [Custom Canary Preservation](#custom-canary-preservation)
  - [MD5 Preimage Gadget Construction](#md5-preimage-gadget-construction)
  - [Python Sandbox Escape](#python-sandbox-escape)
  - [VM GC-Triggered UAF (Slab Reuse)](#vm-gc-triggered-uaf-slab-reuse)
  - [GC Null-Reference Cascading Corruption](#gc-null-reference-cascading-corruption)
  - [OOB Read via Stride/Rate Leak](#oob-read-via-striderate-leak)
  - [SROP with UTF-8 Constraints](#srop-with-utf-8-constraints)
  - [VM Exploitation (Custom Bytecode)](#vm-exploitation-custom-bytecode)
  - [FUSE/CUSE Character Device Exploitation](#fusecuse-character-device-exploitation)
  - [Busybox/Restricted Shell Escalation](#busyboxrestricted-shell-escalation)
  - [process_vm_readv Sandbox Bypass](#process_vm_readv-sandbox-bypass)
  - [Named Pipe (mkfifo) File Size Bypass](#named-pipe-mkfifo-file-size-bypass)
  - [Shell Tricks](#shell-tricks)
  - [Double Stack Pivot to BSS via leave;ret](#double-stack-pivot-to-bss-via-leaveret)
  - [RETF Architecture Switch for Seccomp Bypass](#retf-architecture-switch-for-seccomp-bypass)
  - [Leakless Libc via Multi-fgets stdout FILE Overwrite]
  - [Signed/Unsigned Char Underflow to Heap Overflow]
  - [TLS Destructor Hijack via `__call_tls_dtors`](#tls-destructor-hijack-via-__call_tls_dtors)
  - [Signed Int Overflow to Negative OOB Heap Write]
  - [Custom Shadow Stack Bypass via Pointer Overflow]
  - [Windows SEH Overwrite + VirtualAlloc ROP]
  - [SeDebugPrivilege to SYSTEM](#sedebugprivilege-to-system)
  - [mmap/munmap Size Mismatch UAF](#mmapmunmap-size-mismatch-uaf)
  - [strcspn Indirect Null Byte Injection](#strcspn-indirect-null-byte-injection)
  - [Windows CFG Bypass Using system() as Valid Call Target](#windows-cfg-bypass-using-system-as-valid-call-target)
  - [4-Byte Shellcode with Timing Side-Channel](#4-byte-shellcode-with-timing-side-channel)
  - [CRC Oracle as Arbitrary Read Primitive](#crc-oracle-as-arbitrary-read-primitive)
  - [UTF-8 Case Conversion Buffer Overflow]
- [Useful Commands](#useful-commands)

## Heap Exploitation

- tcache poisoning (glibc 2.26+), fastbin dup / double free
- House of Force (old glibc), unsorted bin attack
- **House of Apple 2** (glibc 2.34+): FSOP (File Stream Oriented Programming) via `_IO_wfile_jumps` when `__free_hook`/`__malloc_hook` removed. Fake FILE with `_flags = " sh"`, vtable chain → `system(fp)`. For SUID binaries: use `setcontext()` variant to stack pivot → `setuid(0)` → `system()` (dash drops privs when uid != euid). See [heap.md].
- **Classic unlink**: Corrupt adjacent chunk metadata, trigger backward consolidation for write-what-where primitive. Pre-2.26 glibc only. See [heap.md](heap.md#classic-heap-unlink-attack).
- **House of Force:** Corrupt top chunk size to `0xffffffffffffffff`, next `malloc(target - top - 2*SIZE_SZ)` returns arbitrary address. Pre-2.29 glibc only. See [heap.md].
- **House of Einherjar**: Off-by-one null clears PREV_INUSE, backward consolidation with self-pointing unlink.
- **Safe-linking** (glibc 2.32+): tcache fd mangled as `ptr ^ (chunk_addr >> 12)`.
- Check glibc version: `strings libc.so.6 | grep GLIBC`
- For named glibc techniques, sanity-check the matching how2heap `glibc_<version>/technique.c` first; see [heap.md](heap.md#versioned-corpus-workflow). Treat House names as hypotheses, not compatibility proof.
- For pwn.college or other lab practice paths, use [practice-labs.md](practice-labs.md) and avoid publishing challenge-specific solution steps.
- Freed chunks contain libc pointers (fd/bk) -> leak via error messages or missing null-termination
- Heap feng shui: control alloc order/sizes, create holes, place targets adjacent to overflow source
- **Unsafe unlink + top chunk consolidation**: After unlink writes self-pointer to BSS, craft fake BSS chunk spanning to top chunk. `free()` consolidates, relocating heap base to BSS. Subsequent mallocs return BSS memory. See [heap.md].

**House of Orange:** Corrupt top chunk size → large malloc forces sysmalloc → old top freed without calling `free()`. Chain with FSOP. See [heap.md](heap.md#house-of-orange).

**House of Spirit:** Forge fake chunk in target area, `free()` it, reallocate to get write access. Requires valid size + next chunk size. See [heap.md](heap.md#house-of-spirit).

**House of Lore:** Corrupt smallbin `bk` → link fake chunk → second malloc returns attacker-controlled address. See [heap.md](heap.md#house-of-lore).

**ret2dlresolve:** Forge Elf64_Sym/Rela to resolve arbitrary libc function without leak. `Ret2dlresolvePayload(elf, symbol="system", args=["/bin/sh"])`. Requires Partial RELRO. See [advanced-primitives.md](advanced-primitives.md#ret2dlresolve).

**tcache stashing unlink (glibc 2.29+):** Corrupt smallbin chunk's `bk` during tcache stashing → arbitrary address linked into tcache → write primitive. See [heap.md](heap.md#tcache-stashing-unlink-attack).

**UAF vtable pointer encoding shell argument:** After UAF, heap spray places `system()` at offset +3. Object address containing `0x6873` ("sh") in low bytes doubles as the command string argument when `system(this)` is called through the hijacked vtable. See [heap.md](heap.md#uaf-vtable-pointer-encoding-shell-argument).

**Fastbin stdout vtable two-stage hijack (PIE + Full RELRO):** Use 0x7f byte in libc's stdout region as fake fastbin chunk size. Two-stage: first vtable redirect to `gets()` (rdi=stdout), then `gets()` overwrites vtable again to `system()` with command string. See [heap.md].

See [heap.md](heap.md) for House of Apple 2 FSOP chain (+ setcontext SUID variant), House of Orange/Spirit/Lore/Force, tcache stashing unlink, custom allocator exploitation (nginx pools, talloc), classic unlink, musl libc heap. See [advanced-primitives.md](advanced-primitives.md) for ret2dlresolve, heap overlap via base conversion, tree data structure stack underallocation, and other edge-case pivots.

**GF(2) Gaussian elimination for tcache poisoning:** When a deterministic XOR cipher corrupts heap metadata as a side effect, model the corruption as linear algebra over GF(2). Find a subset of cipher seeds whose combined XOR transforms tcache `fd` from current value to target address. See [weird-machines.md](weird-machines.md).

## Additional Exploit Notes

### talloc Pool Header Forgery
**Pattern:** talloc (hierarchical allocator in Samba/CUPS) pool header forgery. Forge fake pool header with controlled `end`/`object_count` fields to redirect next `talloc()` to arbitrary address. Leak GOT for libc, write `__free_hook` with `system()`. See [heap.md].

### JIT Compilation Exploits
**Pattern:** Off-by-one in instruction encoding -> misaligned machine code. Embed shellcode as operand bytes of subtraction operations, chain with 2-byte `jmp` instructions. See [advanced-primitives.md](advanced-primitives.md).

**BF JIT unbalanced bracket:** Unbalanced `]` pops tape address (RWX) from stack → write shellcode to tape with `+`/`-`, trigger `]` to jump to it. See [advanced-primitives.md](advanced-primitives.md).

### Type Confusion in Interpreters
**Pattern:** Interpreter sets wrong type tag → struct fields reinterpreted. Unused padding bytes in one variant become active pointers/data in another. Flag bytes as type value trigger UNKNOWN_DATA dump. See [advanced-primitives.md](advanced-primitives.md).

### Off-by-One Index / Size Corruption
**Pattern:** Array index 0 maps to `entries[-1]`, overlapping struct metadata (size field). Corrupted size → OOB read leaks canary/libc, then OOB write places ROP chain. See [advanced-primitives.md](advanced-primitives.md).

### Double win() Call
**Pattern:** `win()` checks `if (attempts++ > 0)` — needs two calls. Stack two return addresses: `p64(win) + p64(win)`. See [advanced-primitives.md](advanced-primitives.md).

### Arbitrary Read/Write to Shell via GOT Overwrite
**Pattern:** Binary provides explicit read/write primitives. Leak libc via GOT read, overwrite `strtoll@GOT` with `system`, next call becomes `system(user_input)`. Choose GOT targets where the function takes a user-controlled string as first arg. See [advanced-primitives.md].

### Stack Leak via __environ and memcpy Overflow
**Pattern:** Binary with read-only primitive and `memcpy(stack_buf, user_addr, user_len)`. Leak libc via GOT, leak stack via `__environ`, plant ROP addresses in input buffer, overflow memcpy to copy them over return address, send EOF to trigger return. See [advanced-primitives.md].

### JIT Sandbox Escape via uint16 Jump Truncation
**Pattern:** JIT compiler truncates conditional jump offset to uint16, causing misalignment when code exceeds 64KB. Embed 2-byte shellcode fragments in `add` immediates, thread with `jmp $+3` to chain execution. See [advanced-primitives.md].

### DNS Compression Pointer Stack Overflow
**Pattern:** Custom DNS server doesn't track decompressed name length. Compression pointer chains revisit data, overflowing stack buffer. Split ROP chain across multiple DNS question entries. See [advanced-primitives.md].

### ELF Code Signing Bypass via Program Headers
**Pattern:** Signing scheme hashes section headers/content but not program headers. Append shellcode, modify LOAD segment's `p_offset` to point to appended data — signature still valid, loader executes attacker code. See [advanced-primitives.md].

### Game Level Format Signed/Unsigned Coordinate Mismatch
**Pattern:** Level editor parses signed integer coordinates but bounds-checks via unsigned comparison — negative coordinates pass the check and write block IDs (arbitrary bytes) before the level array, enabling stack return address overwrite. Leak stack address via hidden developer mode, encode shellcode as block IDs. See [advanced-primitives.md].

### File Descriptor Inheritance via Missing O_CLOEXEC
**Pattern:** Service reads secret into `memfd_create()` FD without `MFD_CLOEXEC`, then calls `system()` for user commands — child inherits the FD. Bypass `strstr()` keyword filters with shell quote splitting (`p'r'oc` instead of `proc`) to read `/proc/self/fd/N`. See [advanced-primitives.md].

### Sign Extension Integer Underflow in Metadata Parsing
**Pattern:** Metadata parser's `to_int32` converts unsigned values >= 0x80000000 to negative signed integers. Used as array index/offset, this causes OOB memory access. Iterate byte-by-byte to leak flag from memory. See [advanced-primitives.md].

### ROP Chain Construction with Read-Only Primitive
**Pattern:** Binary with only `read()` primitive — no write, no win function. Leak libc via GOT, then "import" arbitrary byte values onto the stack by reading from libc offsets whose content matches desired ROP gadget addresses. Read primitive doubles as write primitive. See [advanced-primitives.md].

### Esoteric Language GOT Overwrite
**Pattern:** Brainfuck/Pikalang interpreter with unbounded tape = arbitrary read/write relative to buffer base. Move pointer to GOT, overwrite byte-by-byte with `system()`. See [advanced-primitives.md](advanced-primitives.md).

### Protocol Stack Bleeding
Custom network protocols echoing data based on length field leak stack memory when length exceeds actual data (Heartbleed-style). See [overflow.md].

### Timing Attack Flag Recovery
Validation time varies per correct character; measure elapsed time per candidate byte to recover flag character-by-character. See [advanced-primitives.md].

### DNS Record Buffer Overflow
**Pattern:** Many AAAA records overflow stack buffer in DNS response parser. Set up DNS server with excessive records, overwrite return address. See [advanced-primitives.md](advanced-primitives.md).

### ASAN Shadow Memory Exploitation
**Pattern:** Binary with AddressSanitizer has format string + OOB write. ASAN may use "fake stack" (50% chance). Leak PIE, detect real vs fake stack, calculate OOB write offset to overwrite return address. See [advanced-primitives.md](advanced-primitives.md).

### Format String.fini_array Loop for Multi-Stage Exploitation
**Pattern:** No GOT function called after `printf()`. Overwrite `.fini_array[0]` with `main()` for re-execution loop. Stage 1: leak libc/stack. Stage 2: `printf@GOT` to `system()`, `__stack_chk_fail@GOT` to `main()`. Stage 3: corrupt canary to trigger `__stack_chk_fail` re-entry, now `printf(input)` is `system(input)`. See [format-string.md].

### Format String with RWX.fini_array Hijack
**Pattern:** Base85-encoded input in RWX memory passed to `printf()`. Write shellcode to RWX region, overwrite `.fini_array[0]` via format string `%hn` writes. Use convergence loop for base85 argument numbering. See [advanced-primitives.md](advanced-primitives.md).

### Custom Canary Preservation
**Pattern:** Buffer overflow must preserve known canary value. Write exact canary bytes at correct offset: `b'A' * 64 + b'BIRD' + b'X'`. See [advanced-primitives.md](advanced-primitives.md).

### MD5 Preimage Gadget Construction
**Pattern:** Brute-force MD5 preimages with `eb 0c` prefix (jmp +12) to skip middle bytes; bytes 14-15 become 2-byte i386 instructions. Build syscall chains from gadgets like `31c0` (xor eax), `cd80` (int 0x80). See [advanced-primitives.md](advanced-primitives.md) for the compact pattern summary.

### Python Sandbox Escape
AST bypass via f-strings, audit hook bypass with `b'flag.txt'` (bytes vs str), MRO-based `__builtins__` recovery. See [sandbox.md](sandbox.md).

### VM GC-Triggered UAF (Slab Reuse)
**Pattern:** Custom VM with NEWBUF/SLICE/GC opcodes. Slicing creates shared slab reference; dropping+GC'ing slice frees slab while parent still holds it. Allocate function object to reuse slab, leak code pointer via UAF read, overwrite with win() address. See [advanced-primitives.md](advanced-primitives.md).

### GC Null-Reference Cascading Corruption
**Pattern:** Mark-compact GC follows null references to heap address 0, creating fake object. During compaction, memmove cascades corruption through adjacent object headers → OOB access → libc leak → FSOP. See [advanced-primitives.md](advanced-primitives.md).

### OOB Read via Stride/Rate Leak
**Pattern:** String processing function with user-controlled stride skips past null terminator, leaking stack canary and return address one byte at a time. Then overflow with leaked values. See [overflow.md].

### SROP with UTF-8 Constraints
**Pattern:** When payload must be valid UTF-8 (Rust binaries, JSON parsers), use SROP — only 3 gadgets needed. Multi-byte UTF-8 sequences spanning register field boundaries "fix" high bytes. See [rop.md](rop.md).

### VM Exploitation (Custom Bytecode)
**Pattern:** Custom VM with OOB read/write in syscalls. Leak PIE via XOR-encoded function pointer, overflow to rewrite pointer with `win() ^ KEY`. See [sandbox.md](sandbox.md).

### FUSE/CUSE Character Device Exploitation
Look for `cuse_lowlevel_main()` / `fuse_main()`, backdoor write handlers with command parsing. Exploit to `chmod /etc/passwd` then modify for root access. See [sandbox.md](sandbox.md).

### Busybox/Restricted Shell Escalation
Find writable paths via character devices, target `/etc/passwd` or `/etc/sudoers`, modify permissions then content. See [sandbox.md](sandbox.md).

### process_vm_readv Sandbox Bypass
**Pattern:** Sandbox validates file paths via `process_vm_readv()` + `realpath()`. Map memory with `PROT_READ` only at fixed address via `mmap(MAP_FIXED)` - sandbox's `process_vm_readv` fails silently, bypassing path validation entirely. See [sandbox.md].

### Named Pipe (mkfifo) File Size Bypass
**Pattern:** Binary checks `stat()` file size before reading. Named pipes report `st_size = 0` but deliver arbitrary data via `read()`. `mkfifo /tmp/pipe && cat payload > /tmp/pipe &` then pass pipe to binary. Combine with `ln -s /flag arena.c` for string reuse in ROP. See [sandbox.md].

### Shell Tricks
`exec<&3;sh>&3` for fd redirection, `$0` instead of `sh`, `ls -la /proc/self/fd` to find correct fd. See [sandbox.md](sandbox.md).

### Double Stack Pivot to BSS via leave;ret
**Pattern:** Small overflow (only RBP + RIP). Overwrite RBP → BSS address, RIP → `leave; ret` gadget. `leave` sets RSP = RBP (BSS). Second stage at BSS calls `fgets(BSS+offset, large_size, stdin)` to load full ROP chain. See [rop.md].

### RETF Architecture Switch for Seccomp Bypass
**Pattern:** Seccomp blocks 64-bit syscalls (`open`, `execve`). Use `retf` gadget to load CS=0x23 (IA-32e compatibility mode). In 32-bit mode, `int 0x80` uses different syscall numbers (open=5, read=3, write=4) not covered by the filter. Requires `mprotect` to make BSS executable for 32-bit shellcode. See [rop.md].

### Leakless Libc via Multi-fgets stdout FILE Overwrite
**Pattern:** No libc leak available. Chain multiple `fgets(addr, 7, stdin)` calls via ROP to construct fake stdout FILE struct on BSS. Set `_IO_write_base` to GOT entry, call `fflush(stdout)` → leaks GOT content → libc base. The 7-byte writes avoid null byte corruption since libc pointer MSBs are already `\x00`. See [advanced-primitives.md](advanced-primitives.md).

### Signed/Unsigned Char Underflow to Heap Overflow
**Pattern:** Size field stored as `signed char`, cast to `unsigned char` for use. `size = -112` → `(unsigned char)(-112) = 144`, overflowing a 127-byte buffer by 17 bytes. Combine with XOR keystream brute-force for byte-precise writes, forge chunk sizes for unsorted bin promotion (libc leak), FSOP stdout for TLS leak, and TLS destructor (`__call_tls_dtors`) overwrite for RCE. See [advanced-primitives.md](advanced-primitives.md).

### TLS Destructor Hijack via `__call_tls_dtors`
**Pattern:** Alternative to House of Apple 2 on glibc 2.34+. Forge `__tls_dtor_list` entries with pointer-guard-mangled function pointers: `encoded = rol(target ^ pointer_guard, 0x11)`. Requires leaking pointer guard from TLS segment (via FSOP stdout redirection). Each node calls `PTR_DEMANGLE(func)(obj)` on exit. See [advanced-primitives.md](advanced-primitives.md).

### Signed Int Overflow to Negative OOB Heap Write
**Pattern:** Index formula `y * width + x` in signed 32-bit int overflows to negative value, passing bounds check and writing backward into heap metadata. Use to corrupt adjacent chunk sizes/pointers, leak libc via unsorted bin, redirect a data pointer to `environ` for stack leak, then write ROP chain to main's return address. When binary is behind a web API, chain XSS → Fetch API → heap exploit, and inject `\n` in API parameters for command stacking via `sendline()`. See [advanced-primitives.md](advanced-primitives.md) for the full bridge pattern.

### Custom Shadow Stack Bypass via Pointer Overflow
**Pattern:** Userland shadow stack in `.bss` with unbounded pointer. Recurse to advance `shadow_stack_ptr` past the array into user-controlled memory (e.g., `username` buffer), write `win()` there, then overflow the hardware stack return address to match. Both checks pass. See [advanced-primitives.md](advanced-primitives.md).

### Windows SEH Overwrite + VirtualAlloc ROP
Format string leak defeats ASLR. SEH (Structured Exception Handler) overwrite with stack pivot to ROP chain. `pushad` builds VirtualAlloc call frame for DEP (Data Execution Prevention) bypass. Detached process launcher for shell stability on thread-based servers. See [windows-pwn.md](windows-pwn.md).

### SeDebugPrivilege to SYSTEM
If the compromised context has `SeDebugPrivilege`, treat it as a near-direct path to SYSTEM: confirm with `whoami /priv`, enable the privilege if needed, and migrate or inject into a SYSTEM-owned process such as `winlogon.exe`. See [windows-pwn.md](windows-pwn.md).

### mmap/munmap Size Mismatch UAF
Over-unmap via `mmap(small)` / `munmap(large)` destroys adjacent mappings. A later thread stack can fill the gap, turning a stale buffer pointer into a write-into-stack primitive. See [weird-machines.md](weird-machines.md).

### strcspn Indirect Null Byte Injection
`strcspn(buf, "\r\n")` followed by a null write truncates paths at an injected newline. Use it to remove forced suffixes or wrappers when raw null bytes are filtered. See [weird-machines.md](weird-machines.md).

### Windows CFG Bypass Using system() as Valid Call Target
CFG rejects arbitrary call targets, but `system()` is a legitimate exported entry point and therefore still callable through an overwritten function pointer. See [windows-pwn.md](windows-pwn.md).

### 4-Byte Shellcode with Timing Side-Channel
**Pattern:** Binary executes only 4 bytes of user shellcode in a 4096-iteration loop. Callee-saved registers (r12-r15) persist across iterations, enabling incremental state building. The 4096x loop amplifies timing differences for reliable side-channel measurement. See [advanced-primitives.md](advanced-primitives.md).

### CRC Oracle as Arbitrary Read Primitive
**Pattern:** CRC is bijective on single bytes. Overflow a pointer to control the CRC input address, precompute all 256 single-byte CRCs, and reverse-lookup each byte of arbitrary memory. Chain reads to leak GOT, libc, stack, and canary. See [advanced-primitives.md](advanced-primitives.md).

### UTF-8 Case Conversion Buffer Overflow
**Pattern:** Unicode case conversion can expand character byte length (e.g., 2-byte UTF-8 becomes 4 bytes when uppercased). If buffer is sized for input length, the longer output overflows. Affects GLib `g_utf8_strup()`, ICU, and similar functions. See [overflow.md](overflow.md).

## Useful Commands

`checksec`, `one_gadget`, `ropper`, `ROPgadget`, `seccomp-tools dump`, `strings libc | grep GLIBC`. See [rop.md](rop.md) for full command list and pwntools template.
