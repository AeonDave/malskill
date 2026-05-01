# Ransomware Encryption Routine Analysis

Methodology for identifying cryptographic algorithms, locating key material, assessing implementation flaws, and extracting actionable intelligence from ransomware samples.

---

## Category 1: Hybrid Encryption Model

Modern ransomware universally applies hybrid encryption. Understanding the model tells you what to look for before touching a disassembler.

```
1. Random AES key + IV generated per file (or per session)
2. File content encrypted with AES (CBC/CTR/GCM) or ChaCha20/Salsa20
3. Per-file AES key encrypted with attacker's RSA or Curve25519 public key
4. Encrypted AES key appended / prepended to the ciphertext file
5. Attacker's private key → decrypts AES key → decrypts file
```

**Notable families and their schemes:**

| Family | Symmetric | Asymmetric | Notes |
|---|---|---|---|
| Rhysida | AES-256-CTR | RSA-4096 | Per-file key |
| Qilin.B | AES-256-CTR (AES-NI) | RSA | Falls back to ChaCha20 if no AES-NI |
| Medusa | AES-256 | RSA | |
| BlackCat/ALPHV | AES-128 / XChaCha20 | RSA | Cross-platform Rust; per-credential key |
| LockBit 3.0 | AES | ECDH | Hybrid ECDH + AES |

---

## Category 2: Cryptographic API Identification

### 2.1 Windows CryptoAPI (legacy)

```
CryptAcquireContext(A/W)  → Context init — look for PROV_RSA_AES or PROV_RSA_FULL
CryptGenKey               → Key generation — dwAlgId parameter reveals algorithm
CryptDeriveKey            → Key from password/hash
CryptGenRandom            → Random data (good PRNG, unless seeded with GetTickCount)
CryptImportKey            → Public key import from embedded blob
CryptExportKey            → Key export (check for RSA PUBLICKEYBLOB)
CryptEncrypt / CryptDecrypt → Actual en/decryption
CryptCreateHash / CryptHashData / CryptGetHashParam → Hashing (may derive key)
```

### 2.2 Windows CNG / BCrypt (modern)

```
BCryptOpenAlgorithmProvider → Algorithm init ("AES", "RSA", "CHACHA20_POLY1305", ...)
BCryptGenerateSymmetricKey  → Symmetric key setup
BCryptGenerateKeyPair       → Asymmetric key pair
BCryptImportKeyPair         → Load embedded public key
BCryptSetProperty           → Mode of operation ("ChainingModeGCM", "ChainingModeCBC", ...)
BCryptEncrypt / BCryptDecrypt → Encryption call
```

### 2.3 OpenSSL / libssl (cross-platform / Linux ransomware)

```
EVP_EncryptInit_ex   → Algorithm + key + IV setup (first arg = EVP_aes_256_cbc() etc.)
EVP_EncryptUpdate    → Encrypt data block
EVP_EncryptFinal_ex  → Flush padding
RSA_public_encrypt   → RSA PKCS1 / OAEP encrypt
AES_set_encrypt_key  → Low-level AES key schedule setup
```

### 2.4 File targeting API pattern

Ransomware drives file traversal with these Win32 APIs in sequence:

```
FindFirstFileW → FindNextFileW     (enumerate targets)
CreateFileW (GENERIC_READ)        (read original content)
ReadFile                          (load content)
CreateFileW (GENERIC_WRITE)       (write encrypted content)
WriteFile                         (store ciphertext)
MoveFileW / SetFileAttributesW    (rename with new extension)
DeleteFileW                       (optionally delete originals)
```

**Cross-reference these to find the encryption loop entry function.**

---

## Category 3: Cryptographic Constant Search

Before opening the decompiler, scan the binary for constants that reveal the algorithm:

```python
import re

CRYPTO_MARKERS = {
    # AES S-Box (first 8 bytes)
    bytes([0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5]): 'AES S-Box',
    # ChaCha20 / Salsa20 sigma constant
    b'expand 32-byte k': 'ChaCha20/Salsa20',
    b'expand 16-byte k': 'Salsa20 (128-bit key)',
    # RSA public key PEM / ASN.1
    b'-----BEGIN PUBLIC KEY-----': 'RSA PEM (PKCS#8)',
    b'-----BEGIN RSA PUBLIC KEY-----': 'RSA PEM (PKCS#1)',
    bytes([0x30, 0x82]): 'ASN.1 SEQUENCE (DER key/cert)',
    # Common IV / nonce patterns
    bytes([0] * 16): 'Possible zero IV (implementation flaw)',
}

with open('sample.exe', 'rb') as f:
    data = f.read()

for pattern, label in CRYPTO_MARKERS.items():
    off = data.find(pattern)
    if off != -1:
        print(f'[+] {label} at offset 0x{off:x}')
```

---

## Category 4: Implementation Flaw Checklist

These weaknesses can enable decryption without the attacker's private key. Check each during analysis.

| Flaw | How to detect | Exploitation potential |
|---|---|---|
| **Hardcoded symmetric key** | Key constant in .rodata; same AES key for all files | Decrypt all files with extracted key |
| **Weak PRNG seed** | `GetTickCount()`, `time()`, PID as seed before `srand`/`rand` | Brute-force seed over attack window |
| **IV reuse across files** | Same IV constant for every `BCryptEncrypt` call | AES-CTR/GCM IV reuse → keystream recovery |
| **ECB mode** | No IV argument; `BCryptSetProperty` with `ChainingModeECB` | Identical blocks, pattern leakage |
| **Session key (not per-file)** | Single key generated before file enumeration loop | One key decrypts all files |
| **Key left in memory** | Memory dump during encryption; no `SecureZeroMemory` | Volatile key recovery from crash dump/VM snapshot |
| **Truncated RSA input** | RSA key smaller than AES key material | Partial key recovery |
| **Flawed key derivation** | `SHA256(hostname)` or `MD5(volume_serial)` as key | Recompute from known system metadata |
| **Race condition** | Key visible in memory between generation and use | Memory timing attack via process handle |

---

## Category 5: Encrypted File Analysis

### 5.1 Appended key material detection

Ransomware typically appends the RSA-encrypted per-file key at the end. Detect it via entropy:

```python
import math
from collections import Counter

def entropy(data):
    freq = Counter(data)
    n = len(data)
    return -sum((c/n)*math.log2(c/n) for c in freq.values())

with open('encrypted_file', 'rb') as f:
    data = f.read()

# Common RSA ciphertext sizes: 256 (RSA-2048), 512 (RSA-4096)
for tail_size in [256, 512, 1024]:
    if len(data) > tail_size + 16:
        tail = data[-tail_size:]
        e = entropy(tail)
        if e > 7.5:
            print(f'Possible RSA-encrypted key ({tail_size}B) appended (entropy={e:.2f})')
```

### 5.2 Header analysis

```python
KNOWN_HEADERS = {
    b'PK':           'ZIP / Office Open XML',
    b'\x89PNG':      'PNG',
    b'\xff\xd8\xff': 'JPEG',
    b'%PDF':         'PDF',
    b'\xd0\xcf\x11\xe0': 'OLE (DOC/XLS)',
    b'RIFF':         'WAV/AVI',
    b'\x1f\x8b':     'gzip',
}

header = data[:16]
preserved = any(header.startswith(m) for m in KNOWN_HEADERS)
print('Original header preserved:', preserved)   # If True → only body encrypted
if not preserved:
    print('First 16 bytes:', header.hex())        # If randomised → whole file encrypted
```

---

## Category 6: Public Key Extraction

The attacker's embedded public key is an infrastructure pivot — it may link to other campaigns.

```python
import re, base64

with open('sample.exe', 'rb') as f:
    data = f.read()

# PEM-encoded RSA public key
pem = re.search(rb'-----BEGIN (?:RSA )?PUBLIC KEY-----(.+?)-----END (?:RSA )?PUBLIC KEY-----',
                data, re.DOTALL)
if pem:
    b64 = re.sub(rb'\s+', b'', pem.group(1))
    der = base64.b64decode(b64)
    print(f'[+] RSA public key DER ({len(der)} bytes) — submit to threat intel')

# DER-encoded key blob (0x30 0x82 ...)
for m in re.finditer(rb'\x30\x82(..)', data):
    length = int.from_bytes(m.group(1), 'big')
    candidate = data[m.start():m.start() + length + 4]
    if len(candidate) == length + 4:
        print(f'[+] ASN.1 DER blob at 0x{m.start():x} ({len(candidate)} bytes)')
```

---

## Category 7: Analysis Workflow

```
1. Triage:         strings + CRYPTO_MARKERS scan → identify algorithm family
2. Import scan:    CryptAcquireContext / BCryptOpenAlgorithmProvider → confirm API style
3. Find loop:      Cross-reference FindFirstFileW → locate file encryption entry function
4. Trace key gen:  Follow CryptGenKey / BCryptGenerateSymmetricKey backward → find PRNG
5. Check flaws:    Apply flaw checklist (§4)
6. Trace key wrap: Follow CryptImportKey / BCryptImportKeyPair → extract embedded pubkey
7. File analysis:  Entropy check on tail → confirm appended key scheme
8. Document:       Key size, mode, IV source, targeting pattern, extension list, ransom note path
```

**YARA skeleton for ransomware detection:**
```yara
rule Ransomware_HybridCrypto {
    meta:
        description = "Generic hybrid encryption ransomware indicator"
    strings:
        $bcrypt_aes    = "BCryptOpenAlgorithmProvider" ascii
        $bcrypt_enc    = "BCryptEncrypt" ascii
        $bcrypt_import = "BCryptImportKeyPair" ascii
        $find_files    = "FindFirstFileW" ascii
        $write_files   = "WriteFile" ascii
        $asn1_seq      = { 30 82 ?? ?? 30 ?? }    // RSA DER header
    condition:
        ($bcrypt_aes and $bcrypt_enc and $bcrypt_import) and
        ($find_files and $write_files)
}
```

---

## Common Pitfalls

1. **Mistaking per-session for per-file keying** — if the key generation call is outside the file loop, one key decrypts all files; this is a critical flaw.
2. **Ignoring the mode of operation** — AES-CBC with a static IV is trivially detectable; AES-CTR with IV reuse allows XOR ciphertext pairs; always trace `BCryptSetProperty` for chaining mode.
3. **Not checking `GetTickCount` / `time()` as PRNG seed** — some families still do this; cross-reference CryptGenRandom / rand() callers.
4. **Skipping the note dropper** — the ransom note creation function often writes a hardcoded string; it can reveal the campaign ID, Tor URL, and victim ID format.
5. **Focusing only on Windows APIs** — cross-platform samples (Go, Rust) may use bundled OpenSSL or `ring`/`aes` crates; check for ChaCha20 sigma constant and AES S-box in static data.
