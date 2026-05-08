# CTF Reverse - Analysis and Extraction Patterns

Patterns where the fastest path is to extract data, dump assets, hook a crypto boundary, or reconstruct offline artifacts.

## Table of Contents
- [Hidden Emulator Opcodes + LD_PRELOAD Key Extraction](#hidden-emulator-opcodes-ld_preload-key-extraction)
- [Spectre-RSB SPN Cipher - Static Parameter Extraction](#spectre-rsb-spn-cipher-static-parameter-extraction)
- [Image XOR Mask Recovery via Smoothness](#image-xor-mask-recovery-via-smoothness)
- [Shellcode in Data Section via mmap RWX](#shellcode-in-data-section-via-mmap-rwx)
- [Recursive execve Subtraction](#recursive-execve-subtraction)
- [Byte-at-a-Time Block Cipher Attack](#byte-at-a-time-block-cipher-attack)
- [Mathematical Convergence Bitmap](#mathematical-convergence-bitmap)
- [Windows PE XOR Bitmap Extraction + OCR](#windows-pe-xor-bitmap-extraction-ocr)
- [Two-Stage Loader: RC4 Gate + VM Constraints](#two-stage-loader-rc4-gate-vm-constraints)
- [GBA ROM VM Hash Inversion via Meet-in-the-Middle](#gba-rom-vm-hash-inversion-via-meet-in-the-middle)

## Hidden Emulator Opcodes + LD_PRELOAD Key Extraction

**Pattern:** Non-standard opcode `FxFF` triggers hidden crypto logic.

```c
#include <openssl/evp.h>
int EVP_DecryptInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *type,
                       ENGINE *impl, const unsigned char *key,
                       const unsigned char *iv) {
    for (int i = 0; i < 32; i++) printf("%02x", key[i]);
    printf("\n");
    return ((typeof(EVP_DecryptInit_ex)*)dlsym(RTLD_NEXT, "EVP_DecryptInit_ex"))
           (ctx, type, impl, key, iv);
}
```

```bash
gcc -shared -fPIC -ldl -lssl hook.c -o hook.so
LD_PRELOAD=./hook.so ./emulator rom.ch8
```

## Spectre-RSB SPN Cipher — Static Parameter Extraction

```python
import struct
sbox = [[0]*256 for _ in range(8)]
for i in range(8):
    for j in range(256):
        val = struct.unpack('<I', data[sbox_offset + (i*256+j)*4:...])[0]
        sbox[i][j] = 1 if val == 0x340 else 0
```

**Lesson:** Side-channel implementations still have to ship lookup tables.

## Image XOR Mask Recovery via Smoothness

```python
import numpy as np
from PIL import Image

img = np.array(Image.open('encrypted.png'))

def score_smoothness(region_pixels, mask, positions):
    decrypted = []
    for (x, y), pixel in zip(positions, region_pixels):
        key = (mask * x - y) & 0xFF
        decrypted.append(pixel ^ key)
    return -sum(abs(decrypted[i] - decrypted[i+1]) for i in range(len(decrypted)-1))
```

## Shellcode in Data Section via mmap RWX

Detect `mmap(..., PROT_EXEC, ...)`, lift the copied data blob, try common XOR/unpack transforms, then disassemble it offline.

## Recursive execve Subtraction

Find the base case of the self-recursing `execve` chain and solve the arithmetic backward instead of tracing every generation.

## Byte-at-a-Time Block Cipher Attack

If changing one input byte only affects one output byte, the transform has no useful diffusion. Recover the plaintext byte-by-byte by matching outputs.

## Mathematical Convergence Bitmap

```python
def newton_converges_to_one(px, py, max_iter=50, target_count=12):
    x, y = px, py
    count = 0
    for _ in range(max_iter):
        f_real = x**3 - 3*x*y**2 - 1.0
        f_imag = 3*x**2*y - y**3
        J_rr = 3.0 * (x**2 - y**2)
        J_ri = 6.0 * x * y
        det = J_rr**2 + J_ri**2
        if det < 1e-9:
            break
        x -= (f_real * J_rr + f_imag * J_ri) / det
        y -= (f_imag * J_rr - f_real * J_ri) / det
        count += 1
        if abs(x - 1.0) < 1e-6 and abs(y) < 1e-6:
            break
    return count == target_count
```

**Key insight:** The binary may be a classifier, not a checker.

## Windows PE XOR Bitmap Extraction + OCR

```python
import numpy as np
from PIL import Image

with open("binary.exe", "rb") as f:
    data = f.read()

blob_offset = 0xC3620
blob_size = 0x15F90
blob = np.frombuffer(data[blob_offset:blob_offset + blob_size], dtype=np.uint8)
expected = blob ^ 0xAA
img = expected.reshape(50, 450, 4)
channel = img[:,:, 0]
Image.fromarray(channel, "L").save("target.png")
```

## Two-Stage Loader: RC4 Gate + VM Constraints

```python
def rc4(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(b ^ s[(s[i] + s[j]) & 0xFF])
    return bytes(out)
```

**Key insight:** Stage 1 is often cheap crypto; stage 2 is where the real validator lives.

## GBA ROM VM Hash Inversion via Meet-in-the-Middle

```python
P = 0x100000001b3
CUP = 0x9e3779b185ebca87
MASK64 = (1 << 64) - 1

def fmix64(h):
    h ^= h >> 33; h = (h * 0xff51afd7ed558ccd) & MASK64
    h ^= h >> 33; h = (h * 0xc4ceb9fe1a85ec53) & MASK64
    h ^= h >> 33
    return h
```

```python
import string
TARGET = 0x73f3ebcbd9b4cd93
LENGTH = 6
SPLIT = 3
charset = [c for c in string.printable if 32 <= ord(c) < 127]
```

**Key insight:** Meet-in-the-middle turns impossible brute force into something comfortably scriptable.
