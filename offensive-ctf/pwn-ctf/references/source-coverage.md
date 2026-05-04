# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-pwn`
- Target skill: `pwn-ctf`
- Preserved files: 19

## Imported files and topic cues

### `source-skill.md`

- CTF Binary Exploitation (Pwn)
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- Binary analysis
- Find gadgets
- Debug
- Pattern for offset finding
- libc identification
- Source Code Red Flags
- Race Condition Exploitation
- Common Vulnerabilities
- Protection Implications for Exploit Strategy
- Stack Buffer Overflow
- Parser Stack Overflow (Unchecked memcpy)
- Struct Pointer Overwrite (Heap Menu Challenges)
- Signed Integer Bypass
- Canary-Aware Partial Overflow
- Global Buffer Overflow (CSV Injection)
- ROP Chain Building
- Format String Through Input Transformation
- Kernel Exploitation
- Sandbox and Emulator Escape

### `advanced-exploits-2.md`

- CTF Pwn - Advanced Exploit Techniques (Part 2)
- Table of Contents
- Bytecode Validator Bypass via Self-Modification
- Following bytes: 0x54 0x5e 0x53 0x5a 0x54 0x0f 0xa0
- After push rbx mutates 0xa0 → 0x05: becomes syscall
- io_uring UAF with SQE Injection
- Integer Truncation Bypass int32 to int16
- Value 65534: int32=65534 (passes >= 0), int16=-2 (passes <= 3)
- ring_array[-2] reads 16 bytes before array → leaks GOT/PIE pointers
- Standard ORW fails in Docker:
- open("/flag.txt") → fd=5 (not 3!)
- read(3, buf, size) → reads wrong fd
- Fix: xchg rdi, rax captures open()'s return value dynamically
- rdi now holds actual fd from open()
- GC Null-Reference Cascading Corruption
- Fake FILE structure
- Fake _IO_wide_data
- Fake wide vtable with __doallocate = system
- Overwrite _IO_list_all to point to fake FILE
- Leakless Libc via Multi-fgets stdout FILE Overwrite
- Build ROP chain that calls fgets multiple times to construct stdout on BSS
- Each call writes 7 bytes; null byte falls on canonical address's 0x00 MSB
- Write _flags field
- Write _IO_write_base = GOT address (the value to leak)

### `advanced-exploits-3.md`

- CTF Pwn - Advanced Exploit Techniques (Part 3)
- Table of Contents
- Stack Variable Overlap / Carry Corruption OOB
- 1-Byte Overflow via 8-bit Loop Counter
- Stack layout: buffer[rbp-0x50], size[rbp-0x10], canary[rbp-0x08], rbp, ret
- One-gadget needs NULL at [rbp-0x78] and [rbp-0x60]
- Game AI Arithmetic Mean OOB Read
- Brute-force memory offset to find flag
- Arbitrary Read/Write to Shell via GOT Overwrite
- Step 1: Leak strtoll@GOT
- Step 2: Overwrite strtoll@GOT with system
- Step 3: Next input parsed by strtoll() → system()
- Stack Leak via __environ and memcpy Overflow
- Step 1: Leak libc via GOT read
- Step 2: Leak stack via __environ
- Return address is at known offset from __environ
- Step 3: Plant ROP addresses in the input buffer
- The command buffer is also on the stack at a known offset
- Step 4: memcpy overflow to copy planted payload over return address
- memcpy(dest=stack_buf, src=our_planted_addr, len=enough_to_reach_ret)
- Step 5: EOF triggers return through overwritten address
- JIT Sandbox Escape via Conditional Jump uint16 Truncation
- Embed 2-byte instruction pairs in add immediates, interleaved with jmp $+3
- Each fragment becomes: fragment_bytes + \xEB\x03 (jmp $+3)

### `advanced-exploits-4.md`

- CTF Pwn - Advanced Exploit Techniques (Part 4)
- Table of Contents
- Windows SEH Overwrite + pushad VirtualAlloc ROP
- Key ROP chain structure (simplified)
- Set flProtect = 0x40 (PAGE_EXECUTE_READWRITE) via subtraction (avoid nulls)
- Resolve VirtualAlloc: [TlsAlloc@IAT] + offset
- pushad builds call frame, jmp esp runs shellcode
- include <windows.h>
- SeDebugPrivilege to SYSTEM
- NT AUTHORITY\SYSTEM
- ARM Buffer Overflow with Thumb Shellcode
- Forth Interpreter Command Execution
- GF(2) Gaussian Elimination for Multi-Pass Tcache Poisoning
- Precompute XOR vectors: run cipher with each seed, extract 8 bytes at fd offset
- Compute target delta (safe-linking aware)
- Apply each seed sequentially - order doesn't matter (XOR is commutative)
- Single-Bit-Flip Exploitation Primitive
- Flip bit 6 at address 0x400863 to change 0x48 -> 0x08
- 0x75 (jnz) ^ 0x40 = 0x35 (xor eax, imm32)
- Game of Life Shellcode Evolution via Still-Lifes
- Convert board to coordinates and feed to binary
- UAF via Menu-Driven strdup/free Ordering
- mmap/munmap Size Mismatch UAF for Thread Stack Overlap
- Trigger: allocation uses image dimensions, deallocation uses compressed size

### `advanced-exploits-5.md`

- CTF Pwn - Advanced Exploit Techniques (Part 5)
- Table of Contents
- Chip-8 Emulator Out-of-Bounds Memory for ret2libc
- Host-side exploit driver
- 1. Build a program that reads 8 bytes at offset 6360, then writes the
- one-gadget RIP back to the same offset.
- Double-Precision Float Quicksort Canary Repositioning
- Inputs chosen so that post-qsort order places:
- slot 0 → fake canary (same bits as the real one)
- slot 1 → win()/ret gadget value
- Bloom Filter abs(INT_MIN) Negative Index OOB Write
- Crafting the input so that hash(input) == INT_MIN (0x80000000).
- Many toy bloom filters use FNV-1a or multiplicative hashes; a short
- brute-force finds a colliding prefix in seconds.

### `advanced-exploits.md`

- CTF Pwn - Advanced Exploit Techniques
- Table of Contents
- VM Signed Comparison Bug
- BF JIT Unbalanced Bracket to RWX Shellcode
- Stage 1: Write shellcode to tape via BF +/- operations, then trigger ]
- Use - for bytes >127 (0xff = 1 decrement vs 255 increments)
- Build read(0, tape, 256) shellcode on tape
- Stage 2: Send full execve("/bin/sh") shellcode via stdin after Stage 1 runs
- Type Confusion in Interpreter
- Off-by-One Index to Size Corruption
- Double win() Call Pattern
- DNS Record Buffer Overflow
- ASAN Shadow Memory Exploitation
- 1. Leak PIE base via format string
- 2. Detect real vs fake stack
- Real stack: return address at known offset from format string buffer
- Check if leaked return address matches expected function offset
- 3. Calculate OOB write offset
- Format string buffer at stack offset N
- Target (return address) at stack offset M
- Distance in bytes = (M - N) * 8
- Map to ledger system: slot = distance // 16, sub_offset = distance % 16
- 4. Overwrite return address with win() via OOB ledger write
- Retry until real stack is used (~50% success rate per attempt)

### `advanced.md`

- CTF Pwn - Advanced Techniques
- Table of Contents
- Seccomp Advanced Techniques
- openat2 Bypass (New Age Pattern)
- struct open_how { u64 flags; u64 mode; u64 resolve; }  = 24 bytes
- openat2(AT_FDCWD, filename, &open_how, sizeof(open_how))
- Conditional Buffer Address Restrictions
- Shellcode Construction Without Relocations (pwntools)
- call pushes filename address onto stack, pop rbx retrieves it
- Seccomp Analysis from Disassembly
- rdx Control in ROP Chains
- Use-After-Free (UAF) Exploitation
- JIT Compilation Exploits
- Esoteric Language GOT Overwrite
- Heap Overlap via Base Conversion
- Tree Data Structure Stack Underallocation
- ret2dlresolve
- pwntools has built-in ret2dlresolve support
- Stage 1: Send ROP chain
- Stage 2: Send forged dl-resolve payload
- Forge at a writable address (e.g.,.bss)
- 1. Fake Elf64_Rela: points PLT slot to our fake Elf64_Sym
- 2. Fake Elf64_Sym: st_name offset points to our "system" string
- 3. "system\x00" string

### `field-notes.md`

- Pwn Field Notes
- Table of Contents
- Heap Exploitation
- Additional Exploit Notes
- talloc Pool Header Forgery
- JIT Compilation Exploits
- Type Confusion in Interpreters
- Off-by-One Index / Size Corruption
- Double win() Call
- Arbitrary Read/Write to Shell via GOT Overwrite
- Stack Leak via __environ and memcpy Overflow
- JIT Sandbox Escape via uint16 Jump Truncation
- DNS Compression Pointer Stack Overflow
- ELF Code Signing Bypass via Program Headers
- Game Level Format Signed/Unsigned Coordinate Mismatch
- File Descriptor Inheritance via Missing O_CLOEXEC
- Sign Extension Integer Underflow in Metadata Parsing
- ROP Chain Construction with Read-Only Primitive
- Esoteric Language GOT Overwrite
- Protocol Stack Bleeding
- Timing Attack Flag Recovery
- DNS Record Buffer Overflow
- ASAN Shadow Memory Exploitation
- Format String.fini_array Loop for Multi-Stage Exploitation

### `format-string.md`

- CTF Pwn - Format String Exploitation
- Table of Contents
- Format String Basics
- Format: %<value>c%<offset>$lln + padding + address
- Address at offset 8 when format is 16 bytes
- Note: This prints ~4MB of spaces - be patient waiting for output
- Put known address after N-byte format, check with %<calculated_offset>$p
- Should print 0xdeadbeef if offset 8 is correct
- Argument Retargeting (Non-Positional %n Trick)
- Blind Pwn (No Binary Provided)
- Read GOT entries for known functions
- From leaked __libc_start_main return or similar
- Format String with Filter Bypass
- Write last 3 bytes of debug() addr to strcmp@GOT across 3 payloads
- Pad address to consistent stack offset (e.g., 14th position)
- Format String Canary + PIE Leak
- Stage 1: Leak via format string
- Stage 2: Buffer overflow with known canary
- __free_hook Overwrite via Format String (glibc < 2.34)
- 1. Leak libc via format string
- 2. Write system() address to __free_hook
- 3. Trigger: send command as menu input, program calls free(input_buffer)
- .rela.plt /.dynsym Patching
- Key addresses (from readelf -S)

### `heap-fsop.md`

- CTF Pwn - Heap FILE Structure Attacks
- Table of Contents
- Fastbin stdout Vtable Two-Stage Hijack for PIE + Full RELRO
- Stage 1: Fastbin double-free targeting fake chunk inside stdout
- Use 0x7f byte in libc stdout region as fake chunk size (matches 0x70 fastbin)
- Double-free in 0x70 fastbin
- Redirect fastbin to stdout region
- Stage 2a: First vtable overwrite → gets()
- rdi points to stdout struct, so gets(stdout) reads input into stdout
- Stage 2b: gets() overwrites stdout vtable again → system()
- Next puts() call triggers: vtable lookup → gets(stdout)
- gets() reads from stdin into the stdout struct, overwriting vtable again
- Input: "1\x80;/bin/sh;" — new vtable points to system()
- After gets() returns, next output call triggers system()
- _IO_buf_base Null Byte Overwrite for stdin Hijack
- 1. Arrange heap: allocation immediately before stdin's _IO_buf_base
- (requires heap grooming so chunk is adjacent to FILE struct)
- 2. Null-byte overflow: write one 0x00 byte past chunk boundary
- → corrupts _IO_buf_base LSB → points into FILE struct
- 3. Next read (scanf/fgets): input written into FILE struct fields
- → overwrite _IO_buf_base = target_addr, _IO_buf_end = target_addr + size
- 4. Next read: stdin reads from target_addr → arbitrary write primitive
- → overwrite __free_hook with system() or one_gadget
- 5. Trigger: call a function that invokes free() with a controlled pointer

### `heap-techniques-2.md`

- Heap Exploitation Techniques (Part 2)
- Table of Contents
- UAF Vtable Pointer Encoding Shell Argument
- Heap spray: fill 16MB with system() address at offset +3
- Each spray chunk: 3 bytes padding + 8 bytes system_addr, repeated
- Trigger heap spray via application interface
- UAF object at address 0xXX006873
- Bytes at object start: 73 68 00 XX = "sh\x00..."
- When vtable call dispatches: system(this) → system("sh")
- Trigger: free the target object, then invoke its virtual method
- Uninitialized Chunk Residue Pointer Leak
- 1. Prime the heap: create a contact whose name chunk will later be reused
- as the struct for the next contact.
- 2. Create a new contact — it grabs the previously freed chunk. The old
- name bytes now live in the struct's `bio` field.
- 3. Print → leaks the residue as if it were a bio string.
- tcache strcpy Null-Byte Overflow + Backward Consolidation
- 1. Zero the 0xda memset residue with repeated smaller allocations.
- 2. Set up two adjacent chunks:
- 3. Free victim 1 into the smallbin (needs a > 0x408 sibling to bypass tcache).
- 4. Overflow via strcpy: clears PREV_INUSE, forges prev_size → backward consolidate
- 5. Re-allocate the coalesced region and read the libc pointer that still
- lives in the old fd/bk location.
- Adjacent-Struct fn-Pointer Overflow for Libc Leak + GOT Overwrite

### `heap-techniques.md`

- CTF Pwn - Heap Techniques
- Table of Contents
- House of Apple 2 — FSOP for glibc 2.34+
- When writing to freed chunk, mangle the target address:
- setcontext Variant for SUID Binaries
- Wide vtable targets setcontext instead of system
- setcontext loads registers from offsets relative to RDX (which points to fp->_wide_data):
- RSP from [rdx+0xa0], RIP from [rdx+0xa8], RDI from [rdx+0x68]
- Place ROP chain at _wide_data structure:
- ROP chain at rop_chain_addr:
- House of Einherjar — Off-by-One Null Byte
- Fake chunk layout (at known heap address fake_addr):
- chunk header:
- prev_size:      don't care
- size:           target_size | PREV_INUSE  (must match consolidation math)
- fd:             fake_addr   (self-referencing)
- bk:             fake_addr   (self-referencing)
- fd_nextsize:    fake_addr   (self-referencing, needed for large chunks)
- bk_nextsize:    fake_addr   (self-referencing)
- Victim chunk's prev_size must equal distance from fake_chunk to victim
- Off-by-one NUL clears victim's PREV_INUSE bit
- free(victim) triggers backward consolidation: merges with fake_chunk
- Result: consolidated chunk overlaps other live allocations
- Heap Exploitation

### `kernel-bypass.md`

- CTF Pwn - Kernel Protection Bypass
- Table of Contents
- KASLR and FGKASLR Bypass
- KASLR Bypass via Stack Leak
- define KERNEL_BASE 0xffffffff81000000
- FGKASLR Bypass
- Find gadgets only in the non-randomized range
- KPTI Bypass Methods
- Method 1: swapgs_restore Trampoline
- Method 2: Signal Handler (SIGSEGV)
- include <signal.h>
- Method 3: modprobe_path via ROP
- Method 4: core_pattern via ROP
- SMEP / SMAP Bypass
- KPTI / SMEP / SMAP Quick Reference
- GDB Kernel Module Debugging
- 1. Find module load address (as root inside QEMU)
- vuln 16384 0 - Live 0xffffffffc0000000 (O)
- 2. In GDB, load module symbols at that address
- 3. Inspect stack after breakpoint hit
- Initramfs and virtio-9p Workflow
- Add to QEMU launch script:
- Inside QEMU guest (add to /init or run manually):
- On host, compile exploit into shared directory:

### `kernel-techniques.md`

- CTF Pwn - Kernel Exploitation Techniques
- Table of Contents
- tty_struct RIP Hijack and kROP
- kROP via Fake Vtable on tty_struct
- AAW via ioctl Register Control
- userfaultfd Race Stabilization
- Alternative Race Techniques (uffd Disabled)
- SLUB Allocator Internals
- Freelist Pointer Hardening
- Freelist Obfuscation (CONFIG_SLAB_FREELIST_HARDEN)
- Leak via Kernel Panic
- Race Window Extension via MADV_DONTNEED + mprotect
- Cross-Cache Attack via CPU-Split Strategy
- PTE Overlap Primitive for File Write
- Kernel addr_limit Bypass via Failed File Open
- include <sys/stat.h>
- include <unistd.h>
- include <fcntl.h>
- define DEBUG_FILE "/tmp/debug_log"
- define SYS_TABLE_ADDR 0xffffffff81801400  // from /proc/kallsyms
- Custom binfmt Loader OOB Read + clear_user for Privesc
- Stage 1: leak bprm->cred via OOB header_offset into the kernel-side linux_binprm buffer.
- load_count=5, header_offset=0x80-0x18 -> loads[] parsed from fields past bprm->buf.
- Execute -> dmesg "vm_mmap(..., length=<cred_addr>,...)" reveals the cred pointer.

### `kernel.md`

- CTF Pwn - Linux Kernel Exploitation
- Table of Contents
- Environment Setup and Recon
- QEMU Debug Environment
- Extracting vmlinux
- Use extract-vmlinux.sh from Linux kernel source (scripts/extract-vmlinux)
- Extract ROP gadgets
- Kernel Config Checks
- FGKASLR Detection
- FGKASLR disabled: ~30 sections
- FGKASLR enabled:  36000+ sections (one per function)
- FGKASLR enabled: "too many section (36140)"
- Useful Kernel Structures for Heap Spray
- tty_struct (kmalloc-1024)
- tty_file_private (kmalloc-32)
- poll_list (kmalloc-32 to 1024)
- user_key_payload (kmalloc-32 to 1024)
- setxattr Temporary Buffer (kmalloc-32 to 1024)
- seq_operations (kmalloc-32)
- subprocess_info (kmalloc-128)
- Kernel Stack Overflow and Canary Leak
- Privilege Escalation Primitives
- ret2usr (No SMEP/SMAP)
- Kernel ROP with prepare_kernel_cred / commit_creds

### `overflow-basics.md`

- CTF Pwn - Overflow Basics
- Table of Contents
- Stack Buffer Overflow
- ret2win with Parameter (Magic Value Check)
- Find gadgets
- Stack Alignment (16-byte Requirement)
- ... rest of chain
- Offset Calculation from Disassembly
- Input Filtering (memmem checks)
- Finding Gadgets
- Find pop rdi; ret
- Find simple ret (for alignment)
- Hidden Gadgets in CMP Immediates
- Example: cmpl $0xc35e415f, -0x4(%rbp)
- Bytes: 81 7d fc 5f 41 5e c3
- ^^ ^^ ^^ ^^
- At +3: 5f 41 5e c3 = pop rdi; pop r14; ret
- At +4: 41 5e c3    = pop r14; ret
- At +5: 5e c3       = pop rsi; ret
- pwntools finds these automatically
- Struct Pointer Overwrite (Heap Menu Challenges)
- 1. Create object (allocates struct + sub-allocations)
- 2. Modify name - overflow into pointer field with GOT address
- 3. Modify grade - scanf("%d", corrupted_ptr) writes to GOT

### `rop-advanced.md`

- CTF Pwn - Advanced ROP Techniques
- Table of Contents
- Double Stack Pivot to BSS via leave;ret
- Overflow: 128-byte buffer + RBP + RIP
- After pivot, RSP is at BSS_STAGE. Pre-place a mini-ROP there that
- calls fgets(BSS+0x600, 0x700, stdin) to read the real ROP chain:
- SROP with UTF-8 Payload Constraints
- r15 is the field immediately before rdi in the sigframe
- rdi = pointer to "/bin/sh" = 0x2f9fb0 → bytes [B0, 9F, 2F,...]
- B0, 9F are UTF-8 continuation bytes (10xxxxxx) — invalid as sequence start
- Solution: set r15's last byte to 0xE0 (3-byte UTF-8 leader)
- E0 B0 9F = valid UTF-8 (U+0C1F) spanning r15→rdi boundary
- ROP preamble: 3 UTF-8-safe gadgets
- Place "/bin/sh\0" at offset 0x178 in BUFFER
- Seccomp Bypass
- RETF Architecture Switch for Seccomp Bypass
- Step 1: mprotect BSS as RWX for shellcode
- Step 2: Far return to 32-bit shellcode on BSS
- Or search for byte 0xcb:
- Stack Shellcode with Input Reversal
- .fini_array Hijack
- Find.fini_array address
- Or: objdump -h binary | grep fini_array
- Overwrite with format string %hn (2-byte writes)

### `rop-and-shellcode.md`

- CTF Pwn - ROP Chains and Shellcode
- Table of Contents
- ROP Chain Building
- Common gadgets
- Leak libc
- Two-Stage ret2libc (Leak + Shell)
- Stage 1: Leak libc via puts@PLT, then re-enter vuln for stage 2
- IMPORTANT: Return target after leak
- - Returning to main may crash if check_status/setup corrupts stack
- - Returning to vuln directly may have stack issues
- - Best: return to the 'call vuln' instruction in main (e.g., 0x401239)
- This sets up a clean stack frame via the CALL instruction
- If printf("Laundry complete") has no trailing newline,
- puts() leak appears right after it on the same line:
- Output: "Laundry complete\x50\x5e\x2c\x7e\x56\x7f\n"
- Raw Syscall ROP (When system() Fails)
- Find gadgets in libc
- execve("/bin/sh", NULL, NULL) = syscall 59
- rdx Control in ROP Chains
- Shell Interaction After execve
- Wait for shell to initialize before sending commands
- For flag retrieval:
- DON'T pipe commands via stdin when using pwntools - they get consumed
- by earlier read() calls. Use explicit sendline() after delays instead.

### `sandbox-escape.md`

- CTF Pwn - Sandbox Escape and Restricted Environments
- Table of Contents
- Python Sandbox Escape
- VM Exploitation (Custom Bytecode)
- FUSE/CUSE Character Device Exploitation
- Change /etc/passwd permissions via custom device
- 511 decimal = 0777 octal (rwx for all)
- Now modify passwd to get root
- Busybox/Restricted Shell Escalation
- Shell Tricks
- Redirect stdin/stdout to client socket (fd 3 common for network)
- Or as single command string
- Write-Anywhere via /proc/self/mem
- Service API: send filename, offset, content
- 1. Leak a return address from the stack (or use known binary address)
- 2. Write shellcode to a writable+executable region (or reuse existing code)
- 3. Overwrite return address to point to shellcode
- Overwrite code at known address (e.g., after close@plt returns)
- process_vm_readv Failure as Sandbox Escape
- Named Pipe mkfifo for File Size Check Bypass
- In background, feed overflow payload to the pipe
- Binary sees size=0, skips bounds check, reads arbitrary data
- Lua Integer Underflow via Game Logic
- 1. Identify the two independent reduction events in the game loop

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
