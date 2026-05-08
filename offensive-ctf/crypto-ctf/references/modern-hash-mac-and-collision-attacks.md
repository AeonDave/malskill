# Preserved source: modern-ciphers.md

This reference is a debrandized preservation copy of imported CTF-skill material. It keeps technical techniques, code patterns, workflows, and decision cues while removing challenge, platform, and competition branding. Treat it as a domain knowledge bank loaded after the concise SKILL.md routing guidance.

# CTF Crypto - Modern Hash, MAC, and Collision Attacks

## Use This Reference When

- The artifact contains a digest, checksum, MAC, signature-over-hash, hash chain, truncated hash, CRC, or custom linear hash construction.
- The likely break is length extension, collision generation, multicollision composition, CRC linearity, XOR aggregation, leaked intermediate state, or a flawed HMAC-like design.
- The validation signal is a matching digest/MAC, accepted forged message, recovered secret component, or collision pair that passes the verifier.

## External Anchors

- RFC 2104 defines HMAC behavior, including the rule that keys longer than the hash block size are first hashed.
- The 2020 "SHA-1 is a Shambles" result is the practical chosen-prefix collision baseline for SHA-1 collision workflows.

## Table of Contents
- [Weak Hash Functions / GF(2) Gaussian Elimination](#weak-hash-functions-gf2-gaussian-elimination)
- [Custom Linear MAC Forgery](#custom-linear-mac-forgery)
- [Birthday Attack / Meet-in-the-Middle](#birthday-attack-meet-in-the-middle)
- [CRC32 Collision-Based Signature Forgery](#crc32-collision-based-signature-forgery)
- [SHA-1 Chosen-Prefix Collision for PDF Signature Forgery](#sha-1-chosen-prefix-collision-for-pdf-signature-forgery)
- [Hash Chain Preimage Authentication Bypass](#hash-chain-preimage-authentication-bypass)
- [Hash Length Extension Attack](#hash-length-extension-attack)
- [Hash Function Time Reversal via Cycle Detection](#hash-function-time-reversal-via-cycle-detection)
- [HMAC-CRC Linearity Attack](#hmac-crc-linearity-attack)
- [MD5 Multi-Collision via Fastcol](#md5-multi-collision-via-fastcol)
- [SHA-1 Length Extension Plus AES-CBC Cookie Forgery](#sha-1-length-extension-plus-aes-cbc-cookie-forgery)
- [Custom Hash State Reversal via Known Intermediates](#custom-hash-state-reversal-via-known-intermediates)
- [CRC32 Brute-Force for Small Payloads](#crc32-brute-force-for-small-payloads)
- [SHA-256 Basis Attack for XOR-Aggregate Hash Bypass](#sha-256-basis-attack-for-xor-aggregate-hash-bypass)
- [Custom MAC Forgery via XOR Block Cancellation with Key Rotation](#custom-mac-forgery-via-xor-block-cancellation-with-key-rotation)
- [Bit-by-Bit HMAC Key Recovery via XOR Plus Addition Arithmetic](#bit-by-bit-hmac-key-recovery-via-xor-plus-addition-arithmetic)
- [SHA-1 Length Extension with UTF-8 High-Byte Bypass](#sha-1-length-extension-with-utf-8-high-byte-bypass)


-

## Weak Hash Functions / GF(2) Gaussian Elimination

Linear permutations (only XOR, rotations) are algebraically attackable. Build transformation matrix and solve over GF(2).

```python
import numpy as np

def solve_gf2(A, b):
    """Solve Ax = b over GF(2)."""
    m, n = A.shape
    Aug = np.hstack([A, b.reshape(-1, 1)]) % 2
    pivot_cols, row = [], 0
    for col in range(n):
        pivot = next((r for r in range(row, m) if Aug[r, col]), None)
        if pivot is None: continue
        Aug[[row, pivot]] = Aug[[pivot, row]]
        for r in range(m):
            if r != row and Aug[r, col]: Aug[r] = (Aug[r] + Aug[row]) % 2
        pivot_cols.append((row, col)); row += 1
    if any(Aug[r, -1] for r in range(row, m)): return None
    x = np.zeros(n, dtype=np.uint8)
    for r, c in reversed(pivot_cols):
        x[c] = Aug[r, -1] ^ sum(Aug[r, c2] * x[c2] for c2 in range(c+1, n)) % 2
    return x
```

**Key insight:** Hash functions built from only XOR and rotations (no S-boxes or modular addition) are linear over GF(2). Build the transformation as a binary matrix, then invert it with Gaussian elimination to recover the preimage directly. This breaks any "custom hash" that avoids non-linear operations.

-

## Custom Linear MAC Forgery

**Pattern:** Server signs paste IDs with a custom SHA-256-based construction. The signature is linear in three 8-byte secret blocks derived from the key.

**Structure:** For each 8-byte output block `i`:
- `selector = SHA256(id)[i*8] % 3` → chooses which secret block to use
- `out[i] = hash_block[i] XOR secret[selector] XOR chain[i-1]`

**Recovery:** Create ~10 pastes to collect `(id, sig)` pairs. Each pair reveals `secret[selector]` for 4 selectors. With ~4-5 pairs, all 3 secret blocks are recovered. Then forge for target ID.

**Key insight:** Linearity in custom crypto constructions (XOR-based signing) makes them trivially forgeable. Always check if the MAC has the property: knowing the secret components lets you compute valid signatures for arbitrary inputs.

-

## Birthday Attack / Meet-in-the-Middle

**Pattern:** Find collisions in hash functions or MACs using the birthday paradox. With an n-bit hash, expect a collision after ~2^(n/2) random inputs.

```python
import hashlib, os

def birthday_collision(hash_fn, output_bits, prefix=b''):
    """Find two inputs with the same truncated hash."""
    target_bytes = output_bits // 8
    seen = {}

    while True:
        msg = prefix + os.urandom(16)
        h = hash_fn(msg).digest()[:target_bytes]
        if h in seen:
            return seen[h], msg  # Collision found!
        seen[h] = msg

# Example: find collision on first 4 bytes of SHA-256 (~65536 attempts)
msg1, msg2 = birthday_collision(hashlib.sha256, 32)
```

**Meet-in-the-Middle (2DES, double encryption):**
```python
def meet_in_the_middle(encrypt_fn, decrypt_fn, plaintext, ciphertext, keyspace):
    """Break double encryption E(k2, E(k1, pt)) = ct."""
    # Forward: encrypt plaintext with all possible k1
    forward = {}
    for k1 in keyspace:
        intermediate = encrypt_fn(k1, plaintext)
        forward[intermediate] = k1

    # Backward: decrypt ciphertext with all possible k2
    for k2 in keyspace:
        intermediate = decrypt_fn(k2, ciphertext)
        if intermediate in forward:
            return forward[intermediate], k2  # Found k1, k2!
```

**Key insight:** Birthday attack: n-bit hash needs ~2^(n/2) queries for 50% collision probability. 32-bit hash -> ~65K, 64-bit -> ~4 billion. Meet-in-the-middle reduces double encryption from O(2^(2k)) to O(2^k) time + O(2^k) space — this is why 2DES provides only 1 extra bit of security over DES.

-

## CRC32 Collision-Based Signature Forgery

**Pattern:** CRC32 is linear — appending 4 carefully chosen bytes to any message produces a target CRC32 value, enabling signature forgery without knowing the secret key.

**Key insight:** `CRC32(msg || secret)` is not a secure MAC. Given any signed response `(msg, sig)`, compute 4 suffix bytes that force `CRC32(forged_msg || suffix || secret) == target_sig`. The linearity of CRC32 means the suffix computation is deterministic and instant.

```python
import struct, binascii

def crc32_forge(data, target_crc):
    """Append 4 bytes to data so CRC32(data + suffix) == target_crc"""
    current = binascii.crc32(data) & 0xFFFFFFFF
    # CRC32 polynomial table lookup to find suffix bytes
    # that transform current CRC into target_crc
    suffix = b''
    crc = target_crc ^ 0xFFFFFFFF
    for _ in range(4):
        byte = (crc & 0xFF)
        crc = (crc >> 8)
        suffix = bytes([byte]) + suffix
    return data + suffix  # Simplified — full implementation requires polynomial division
```

**When to use:** Any protocol using CRC32 as a message authentication code (MAC). CRC32 is a checksum, not a cryptographic hash — it provides no integrity guarantees against adversarial modification.

-

## SHA-1 Chosen-Prefix Collision for PDF Signature Forgery

**Pattern:** Server extracts commands from an uploaded PDF via OCR, then signs the OCR'd byte-string as `sha1(data)` and attaches the signature. Use a shattered-style SHA-1 chosen-prefix collision to produce two PDFs that OCR to different commands but share the same SHA-1 digest.

**Exploit workflow:**
1. Build PDF A that OCR's to a benign command (no `EXECUTE`) and PDF B that OCR's to `EXECUTE <attacker command>`.
2. Pad both with shattered-style suffix data so `sha1(A) == sha1(B)`.
3. Submit A to obtain a valid signature for the shared digest.
4. Replay that signature on B — the server verifies the SHA-1 matches and executes the attacker command.

```bash
# Build the two colliding PDFs (cpc = chosen-prefix collision tool)./cpc prefix_A prefix_B collision_A.pdf collision_B.pdf
sha1sum collision_A.pdf collision_B.pdf  # identical
# Upload A, capture signature, replay on B
```

**Key insight:** When a protocol signs a message as `sign(sha1(M))` instead of `sign(M)` directly, any SHA-1 collision becomes a signature forgery. Chosen-prefix collisions are practical (cpc/shattered toolkit) — the signer only inspects the digest, never the second preimage.

-

## Hash Chain Preimage Authentication Bypass

**Pattern:** Server authenticates the Nth challenge by asking for `hash^(N-1)(seed)` given `hash^N(seed)`. The seed is derivable from public user data (e.g., `md5(username)`), so any attacker can precompute the whole chain from the start and answer any step.

**Exploit:**
```python
import hashlib

def H(x): return hashlib.md5(x).digest()

seed = H(username.encode())        # public-derived seed
chain = [seed]
for _ in range(TARGET_N + 1):
    chain.append(H(chain[-1]))

# Server sends chain[N]; answer with chain[N-1]
```

**Key insight:** Hash chains are only one-way if the seed is secret. If the seed can be reconstructed from public inputs (username, challenge ID, timestamp), the entire chain is computable forward, and answering "give me the previous hash" is trivial. Treat the seed like a key.

-

## Hash Length Extension Attack

**Pattern:** Server computes `hash(SECRET || user_data)` using MD5, SHA-1, or SHA-256 (Merkle-Damgard constructions). Given a valid hash and the original data, extend it with arbitrary appended data and compute a valid hash — without knowing the secret.

```bash
# Using HashPump (install: apt install hashpump)
hashpump -keylength 8 \
  -signature 'ef16c2bffbcf0b7567217f292f9c2a9a50885e01e002fa34db34c0bb916ed5c3' \
  -data 'original_data' \
  -additional ';admin=true'
# Outputs: new_signature and new_data (with padding bytes)
```

```python
# Python: hashpumpy
import hashpumpy
new_hash, new_data = hashpumpy.hashpump(
    original_hash, original_data, append_data, secret_length
)
```

**Key insight:** Merkle-Damgard hashes (MD5, SHA-1, SHA-256) process data in blocks, and the hash output IS the internal state. Given `H(secret || msg)`, you can compute `H(secret || msg || padding || extension)` without knowing `secret` — just initialize the hash state from the known output and continue hashing. Only HMAC (`H(K XOR opad || H(K XOR ipad || msg))`) is immune. If the secret length is unknown, try lengths 1-32.

The same primitive also appears in web authentication tokens when the verifier computes a raw Merkle-Damgard hash over `secret || data` instead of HMAC.

-

## Hash Function Time Reversal via Cycle Detection

When a system uses iterated hashing as a "time" function (`state_t = H(state_{t-1})`), reverse time by exploiting the finite cycle structure:

1. **Detect cycle:** Use Floyd's tortoise-and-hare or Brent's algorithm to find cycle length L
2. **Compute backward steps:** To go from time T to earlier time T_goal: iterate forward `(L - (T - T_goal)) % L` steps

```python
import hashlib

def hash_step(state):
    return hashlib.md5(state).digest()[:8]  # Truncated hash

def find_cycle(start):
    """Brent's cycle detection: returns (cycle_length, start_of_cycle)"""
    power = lam = 1
    tortoise = start
    hare = hash_step(start)
    while tortoise != hare:
        if power == lam:
            tortoise = hare
            power *= 2
            lam = 0
        hare = hash_step(hare)
        lam += 1
    # lam = cycle length; find cycle start
    tortoise = hare = start
    for _ in range(lam):
        hare = hash_step(hare)
    mu = 0
    while tortoise != hare:
        tortoise = hash_step(tortoise)
        hare = hash_step(hare)
        mu += 1
    return lam, mu  # cycle_length, cycle_start_offset

# Reverse from T_known to T_goal
cycle_len, _ = find_cycle(known_state)
forward_steps = (cycle_len - (t_known - t_goal)) % cycle_len
state = known_state
for _ in range(forward_steps):
    state = hash_step(state)
# state is now the value at t_goal
```

**Key insight:** For truncated hashes (e.g., MD5 -> 64 bits), the expected cycle length is ~2^32, making cycle detection feasible. Going "backward" N steps is equivalent to going forward (cycle_length - N) steps. Assumes the target state is within the main cycle, not on a tail.

-

## HMAC-CRC Linearity Attack

**Pattern:** HMAC constructed with CRC as the hash function is completely broken because CRC is linear over GF(2). The key is directly recoverable from a single message-MAC pair via polynomial arithmetic over GF(2^64).

```python
# CRC is linear: CRC(a XOR b) = CRC(a) XOR CRC(b)
# HMAC-CRC(key, msg) = CRC(key_opad || CRC(key_ipad || msg))
# Rewrite as polynomial in GF(2): K = known_terms * inverse(x^(128+M) + x^128) mod CRC_POLY
```

**Key insight:** CRC's linearity over GF(2) means HMAC-CRC provides zero security. Always verify the underlying hash function is non-linear before trusting HMAC.

-

## MD5 Multi-Collision via Fastcol

**Pattern:** Generate 2^k files with identical MD5 hashes by chaining `fastcol` (Marc Stevens' tool). Each run produces two suffixes (A, B) that when appended yield the same MD5. Chain 3 runs to produce 8 collisions:

```text
[prefix][suffix1A][suffix2A][suffix3A]  \
[prefix][suffix1A][suffix2A][suffix3B]   |
[prefix][suffix1A][suffix2B][suffix3A]   |- all have same MD5
[prefix][suffix1A][suffix2B][suffix3B]   |
[prefix][suffix1B][suffix2A][suffix3A]   |
[prefix][suffix1B][suffix2B][suffix3B]  /
```

```bash
# Install: git clone https://github.com/cr-marcstevens/hashclash
# Generate one collision pair (~minutes on modern CPU):./fastcol -o suffix1A.bin suffix1B.bin < prefix.bin
# Chain: append suffix1A to prefix, run fastcol again for suffix2A/2B, etc.
```

**Key insight:** MD5 collision generation is practical with `fastcol` (~minutes per pair). Because MD5 uses Merkle-Damgard construction, collisions compose: if `H(A||X) == H(A||Y)`, then `H(A||X||Z) == H(A||Y||Z)` for any suffix Z. Chaining k collision pairs produces 2^k files with identical MD5. For CRC32 collisions, append bytes after PNG IEND chunk (parsers ignore trailing data) and brute-force the 4-byte CRC adjustment.

-

## SHA-1 Length Extension Plus AES-CBC Cookie Forgery

**Pattern:** Cookie stores `user = iv || AES-CBC(key, plaintext)` plus a separate `signature = SHA1(secret || decrypt(ct))` tag. The session cookie leaks the AES key (e.g. trailing 32 bytes of a base64 session blob). To forge `UID 0`, length-extend the signature with `\nUID 0\n`, decrypt the current ciphertext to learn the plaintext, append hashpump's padding + extension, re-encrypt with the known key, and send both updated `user` and `signature`.

```python
import hashpumpy, binascii, base64, urllib
from Crypto.Cipher import AES

# Extract AES key from leaked rack.session cookie
key = base64.b64decode(urllib.unquote(cookies['rack.session'].split('-')[0]))[-32:]
user = binascii.unhexlify(cookies['user'])
iv, ct = user[:16], user[16:]

def decrypt(c): return AES.new(key, AES.MODE_CBC, iv).decrypt(c).rstrip(b'\x10\x0f\x0e...')
def encrypt(p): pad = 16 - len(p) % 16; return AES.new(key, AES.MODE_CBC, iv).encrypt(p + bytes([pad])*pad)

# Length-extend signature (secret length guessed = 8)
new_sig, new_plain = hashpumpy.hashpump(cookies['signature'], decrypt(ct), b'\nUID 0\n', 8)
cookies['signature'] = new_sig
cookies['user']      = binascii.hexlify(iv + encrypt(new_plain))
```

**Key insight:** Hash length extension applies whenever the MAC is `H(secret || data)` over a Merkle-Damgard hash (MD5/SHA-1/SHA-256). If the *same* `data` also lives inside a *separately* keyed cipher whose key is recoverable, you can combine primitives: hashpumpy produces the extended plaintext and new tag, then you re-encrypt with the leaked AES key so the server's CBC decryption matches the extended string the signature now covers. Parse-order quirks let the appended `\nUID 0\n` win.

-



## Custom Hash State Reversal via Known Intermediates

**Pattern:** Custom hash processes 4-byte blocks, updating state with XOR and rotations. If intermediate states are printed, reverse each block's hash by computing `hash(block) = s(i) XOR ROL(s(i+1), 7)`. Then brute-force 4-byte printable inputs matching each hash value.

```python
def reverse_hash_states(states):
    """Given intermediate hash states, recover per-block hash values."""
    blocks = []
    for i in range(len(states) - 1):
        # state_update: s(i+1) = ROR(s(i) ^ hash(block), 7)
        # Therefore:    hash(block) = s(i) ^ ROL(s(i+1), 7)
        h = states[i] ^ rol32(states[i+1], 7)
        blocks.append(h)
    return blocks

def rol32(val, n):
    return ((val << n) | (val >> (32 - n))) & 0xFFFFFFFF

# Brute-force printable 4-byte blocks matching each hash
import itertools, string
for target_hash in block_hashes:
    for chars in itertools.product(string.printable, repeat=4):
        block = bytes(ord(c) for c in chars)
        if custom_hash(block) == target_hash:
            print(f"Found: {block}")
            break
```

**Key insight:** When a custom hash function leaks intermediate states (after each block), each block becomes an independent 4-byte brute-force problem (~2^32 worst case, reduced to ~10^8 for printable ASCII). Inverting the state update equation isolates per-block targets. This pattern appears whenever iterative hashes expose partial state.

-

## CRC32 Brute-Force for Small Payloads

**Pattern:** Encrypted ZIP files store CRC32 of uncompressed contents. For very small files (5 bytes), brute-force all printable 5-character strings, compute CRC32, and match against the stored value. Multiple matches are common but context resolves ambiguity.

```python
import binascii, itertools, string, zipfile

# Extract CRC from ZIP without decrypting
with zipfile.ZipFile('encrypted.zip') as z:
    crc = z.infolist()[0].CRC

# Brute-force 5-byte printable content
for chars in itertools.product(string.printable[:95], repeat=5):
    candidate = ''.join(chars).encode()
    if binascii.crc32(candidate) & 0xFFFFFFFF == crc:
        print(f"Match: {candidate}")
```

**Key insight:** CRC32 stored in ZIP headers is not encrypted — it's always accessible even for password-protected ZIPs. For small files (≤ 6 bytes of printable ASCII), the search space is feasible. A C implementation is ~100x faster than Python. Multiple CRC collisions are expected for 5+ byte payloads; combine with language analysis or cross-reference multiple encrypted files to disambiguate.

-

## SHA-256 Basis Attack for XOR-Aggregate Hash Bypass

**Pattern:** Find 256 files whose SHA-256 hashes form a linear basis for `Z_2^256`. Then for any target hash, compute which subset of basis files XORs to produce the desired hash difference. This breaks systems that verify integrity via `XOR(sha256(file_i)) == expected`.

```python
# 1. Generate ~300 random valid Python files
# 2. Compute SHA-256 of each -> 256-bit vectors over GF(2)
# 3. Gaussian elimination to find 256 linearly independent vectors
# 4. Target: h_new XOR h_delta = h_orig
# 5. Solve the linear system to find which basis files to include
from sage.all import GF, matrix
M = matrix(GF(2), [hash_to_bits(sha256(f)) for f in basis_files])
target = hash_to_bits(sha256(malicious_zip)) ^ hash_to_bits(original_hash)
solution = M.solve_left(target)
```

**Key insight:** SHA-256 hashes are 256-bit vectors over GF(2). Given ~256 random hashes, they almost certainly span the full space, meaning you can XOR-combine them to produce any target 256-bit value. This breaks XOR-based aggregate hash verification: if the system checks `XOR(sha256(file_i)) == expected`, you can replace files while maintaining the aggregate. The attack does NOT find SHA-256 collisions - it exploits the linearity of XOR aggregation over non-linear hash outputs.

-

### Custom MAC Forgery via XOR Block Cancellation with Key Rotation

**Pattern:** Custom MAC uses AES-ECB with key stream that repeats every 128 blocks. Craft three queries where 2048-byte filler blocks cancel via XOR between queries, leaving only the target command's MAC.

```python
mac1 = fmac("tag " + tag_cmd(cmdline))      # tag AAA...
mac2 = fmac("tag " + expand_cmd(cmdline))    # tag BBB... + cmd_padded
mac3 = fmac("tag " + expand_cmd(tag_cmd(cmdline)))  # tag BBB... + tagAAA_padded
forged_mac = mac1 ^ mac2 ^ mac3  # XOR cancellation = fmac(cmdline)
```

**Key insight:** When a MAC's internal key stream repeats periodically, arrange message blocks so that identical blocks at the same key-stream positions cancel via XOR across multiple queries. Three queries suffice to forge any target command's MAC.

-

### Bit-by-Bit HMAC Key Recovery via XOR Plus Addition Arithmetic

**Pattern:** Flawed HMAC computes `sha256((key XOR msg) + msg)` where `+` is bitwise addition (not concatenation). Sending `msg=0` gives `sha256(key)`. For bit position `i`, sending `msg=2^i`: if key bit `i` is set, XOR clears it and addition restores it, giving the same hash.

```python
key_hash = get_digest(b'\x00')  # sha256(key + 0) = sha256(key)
key = 0
for i in range(key_bits):
    digest = get_digest(int_to_bytes(2**i))
    if digest == key_hash:
        key |= (1 << i)  # bit i is set in key
```

**Key insight:** When XOR and addition interact, setting bit `i` in the message XORs it away from the key but adds it back. If key bit `i` was already set, `XOR(1,1)=0` and `0+1=1`, restoring the original value. If key bit `i` was 0, `XOR(0,1)=1` and `1+1=0` with carry, changing the hash. This creates a per-bit oracle.

-

### SHA-1 Length Extension with UTF-8 High-Byte Bypass

**Pattern:** Server checks that all appended bytes to a length-extendable SHA-1 MAC are `< 0x80`. Standard `hashpumpy`/`hlextend` output contains `0x80` and padding bytes that fail the check. Rewrite the padding region using valid multi-byte UTF-8 sequences (e.g., `\xc2\x80` → U+0080) that survive the filter but SHA-1 treats identically.

```python
import hlextend
h = hlextend.new('sha1')
forged = h.extend(b';cat flag', b'A'*msg_len, key_len, old_mac)
# Replace any 0x80-0xFF bytes with UTF-8 two-byte equivalents
safe = forged.replace(b'\x80', b'\xc2\x80')
```

**Key insight:** ASCII-only filters can be bypassed by substituting multi-byte Unicode sequences whose byte values stay below `0x80`. Any length-extension attack behind an ASCII validator is still exploitable with UTF-8 creativity.

-

