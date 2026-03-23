# Heaven's Gate — WoW64 32→64 Mode Switching

## What is Heaven's Gate?

In WoW64 processes (32-bit executables running on 64-bit Windows), there are **two layers** of hooks:
1. 32-bit ntdll.dll (in SysWoW64) — most AV/EDR products hook here
2. 64-bit ntdll.dll — largely unhooked by 32-bit tools

Heaven's Gate exploits a **far jump/call or far return** to switch the CPU's code segment selector:
- CS = 0x23 → 32-bit (IA-32 compatibility mode)
- CS = 0x33 → 64-bit (IA-32e / long mode)

Switching to CS=0x33 from WoW64 gives direct access to 64-bit ntdll, 64-bit shellcode, and native syscalls — bypassing all 32-bit hooks.

---

## CPU Mode Switch Mechanics

Intel/AMD CPUs use the **CS segment selector** to determine the code execution mode:
```
CS = 0x23 → 32-bit protected mode (IA-32 compatibility mode in 64-bit OS)
CS = 0x33 → 64-bit long mode (IA-32e)
```

A **far return** (`RETF`) pops both IP and CS from the stack, enabling a mode switch:
```nasm
PUSH CS_selector
PUSH target_offset
RETF
```

---

## Implementation

### Step 1: Switch from 32-bit to 64-bit

```nasm
BITS 32
    push 0x33                   ; 64-bit CS selector
    call .get_eip
.get_eip:
    pop  eax
    add  eax, (code64 - .get_eip)
    push eax                    ; 64-bit RIP (zero-extended on switch)
    retf                        ; far return -> CS=0x33, mode -> 64-bit

BITS 64
code64:
    ; Now executing in 64-bit mode!
    ; RSP, RBP etc. are still 32-bit values (zero-extended)
    ; Access 64-bit ntdll.dll, issue native x64 syscalls
    ; ...
```

### Step 2: Return to 32-bit

```nasm
BITS 64
    ; prepare 32-bit return
    sub  rsp, 8
    mov  dword [rsp+4], 0x23    ; 32-bit CS
    mov  dword [rsp+0], eip32   ; 32-bit EIP to return to
    retf
```

---

## Accessing 64-bit ntdll from 32-bit Process

64-bit ntdll is loaded at a different base than 32-bit ntdll (SysWoW64).
From 64-bit mode, the PEB is at GS:[0x60] (not FS) and the 64-bit ntdll is in LDR.

```nasm
BITS 64
    mov  rax, gs:[0x30]         ; TEB64 (WoW64: TEB64 is at +0 of the TEB)
    ; alt: gs:[0x60] = PEB64
    ; walk 64-bit PEB->Ldr->InMemoryOrderModuleList to find ntdll64 base
```

---

## Detection & Limitations

| Limitation | Notes |
|---|---|
| WoW64 processes only | 64-bit native processes already run in long mode — no switch needed |
| CFG enforcement | Control Flow Guard may reject the far jump/return target |
| Windows 10/11 mitigations | Some builds enforce segment limits; test per target OS |
| Stack pointer | At the switch point, RSP is a 32-bit value zero-extended to 64-bit — adjust before any 64-bit stack ops |
| 64-bit stack re-alignment | Apply AlignRSP pattern (see `references/pic-shellcode.md`) |

---

## Detection Signatures

- `RETF` (CB) or `CALL FAR` (9A / FF /3) in 32-bit code is unusual — flagged by some scanners
- The push of `0x33` before a `RETF` is a known Heaven's Gate bytesig
- Obfuscate by computing CS selector at runtime: `xor eax,eax; add eax, 0x33; push eax`

---

## Extended: Returning to 64-bit WoW64 Thunk

To avoid crashing after 64-bit payload executes, return through the legitimate `Wow64Transition` thunk:

```nasm
BITS 64
    ; find Wow64Transition stub in fs/gs (WoW64 transition address)
    ; or resolve ntdll!ZwXxx + Heaven's Gate stub manually
    ; set up 32-bit stub to cleanly continue
    db 0xEA                     ; JMP FAR (x86)
    dd return_eip_32
    dw 0x23
```
