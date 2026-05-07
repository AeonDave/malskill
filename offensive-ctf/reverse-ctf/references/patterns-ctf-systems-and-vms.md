# CTF Reverse - Systems and VM-Heavy Patterns

Patterns where the target behaves like a mini-system: games, kernels, VMs, loaders, host/guest orchestration, or service-like binaries.

## Table of Contents
- [Sprague-Grundy Game Theory Binary](#sprague-grundy-game-theory-binary)
- [Kernel Module Maze Solving](#kernel-module-maze-solving)
- [Multi-Threaded VM with Channel Synchronization](#multi-threaded-vm-with-channel-synchronization)
- [Backdoored Shared Library Detection via String Diffing](#backdoored-shared-library-detection-via-string-diffing)
- [Custom binfmt Kernel Module with RC4 Flat Binaries](#custom-binfmt-kernel-module-with-rc4-flat-binaries)
- [Hash-Resolved Imports / No-Import Ransomware](#hash-resolved-imports--no-import-ransomware)
- [ELF Section Header Corruption for Anti-Analysis](#elf-section-header-corruption-for-anti-analysis)
- [VM Trace Diffing Instead of Full Disassembly](#vm-trace-diffing-instead-of-full-disassembly)

## Sprague-Grundy Game Theory Binary

```python
MASK64 = (1 << 64) - 1

def prng_step(state, pile_count, k):
    r12 = state[2] ^ 0x28027f28b04ccfa7
    rax = (state[1] + r12) & MASK64
    s0_new = ROL64((state[0] ** 2 + rax) & MASK64, 32)
    r12_upd = (r12 + rax) & MASK64
    s0_final = ROL64((s0_new ** 2 + r12_upd) & MASK64, 32)
    pile_idx = rax % pile_count
    amount = (r12_upd % k) + 1
    return pile_idx, amount, [s0_final, r12_upd, state[2]]
```

**Key insight:** If PRNG evolution depends on user feedback, solve the game and the state machine together.

## Kernel Module Maze Solving

```c
int visited[16][16][16];
int bad[16][16][16];

void dfs(int fd, int x, int y, int z) {
    if (visited[x][y][z] || bad[x][y][z]) return;
    visited[x][y][z] = 1;
    int status = ioctl_get_status(fd);
    if (status == 1) { read_flag(fd); exit(0); }
    if (status == 2) { bad[x][y][z] = 1; return; }
}
```

**Key insight:** Dynamic ioctl probing is often faster than full static RE of stripped kernel tasks.

## Multi-Threaded VM with Channel Synchronization

```python
from collections import deque

def solve_flag(scramble_vals, lookup_table, initial_state, target_state):
    flag = [None] * 30
    states = {initial_state}
    for pos in range(28, 4, -1):
        next_states = {}
        for state in states:
            for ch in range(32, 127):
                transformed = transform(ch, scramble_vals[pos])
                digits = to_base4(transformed)
                new_state = apply_digits(state, digits, lookup_table)
                if new_state is not None:
                    next_states.setdefault(new_state, []).append((state, ch))
        states = set(next_states.keys())
```

**Key insight:** Trace thread roles first; only then rebuild the state machine.

## Backdoored Shared Library Detection via String Diffing

```bash
ldd ./binary
strings /lib/libc/libc.so.6 > suspicious_strings
strings /lib32/libc-2.15.so > normal_strings
diff suspicious_strings normal_strings
```

**Key insight:** If behavior changes between GDB and normal execution, suspect environment-sensitive libraries before deeper payload logic.

## Custom binfmt Kernel Module with RC4 Flat Binaries

```python
from Crypto.Cipher import ARC4

key = bytes([0x41, 0x42, 0x43, ...])
with open('encrypted.bin', 'rb') as f:
    header = f.read(HEADER_SIZE)
    encrypted = f.read()

cipher = ARC4.new(key)
decrypted = cipher.decrypt(encrypted)
```

**Key insight:** Loader modules frequently embed both the decryption routine and the load address you need for clean import into a disassembler.

## Hash-Resolved Imports / No-Import Ransomware

```c
#define _GNU_SOURCE
#include <dlfcn.h>
#include <openssl/evp.h>
#include <stdio.h>

int EVP_CipherInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *type,
                       ENGINE *impl, const unsigned char *key,
                       const unsigned char *iv) {
    if (key) {
        FILE *f = fopen("/tmp/aes_key.bin", "wb");
        fwrite(key, 1, 32, f);
        fclose(f);
    }
    return ((int (*)(EVP_CIPHER_CTX*, const EVP_CIPHER*, ENGINE*,
            const unsigned char*, const unsigned char*))dlsym(RTLD_NEXT, "EVP_CipherInit_ex"))
            (ctx, type, impl, key, iv);
}
```

**Key insight:** When import hashing is just a delivery mechanism, hook the resolved functionality instead of reconstructing the whole hash oracle.

## ELF Section Header Corruption for Anti-Analysis

```python
with open("stubborn_elf", "rb") as f:
    data = f.read()
magic = b"\xDE\xAD\xBE\xEF\xCA\xFE\xBA\xBE"
idx = data.find(magic)
if idx >= 0:
    encrypted = data[idx + len(magic):]
    decrypted = bytes(b ^ 0x42 for b in encrypted)
```

**Recovery approach:**
```bash
printf '\x00\x00\x00\x00\x00\x00\x00\x00' | dd of=binary bs=1 seek=40 conv=notrunc
readelf -l stubborn_elf
```

## VM Trace Diffing Instead of Full Disassembly

```python
def on_dispatch():
    op  = read_byte(bytecode + pc)
    top = stack[:sp+1]
    print(f"{decode(op)}\t({'|'.join(hex(x) for x in top)})")
```

```python
def calc_hash(x, mod):
    for _ in range(8):
        x = x * x % mod
    return x * x_original % mod
```

**Key insight:** Execution traces often expose the real algorithm faster than full VM reimplementation.
