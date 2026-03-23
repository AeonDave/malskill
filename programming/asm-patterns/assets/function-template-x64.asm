; ============================================================================
; Function Template — x86-64 (NASM)
; Target: System V ABI (Linux/macOS) + Win64 conditional assembly
; Usage:  Copy, rename function, fill in body.
; ============================================================================

default rel

%ifidn __OUTPUT_FORMAT__, win64
  %define ABI_WIN64
%endif

section .text

; ----------------------------------------------------------------------------
; int64_t my_function(int64_t a, int64_t b, int64_t c)
;
;   System V: rdi=a, rsi=b, rdx=c  — Returns rax
;   Win64:    rcx=a, rdx=b, r8=c   — Returns rax
; ----------------------------------------------------------------------------
global my_function
my_function:
%ifdef ABI_WIN64
    ; Win64 prologue — save callee-saved + shadow space
    push    rbx
    sub     rsp, 32                 ; shadow space (always 32 bytes on Win64)

    ; Map Win64 args → local registers
    mov     rbx, rcx                ; a (saved across calls)
    ; rdx = b (already in place)
    ; r8  = c
%else
    ; System V prologue
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 8                  ; align stack to 16 bytes

    ; Map System V args → local registers
    mov     rbx, rdi                ; a (saved across calls)
    ; rsi = b
    ; rdx = c
%endif

    ; ---- function body ----
    ; TODO: replace with actual logic
    mov     rax, rbx                ; placeholder: return a

%ifdef ABI_WIN64
    add     rsp, 32
    pop     rbx
%else
    add     rsp, 8
    pop     rbx
    pop     rbp
%endif
    ret
