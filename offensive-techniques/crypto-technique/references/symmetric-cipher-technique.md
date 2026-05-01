# Symmetric Cipher Technique Reference

Methodology for attacking block ciphers (AES, DES, etc.), stream ciphers, and cipher mode weaknesses.

---

## Category 1: Block Cipher Mode Attacks

### 1.1 ECB Mode (Electronic Code Book)

**Preconditions:**
- Encryption uses ECB mode.
- Plaintext blocks are deterministic (same plaintext → same ciphertext).

**Why it's weak:**
ECB does not hide plaintext patterns. Identical plaintext blocks encrypt to identical ciphertext blocks.

**Attacks:**

**A. Pattern Leakage:**
```python
# Plaintext: "AAAA BBBB AAAA CCCC"
# Ciphertext: "1234 5678 1234 9ABC"
# You can see repeated pattern without knowing plaintext

# Use for: fingerprinting images, detecting repeated data
```

**B. Chosen-Plaintext Block Recovery:**
```python
# If you control plaintext, encrypt known blocks and build directory
# plaintext_block → ciphertext_block mapping

directory = {}
for i in range(256):
    for j in range(256):
        block = bytes([i, j, ...])  # 16-byte AES block
        ct = encrypt(block)
        directory[ct] = block

# Then, given ciphertext block, look it up in directory
# (If key unknown, brute force or dictionary attack)
```

**When to suspect:**
- Challenge explicitly says "ECB mode."
- Ciphertext blocks have visible repetition.
- Image encryption shows pattern (ECB penguin vulnerability).

**Tool**: `offensive-tools/cryptography/cyberchef/` (plaintext recovery via mode-specific decryption).

---

### 1.2 CBC Mode with Predictable or Reused IV

**Preconditions:**
- Encryption uses CBC mode.
- IV is predictable (derived from timestamp, counter, or hardcoded).
- Or: IV is reused across multiple encryptions.

**Why it's weak:**
CBC decryption: `m_i = D_k(c_i) XOR c_{i-1}` (or IV for first block).
If IV is known/reused, attacker can:
- Manipulate plaintext via IV bit-flipping.
- Detect plaintext similarity across encryptions.

**Attacks:**

**A. IV Bit-Flipping:**
```python
# If you want to flip bit j in plaintext block 0:
# m[0] = D_k(c[0]) XOR IV
# Flip IV bit j: m[0]' = D_k(c[0]) XOR (IV XOR 2^j)
# Result: m[0]' = m[0] XOR 2^j

# Example: change "is_admin: false" to "is_admin: true"
# by flipping specific bits in IV

iv_new = bytes([iv[i] ^ (1 << j) if i == 0 else iv[i] for i in range(16)])
ct_new = iv_new + c  # Prepend modified IV
# Send to decryption oracle; plaintext has flipped bits
```

**B. CBC Padding Oracle:**
See `prng-oracle-technique.md § 2.1`.

**When to suspect:**
- Challenge says "CBC mode used."
- IV is derived from predictable source (timestamp, counter).
- You can modify ciphertext and observe decryption result.

**Tool**: Custom Python or `offensive-tools/cryptography/cyberchef/`.

---

### 1.3 CTR Mode with Nonce Reuse

**Preconditions:**
- Encryption uses CTR (counter) mode.
- Nonce is reused: same (key, nonce) pair encrypts two different plaintexts.

**Why it's weak:**
CTR mode: `c_i = m_i XOR keystream_i`.
If keystream is reused:
```
c_1 = m_1 XOR ks
c_2 = m_2 XOR ks
c_1 XOR c_2 = m_1 XOR m_2
```
Given two ciphertexts, you get plaintext XOR. Often enough to recover both plaintexts.

**Operational:**

```python
# Given: c1, c2 (same key, same nonce)
# Recover: m1 XOR m2 = c1 XOR c2

xor_plain = bytes([c1[i] ^ c2[i] for i in range(len(c1))])

# Now, if you know/guess part of m1, recover corresponding part of m2
# Example: m1 starts with "flag{"
known = b"flag{"
m1_start = known
for i in range(len(known)):
    m2_byte = xor_plain[i] ^ m1_start[i]
    # m2[i] = m2_byte
```

**When to suspect:**
- Challenge uses CTR or stream cipher.
- Multiple ciphertexts with same key/nonce.
- Nonce is not random (hardcoded, incrementing, etc.).

**Tool**: Custom Python (XOR recovery is trivial).

---

### 1.4 GCM Mode Nonce Reuse (GHASH Break)

**Preconditions:**
- AES-GCM used with nonce reused (same key, same nonce).
- You have two ciphertexts with authentication tags.

**Why it's weak:**
GCM authentication key `H` is derived from key but not nonce. Reusing nonce leaks `H`.

**Operational:**

```python
# Given: (c1, tag1) and (c2, tag2) encrypted with same (key, nonce)
# Both ciphertexts same length

# GHASH(m, A) = sum(c_i * H^i) mod (2^128 + 7)
# If nonce reused, the same counter-mode stream is used for both

# Recovery of H:
# tag1 = GHASH(c1, A) XOR E_k(0)
# tag2 = GHASH(c2, A) XOR E_k(0)
# tag1 XOR tag2 = GHASH(c1 XOR c2, A)

# Use algorithm to recover H (complex; typically requires external tool)

# Once H known:
# Forge arbitrary ciphertexts and tags
ct_forge = <your_plaintext_encrypted_with_ctr>
tag_forge = ghash(ct_forge, A, H)
```

**When to suspect:**
- AES-GCM with nonce reuse (explicit or implicit).
- Challenge mentions authentication bypass.

**Tool**: External GCM-break tools or `offensive-tools/cryptography/cyberchef/`.

---

## Category 2: Stream Cipher Attacks

### 2.1 RC4 Bias and Biased Output

**Preconditions:**
- RC4 (or similar stream cipher) is used.
- Initial bytes or specific positions have statistical bias.
- Example: RC4 first byte is biased towards 0.

**Why it works:**
RC4 initialization is weak; output is not uniformly random. Exploit bias to recover key or plaintext.

**Operational:**

```python
# Collect many RC4 outputs (encrypt known plaintexts)
# Analyze byte distribution

from collections import Counter

outputs = [rc4(key, b"A"*256) for key in keys]  # Many keys
# Or: many messages with same key

# Check first byte bias
first_bytes = [out[0] for out in outputs]
counts = Counter(first_bytes)

# Plot histogram; if not uniform, bias exists
import matplotlib.pyplot as plt
plt.hist(first_bytes)
plt.show()

# Use bias to narrow key space via Bayesian update
# (Complex; typically requires specialized tool)
```

**When to suspect:**
- Challenge uses RC4 or obsolete stream cipher.
- Problem mentions "weak key schedule" or "biased output."

**Tool**: Specialized RC4 analysis tools or custom statistical analysis.

---

### 2.2 Linear Feedback Shift Register (LFSR) Keystream Recovery

**Preconditions:**
- LFSR-based stream cipher (older systems, some embedded devices).
- You have plaintext/ciphertext pairs or known plaintext.

**Why it works:**
LFSR is linear over GF(2). Given enough plaintext/ciphertext, solve linear system to recover feedback polynomial.

**Operational:**

```python
# Known plaintext attack on LFSR cipher
# Given: plaintext m, ciphertext c
# Keystream: ks = m XOR c

keystream = bytes([m[i] ^ c[i] for i in range(len(m))])

# Recover LFSR feedback polynomial (assuming n-stage LFSR)
from sage.all import *

# Convert to bits
ks_bits = ''.join(format(b, '08b') for b in keystream)

# Build linear system over GF(2)
F2 = GF(2)
n = 64  # Assume 64-bit LFSR

A = matrix(F2, [[int(ks_bits[i+j]) for j in range(n)] for i in range(len(ks_bits) - n)])
b = vector(F2, [int(b) for b in ks_bits[n:n + len(A)]])

# Solve for feedback polynomial
try:
    feedback = A.solve_right(b)
    print(f"Feedback polynomial: {feedback}")
except:
    print("No solution found; try different n")
```

**When to suspect:**
- Challenge uses LFSR or linear feedback.
- Known plaintext is available.

**Tool**: `offensive-tools/cryptography/sagemath/` for linear algebra.

---

## Category 3: Key Derivation and Weak Keys

### 3.1 Weak Key Derivation Function (KDF)

**Preconditions:**
- KDF uses weak hash (MD5, SHA1) or insufficient stretching.
- Plaintext password is guessable or leaked.

**Why it's weak:**
Weak KDF makes brute-force feasible. Test candidate passwords against derived key.

**Operational:**

```python
# Given: password, derived key
# Verify if password generates the key

from hashlib import sha1, pbkdf2_hmac

password = b"weak_password"
salt = b"salt_value"
iterations = 1000  # Too few

derived = pbkdf2_hmac('sha1', password, salt, iterations, dklen=32)

# Test candidate passwords
import itertools

charset = "abcdefghijklmnopqrstuvwxyz"
for length in range(1, 10):
    for candidate in itertools.product(charset, repeat=length):
        pwd_bytes = ''.join(candidate).encode()
        test_key = pbkdf2_hmac('sha1', pwd_bytes, salt, iterations, dklen=32)
        if test_key == derived:
            print(f"Found password: {''.join(candidate)}")
            break
```

**When to suspect:**
- Challenge mentions "password-based encryption."
- KDF uses weak hash or low iteration count.

**Tool**: `offensive-tools/cracking/hashcat/` or `offensive-tools/cracking/john/` for brute-force.

---

### 3.2 Known Weak Keys

Some ciphers (DES, Blowfish) have mathematically weak keys.

**DES weak keys:**
```python
# DES has 4 weak keys where encryption == decryption
# Also semi-weak keys where E_k1(m) == D_k2(m)

weak_keys_des = [
    0x0101010101010101,
    0xfefefefefefefefe,
    0xe0e0e0e0f1f1f1f1,
    0x1f1f1f1f0e0e0e0e,
]

# If key matches weak key, decryption is equivalent to re-encryption
```

**When to suspect:**
- Challenge uses DES or Blowfish.
- Key is guessable or constrained.

---

## Category 4: Reduced-Round Block Cipher Attacks

When a custom cipher uses a small number of rounds (1–3) and lacks a proper key schedule, meet-in-the-middle or byte-independent key recovery is feasible.

### 4.1 Byte-Independent Key Recovery (2-Round AES Variant)

**When this applies:**
- Custom cipher derived from AES with only 1–2 rounds.
- Key schedule is absent or trivial (key = two independent halves `k0 || k1`).
- Decryption structure: `AddRoundKey(k1) → InvMixCols → InvShiftRows → SubBytes → AddRoundKey(k0)`.

**Why it works:**
After undoing the global mixing operations (`InvMixCols`, `InvShiftRows`) on the ciphertext, each byte of the resulting intermediate state depends only on the corresponding byte of `k0` and `k1`. Two chosen plaintexts with known byte values constrain each key byte pair independently → enumerate `256×256 = 65536` candidates per byte position with 2 plaintexts.

**Attack workflow:**
1. Register/encrypt two chosen plaintexts `PT[0]` and `PT[1]` with known byte patterns.
2. Collect corresponding ciphertexts `CT[0]` and `CT[1]`.
3. Compute intermediate state: `CP[i] = InvShiftRows(InvMixCols(CT[i]))`.
4. For each byte index `j` and each pair `(b0, b1)` in `[0,255]×[0,255]`:
   - Check if `b1 == CP[i][j] XOR S_BOX[PT[i][j] XOR b0]` for both plaintexts.
   - If consistent for both, add `(b0, b1)` to `candidates[j]`.
5. Enumerate candidates depth-first; validate full 32-byte key candidate by decrypting a known block.

```python
from Crypto.Util.Padding import pad, unpad

# Two chosen plaintexts (16 bytes each, chosen to align with block boundary)
PT = [
    b'}' + b'\x0f' * 0x0f,   # Byte 0 = 0x7D, rest = 0x0F
    b'0}' + b'\x0e' * 0x0e,  # Byte 0 = 0x30, byte 1 = 0x7D, rest = 0x0E
]

# Get ciphertext blocks from oracle
CT = [get_ciphertext(pt)[-16:] for pt in PT]  # Take last block

# Undo global mixing steps on each ciphertext
CP = [matrix2bytes(inv_shift_rows(inv_mix_columns(bytes2matrix(ct)))) for ct in CT]

# Enumerate candidates per byte
candidates = {i: [] for i in range(16)}

for i in range(16):
    for b0 in range(256):
        for b1 in range(256):
            valid = True
            for pt, cp in zip(PT, CP):
                if b1 != cp[i] ^ S_BOX[pt[i] ^ b0]:
                    valid = False
                    break
            if valid:
                candidates[i].append((b0, b1))

# Candidates per byte should be ~1 (2 plaintexts reduce 65536 → 1)
# Traverse combinations and validate full key
def traverse(i, k0, k1_partial):
    if len(k0) == 16:
        k0 = bytes(k0)
        # Recover k1 from partial state (apply MixCols+ShiftRows to k1_partial)
        k1 = matrix2bytes(mix_columns(shift_rows(bytes2matrix(bytes(k1_partial)))))
        TEST_KEY = k0 + k1
        if PT[0] == decrypt(TEST_KEY, CT[0]):
            print(f"Key found: {TEST_KEY.hex()}")
        return
    for b0, b1 in candidates[i]:
        traverse(i + 1, k0 + [b0], k1_partial + [b1])

traverse(0, [], [])
```

**When to suspect:**
- Custom cipher labeled as "AES-based" or "AES-derived" with fewer rounds.
- Key is described as 32 bytes split into two 16-byte halves.
- No key schedule function visible in source, or k0/k1 used directly.

---

### 4.2 Meet-in-the-Middle on Reduced Round Count

**When this applies:**
- Double-DES or double-block-cipher (two passes through same cipher with independent keys).
- Cipher has 2 independent keys; brute-forcing both would be 2^(2k) but MITM reduces to 2^k.

**Why it works:**
Encrypt from plaintext side with all possible k1, decrypt from ciphertext side with all possible k2. Intersection gives (k1, k2) pairs.

```python
# Offline MITM for double cipher
# Encrypt: CT = E_{k2}(E_{k1}(PT))
# Recover k1, k2 given (PT, CT)

from tqdm import tqdm

# Step 1: Build dictionary from plaintext side
forward_table = {}
for k1 in range(key_space):
    mid = encrypt_single(k1, PT)
    if mid not in forward_table:
        forward_table[mid] = []
    forward_table[mid].append(k1)

# Step 2: Decrypt from ciphertext side and look up
for k2 in tqdm(range(key_space)):
    mid = decrypt_single(k2, CT)
    if mid in forward_table:
        for k1 in forward_table[mid]:
            # Verify with second known plaintext-ciphertext pair
            if encrypt_single(k2, encrypt_single(k1, PT2)) == CT2:
                print(f"Keys found: k1={k1}, k2={k2}")
```

---

## Category 5: Classical Polyalphabetic Cipher Attacks

Classical ciphers (Vigenère, Polybius square, rotor-based) are broken by exploiting key repetition and letter frequency. The same principle applies to alphanumeric variants and custom alphabets.

### 5.1 Vigenère / Polybius Square — Frequency Analysis Attack

**What this looks like (Optimistic-style):**
- A Polybius square (N×N grid, e.g., 6×6) is built from a keyword that reorders the alphabet.
- Encryption: `c_i = offset(pt_char_i) + offset(key_char_{i mod L})` where `offset()` maps position in the grid to a numeric value.
- Decryption is linear: subtract key character's offset.
- Key of length L repeats: every L-th character shares the same key character.

**Attack:** frequency analysis independently per key position.

```python
import string

# Alphabet and grid setup
ALPH = string.ascii_uppercase + string.digits  # 36 chars
Z = 6   # Grid dimension (6×6)
L = 36  # Key length (must be determined via Kasiski/IOC first)

KEYWORD = <inferred_or_given>

def construct_square(keyword):
    """Build Polybius square from keyword (keyword chars come first)."""
    sqr = ALPH
    for c in keyword:
        sqr = sqr.replace(c, '')
    sqr = keyword + sqr
    return [list(sqr[i:i+Z]) for i in range(0, len(sqr), Z)]

s = construct_square(KEYWORD)
OFFSETS   = {s[i][j]: (i+1)*10+(j+1) for j in range(Z) for i in range(Z)}
REV_OFFSETS = {int(v): k for k, v in OFFSETS.items()}

def english_score(text):
    """Frequency score: higher = more English-like."""
    return sum(text.count(ch) for ch in 'ETAOINSHRDLU')

def recover_key_char(group):
    """For one key position: try all key chars, score plaintext, pick best."""
    results = {}
    for k in ALPH:
        key_off = OFFSETS[k]
        plaintext_candidate = []
        for c in group:
            p = c - key_off
            if p in REV_OFFSETS:
                plaintext_candidate.append(REV_OFFSETS[p])
        results[k] = english_score(''.join(plaintext_candidate))
    return max(results, key=results.get)

# Recover each key character
CIPHERTEXT_NUMS = [...]  # Numeric ciphertext values
KEY = ''.join(recover_key_char(CIPHERTEXT_NUMS[g::L]) for g in range(L))
print(f"Recovered key: {KEY}")

# Decrypt full plaintext
def decrypt(key, ciphertext):
    pt = ''
    for i, c in enumerate(ciphertext):
        key_off = OFFSETS[key[i % len(key)]]
        pt += REV_OFFSETS[abs(c - key_off)]
    return pt

PLAINTEXT = decrypt(KEY, CIPHERTEXT_NUMS)
print(f"Plaintext: {PLAINTEXT}")
```

### 5.2 Determining Key Length (Kasiski / Index of Coincidence)

Before frequency analysis, you need to know the key length L.

```python
def index_of_coincidence(text):
    """Higher IC → more repetition → likely correct key length."""
    n = len(text)
    counts = Counter(text)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))

# Try key lengths 2..50
for L_test in range(2, 50):
    # Group ciphertext by position mod L_test
    columns = [''.join(ciphertext[i::L_test]) for i in range(L_test)]
    avg_ic = sum(index_of_coincidence(col) for col in columns) / L_test
    print(f"L={L_test}: avg IC = {avg_ic:.4f}")
# English text IC ≈ 0.067; random text IC ≈ 0.038
# Key length where IC is highest = likely correct L
```

### 5.3 Recovering Keyword from Polybius Square Construction

If the grid keyword is unknown, treat it as a short additional Vigenère key and brute-force or infer from context.

```python
# If keyword length is small (e.g., 4-10 chars), enumerate:
from itertools import product

for keyword_len in range(4, 12):
    for keyword in (some_wordlist_of_len(keyword_len)):
        s = construct_square(keyword)
        # Attempt frequency analysis attack...
        # Score: count how many ETAOINSHRDLU chars appear in decrypted plaintext
```

**When to suspect:**
- Ciphertext is numeric (integers, not hex bytes).
- Problem mentions "grid", "square", "keyword cipher", or "polybius".
- Ciphertext length is a multiple of the key length.
- All numeric values cluster in a narrow range (e.g., 11–66 for a 6×6 grid).

---

## Decision Tree

```
START: You have ciphertext and suspect cipher mode weakness.

Q1: What cipher mode?
  ECB → Pattern leakage attack (§1.1)
  CBC → Padding oracle or IV bit-flipping (§1.2)
  CTR → Nonce reuse / keystream XOR (§1.3)
  GCM → Nonce reuse and GHASH break (§1.4)
  Stream cipher → Check for bias or linearity (§2.1, §2.2)

Q2: Can you control plaintext (encryption oracle)?
  YES → Use chosen-plaintext to build dictionary or fingerprint
  NO → Continue with known ciphertext attacks

Q3: Can you access decryption oracle?
  YES → Padding oracle or similar (see prng-oracle-technique.md)
  NO → Offline analysis only

Q4: Is KDF weak?
  YES → Brute-force password (§3.1)
  NO → Assume strong key derivation

Q5: Is this a custom reduced-round block cipher?
  Has 1–2 rounds and no real key schedule?
    YES → Byte-independent chosen-plaintext key recovery (§4.1)
  Is it double-encryption with two independent keys?
    YES → Meet-in-the-middle offline (§4.2)

Q6: Is ciphertext numeric or is the cipher described as a grid/keyword cipher?
  YES → Polybius square / Vigenère → frequency analysis per key position (§5.1)
  NO → Standard cipher; use mode-specific attacks above

Q7: Does the MAC or signature use `hash(secret || message)`?
  YES → Hash length extension attack (§6.1)
  NO → Continue

Q8: Does the protocol compress then encrypt?
  YES → Compression oracle: observe ciphertext length to recover plaintext byte-by-byte (§7.1)
  NO → Continue

Q9: Is the keystream generated by an LFSR or bit-based shift register?
  YES → Berlekamp-Massey with known plaintext (§8.1); check for correlation attacks (§8.2)
  NO → Not LFSR-based
```

---

## Category 6: Hash Length Extension

### 6.1 Hash Length Extension Attack

**Pattern:** A server MACs data as `tag = H(secret || message)` using a Merkle-Damgard hash (MD5, SHA-1, SHA-256). Given `tag` and `message`, an attacker can forge a valid tag for `message || pad || extension` without knowing `secret`.

**Why it works:**
Merkle-Damgard resumes from any intermediate hash state. The `tag` encodes the state after processing `secret || message`. Appending `extension` and continuing hashing produces a valid tag for the extended message.

**Prerequisites:**
- MAC is constructed as `H(secret || data)` (not HMAC).
- Hash algorithm is MD5, SHA-1, or SHA-256 (all Merkle-Damgard).
- You know the hash value and original data (secret length may be guessed).

**Operational — hashpumpy (Python):**

```python
import hashpumpy  # pip install hashpumpy

# Inputs
orig_hash = "aabbccddeeff..."  # Hex string
orig_data = b"amount=100"      # Original message (without secret)
append_data = b"&admin=true"   # Data to append
secret_len = 8                 # Byte length of unknown secret (try 1–32)

# Compute forged hash and data
forged_hash, forged_data = hashpumpy.hashpump(
    orig_hash,
    orig_data,
    append_data,
    secret_len
)
# forged_data includes original + Merkle-Damgard padding + extension
# Submit forged_data + forged_hash to the server

print(f"Forged hash: {forged_hash}")
print(f"Forged data: {forged_data.hex()}")
```

**Command-line (hashpump tool):**
```bash
hashpump \
  --keylength 8 \
  --signature aabbccddeeff... \
  --data "amount=100" \
  --additional "&admin=true"
```

**Brute-force secret length:**
```python
for secret_len in range(1, 33):
    forged_hash, forged_data = hashpumpy.hashpump(
        orig_hash, orig_data, append_data, secret_len
    )
    resp = send_to_server(forged_data, forged_hash)
    if resp.status == 200:
        print(f"Valid! Secret length = {secret_len}")
        break
```

**Immune constructions:**
- HMAC: uses an inner and outer key application, not simple prefix.
- SHA-3 (Keccak): sponge construction, not Merkle-Damgard.
- SHA-512/256, SHA-512/224: truncated variants are immune to length extension.

**When to suspect:**
- API endpoints verify `tag = H(key || request_params)`.
- MAC implementation is visible in source: `md5(SECRET + user_input)`.
- Server accepts data with appended parameters if the tag is "valid".

---

## Category 7: Compression Oracle (CRIME-style)

### 7.1 Length-Based Plaintext Recovery

**Pattern:** Server compresses request data before encrypting. An attacker who can inject chosen prefixes into the plaintext and observe ciphertext length can recover secret bytes one at a time: the correct byte makes the compressed+encrypted output shorter.

**Why it works:**
LZ-family compression (DEFLATE, LZW, zlib) replaces repeated substrings with references. If the injected prefix shares a substring with the secret, the compressed output is shorter.

**Preconditions:**
- Server compresses before encrypting (e.g., TLS CRIME, HTTPS with `Content-Encoding: deflate`).
- Attacker can inject chosen data into the same compression context as the secret.
- Attacker can observe ciphertext length (not content).

**Operational:**

```python
import string

def oracle(plaintext: bytes) -> int:
    """Send plaintext to server; return observed ciphertext length."""
    ...  # Implementation-specific

def recover_secret(known_prefix: bytes, secret_position: int, candidates: str) -> bytes:
    """Recover one byte of secret at secret_position."""
    secret = bytearray()

    for pos in range(secret_position, secret_position + 128):
        base_len = oracle(known_prefix + b"A" * 8)  # Neutral padding
        best_char = None
        best_len = float("inf")

        for c in candidates:
            probe = known_prefix + secret + c.encode()
            length = oracle(probe)
            if length < best_len:
                best_len = length
                best_char = c

        # Verify: shorter must be significantly better to be confident
        if best_len < base_len:
            secret.append(ord(best_char))
            print(f"Byte {pos}: {best_char!r} (len={best_len})")
        else:
            print(f"Recovery stalled at position {pos}")
            break

    return bytes(secret)

# Usage
recovered = recover_secret(b"Cookie: session=", 0, string.printable)
```

**Important constraints:**
- Block-cipher padding can quantize lengths to block boundaries. Pad your probe to minimize quantization noise.
- CBC mode may round up to 16-byte blocks; adjust candidate evaluation accordingly.
- Stream ciphers (RC4, ChaCha20) have exact lengths — directly readable.

**When to suspect:**
- Protocol description says data is compressed before encryption.
- Ciphertext length varies based on how much overlap exists between request and response.
- TLS 1.2 or earlier with `DEFLATE` content encoding and attacker-controlled request injection.

---

## Category 8: LFSR and Berlekamp-Massey

### 8.1 Berlekamp-Massey: Recover Feedback Polynomial from Keystream

**Pattern:** A keystream is generated by an LFSR of unknown degree `L`. With at least `2L` bits of known keystream (from known-plaintext XOR with ciphertext), Berlekamp-Massey recovers the minimal feedback polynomial.

```python
from sage.all import berlekamp_massey, GF

# Recover keystream bits via known-plaintext XOR
keystream_bits = [ct_bit ^ pt_bit for ct_bit, pt_bit in zip(ciphertext_bits, plaintext_bits)]

# Apply Berlekamp-Massey
seq = [GF(2)(b) for b in keystream_bits]
feedback_poly = berlekamp_massey(seq)

L = feedback_poly.degree()            # LFSR length
print(f"Minimal LFSR length: {L}")
print(f"Feedback polynomial: {feedback_poly}")

# Recover initial state
# The first L bits of keystream are the initial LFSR state (Fibonacci form)
initial_state = keystream_bits[:L]

# Predict future keystream bits
state = list(initial_state)
coeffs = [int(c) for c in feedback_poly.list()[:-1]]  # Exclude leading 1

predicted = []
for _ in range(1024):
    new_bit = int(sum(coeffs[i] * state[-(i+1)] for i in range(len(coeffs))) % 2)
    predicted.append(new_bit)
    state.append(new_bit)
```

**When to suspect:**
- Keystream produces a periodic or patterned sequence.
- Cipher is described as "shift register-based" or "stream cipher."
- Known-plaintext segment of any length is available.

---

### 8.2 Combined LFSR Correlation Attack

**Pattern:** A keystream is the XOR of several short LFSRs. Each LFSR is weakly correlated with the output (probability > 0.5). Brute-force each LFSR independently.

**Why it works:**
If `P(output_bit == LFSR_i bit) = p > 0.5`, maximum-likelihood decoding over enough bits identifies the initial state of LFSR_i in `O(2^L_i)` time rather than the joint `O(2^(L_1 + L_2 + ...))`.

```python
from sage.all import GF

def lfsr_output(initial: list, feedback: list, n: int) -> list:
    """Generate n bits from an LFSR defined by initial state and feedback taps."""
    state = list(initial)
    out = []
    for _ in range(n):
        bit = sum(state[i] for i in feedback) % 2
        out.append(state[-1])
        state = [bit] + state[:-1]
    return out

def correlation_score(candidate_bits, observed_keystream):
    """Fraction of matching bits (should be > 0.5 for correct LFSR)."""
    matches = sum(a == b for a, b in zip(candidate_bits, observed_keystream))
    return matches / len(observed_keystream)

L = 16          # LFSR degree to brute-force
feedback = [0, 2, 5, 15]  # Tap positions from known feedback polynomial

best_score = 0
best_state = None

for seed in range(2**L):
    initial = [(seed >> i) & 1 for i in range(L)]
    candidate = lfsr_output(initial, feedback, len(observed_keystream))
    score = correlation_score(candidate, observed_keystream)
    if score > best_score:
        best_score = score
        best_state = initial

print(f"Best LFSR initial state: {best_state} (correlation: {best_score:.4f})")
```

**Preconditions:**
- Known-plaintext to recover keystream.
- Cipher is a combination (XOR) of independent LFSRs.
- Individual LFSR lengths are small enough for brute force (L ≤ 26 practical).
- Feedback polynomial known from §8.1 or from cipher specification.

---

## Common Pitfalls

1. **ECB assumption**: Not all blocks of same plaintext encrypt identically if iv/counter differs.
2. **CTR nonce scope**: Some systems call "nonce" what others call "IV." Confirm what's being reused.
3. **Padding oracle signal-to-noise**: Real oracle timings are noisy. Collect many samples before committing.
4. **Polybius offset direction**: Some implementations add offsets, others XOR or concatenate. Inspect the encryption function before building the inverse.
5. **Reduced-round key recovery per-byte assumption**: Only valid when InvMixCols+InvShiftRows are applied to the full ciphertext first. If the intermediate step crosses byte boundaries, per-byte independence breaks.
4. **Key schedule**: Some ciphers (DES) have special properties; check if key is weak.

