# CTF Reverse - Constraint and Crypto Patterns

Patterns centered on staged decryptors, lattices, field arithmetic, decision trees, and other high-structure validators.

## Table of Contents
- [Multi-Layer Self-Decrypting Binary](#multi-layer-self-decrypting-binary)
- [Embedded ZIP + XOR License Decryption](#embedded-zip-xor-license-decryption)
- [Stack String Deobfuscation from .rodata XOR Blob](#stack-string-deobfuscation-from-rodata-xor-blob)
- [Prefix Hash Brute-Force](#prefix-hash-brute-force)
- [CVP/LLL Lattice for Constrained Integer Validation](#cvplll-lattice-for-constrained-integer-validation)
- [Decision Tree Function Obfuscation](#decision-tree-function-obfuscation)
- [GF(2^8) Gaussian Elimination for Flag Recovery](#gf28-gaussian-elimination-for-flag-recovery)
- [ROP Chain Obfuscation in Modified Binary](#rop-chain-obfuscation-in-modified-binary)

## Multi-Layer Self-Decrypting Binary

```c
void *text = mmap((void*)0x400000, text_size, PROT_RWX, MAP_FIXED|MAP_PRIVATE, fd, 0);
void *bss = mmap((void*)bss_addr, bss_size, PROT_RW, MAP_FIXED|MAP_SHARED, shm_fd, 0);
```

```c
for (int candidate = 0; candidate < 65536; candidate++) {
    pid_t pid = fork();
    if (pid == 0) {
        mmap(bss_addr, bss_size, PROT_RW, MAP_FIXED|MAP_PRIVATE, shm_fd, 0);
        inject_key(candidate >> 8, candidate & 0xff);
        ((void(*)())layer_addr)();
        if (count_read_calls(next_layer_addr) == 2) signal_found(candidate);
        _exit(0);
    }
}
```

**Key insight:** Treat the task as a brute-force engine design problem, not just a reversing problem.

## Embedded ZIP + XOR License Decryption

```bash
readelf -s binary | grep -E "EMBEDDED|ENCRYPTED|LICENSE"
```

```python
with open('binary', 'rb') as f:
    data = f.read()
zip_start = data.find(b'PK\x03\x04')
open('embedded.zip', 'wb').write(data[zip_start:zip_start+384])
```

```python
license = open('license.txt', 'rb').read()
enc_msg = open('encrypted_msg.bin', 'rb').read()
flag = bytes(a ^ b for a, b in zip(enc_msg, license))
```

## Stack String Deobfuscation from .rodata XOR Blob

```python
from elftools.elf.elffile import ELFFile
with open(binary, "rb") as f:
    elf = ELFFile(f)
    ro = elf.get_section_by_name(".rodata")
    blob = ro.data()[offset:offset+size]
```

**Variant clues:** position permutation, previous-byte state dependence, and hashy constants like `0x9E3779B9` or `0x85EBCA6B`.

## Prefix Hash Brute-Force

```python
for pos in range(1, len(target_hashes)):
    for ch in charset:
        candidate = known_prefix + ch + padding
        hashes = run_binary(candidate)
        if hashes[pos] == target_hashes[pos]:
            known_prefix += ch
            break
```

## CVP/LLL Lattice for Constrained Integer Validation

```python
from sage.all import *

def solve_constrained_matrix(coefficients, targets, char_range=(32, 126)):
    n = len(coefficients[0])
    mid = (char_range[0] + char_range[1]) // 2
    M = matrix(ZZ, n + len(targets), n + len(targets))
    scale = 1000
```

```python
from sympy import Matrix
M_mod = Matrix(coefficients) % (2**32)
v_mod = Matrix(targets) % (2**32)
solution = M_mod.solve(v_mod)
```

**Key insight:** Constrained printable solutions are often lattice problems wearing a validator costume.

## Decision Tree Function Obfuscation

```python
from ghidra.program.model.listing import *
from ghidra.program.model.symbol import *

fm = currentProgram.getFunctionManager()
results = []
for func in fm.getFunctions(True):
    name = func.getName()
    if name.startswith('f') and name[1:].isdigit():
        inst_iter = currentProgram.getListing().getInstructions(func.getBody(), True)
        for inst in inst_iter:
            if inst.getMnemonicString() == 'CMP':
                operand = inst.getOpObjects(1)
                if operand:
                    results.append((name, int(operand[0].getValue())))
```

**Key insight:** Auto-generated trees are repetitive by construction, so script extraction beats node-by-node reading.

## GF(2^8) Gaussian Elimination for Flag Recovery

```python
def gf_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p
```

```python
for col in range(N):
    pivot = next((r for r in range(col, N) if aug[r][col] != 0), -1)
```

**Key insight:** The `0x1b` reduction constant is often the loudest clue that you're in AES-field arithmetic.

## ROP Chain Obfuscation in Modified Binary

```python
import gdb
magic_buf = 0x080b0000
buf_size = 0x40000
offset = 0
while offset < buf_size:
    addr = int.from_bytes(gdb.selected_inferior().read_memory(magic_buf + offset, 4), 'little')
    gdb.execute(f'x/3i {addr}')
    offset += 4
```

```python
import hashlib
for s in range(128 * 0x35):
    h = hashlib.md5(str(s ^ xor_constant).encode()).hexdigest()
```

**Key insight:** ROPfuscated validators are still algorithms; dump the gadget stream, compress the repetition, solve the real math.
