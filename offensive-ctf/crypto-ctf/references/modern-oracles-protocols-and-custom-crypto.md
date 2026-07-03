# CTF Crypto - Modern Oracles, Protocols, and Custom Crypto Failures

## Table of Contents
- [Non-Permutation S-box Collision Attack](#non-permutation-s-box-collision-attack)
- [LCG Partial Output Recovery](#lcg-partial-output-recovery)
- [Affine Cipher over Composite Modulus](#affine-cipher-over-composite-modulus)
- [Ascon-like Reduced-Round Differential Cryptanalysis](#ascon-like-reduced-round-differential-cryptanalysis)
- [Bleichenbacher / PKCS#1 v1.5 RSA Padding Oracle](#bleichenbacher-pkcs1-v15-rsa-padding-oracle)
- [Blum-Goldwasser Bit-Extension Oracle](#blum-goldwasser-bit-extension-oracle)
- [Weak Key Derivation via Public Key Hash XOR](#weak-key-derivation-via-public-key-hash-xor)
- [SRP (Secure Remote Password) Protocol Bypass via Modular Arithmetic](#srp-secure-remote-password-protocol-bypass-via-modular-arithmetic)
- [Modified AES S-Box Brute-Force Recovery](#modified-aes-s-box-brute-force-recovery)
- [Rabin Cryptosystem LSB Parity Oracle](#rabin-cryptosystem-lsb-parity-oracle)
- [PBKDF2 Pre-Hash Bypass for Long Passwords](#pbkdf2-pre-hash-bypass-for-long-passwords)
- [GHASH Key Recovery over Prime Modulus](#ghash-key-recovery-over-prime-modulus)
- [Noisy RSA LSB Oracle with Post-Hoc Error Correction](#noisy-rsa-lsb-oracle-with-post-hoc-error-correction)
- [Sponge Hash Collision via Meet-in-the-Middle on Partial State](#sponge-hash-collision-via-meet-in-the-middle-on-partial-state)
- [SPN Cipher Partial Key Recovery via S-box Intersection](#spn-cipher-partial-key-recovery-via-s-box-intersection)
- [Three-Round XOR Protocol Key Cancellation](#three-round-xor-protocol-key-cancellation)
- [GF(p) Linear-System AES Key Recovery from PCAP Matrix](#gfp-linear-system-aes-key-recovery-from-pcap-matrix)
- [Cross-Session Cube-Root Recovery via CRT](#cross-session-cube-root-recovery-via-crt)
- [Custom SPN Column-Wise XOR Brute-Force](#custom-spn-column-wise-xor-brute-force)
- [Iterated SHA-256 Timing Oracle on Character Match](#iterated-sha-256-timing-oracle-on-character-match)


-

## Non-Permutation S-box Collision Attack

**Pattern:** Custom AES-like cipher with S-box collisions.

**Detection:** `len(set(sbox)) < 256` means collisions exist. Find collision pairs and their XOR delta.

**Attack:** For each key byte, try 256 plaintexts differing by delta. When `ct1 == ct2`, S-box input was in collision set. 2-way ambiguity per byte, 2^16 brute-force. Total: 4,097 oracle queries.

See [advanced-math.md](advanced-math.md) for full S-box collision analysis code.

-

## LCG Partial Output Recovery

**Known parameters:** If LCG (Linear Congruential Generator) constants (M, A, C) are known and output is `state mod N`, iterate by N through modulus to find state:
```python
# output = state % N, state = (A * prev + C) % M
for candidate in range(output, M, N):
    # Check if candidate is consistent with next output
    next_state = (A * candidate + C) % M
    if next_state % N == next_output:
        print(f"State: {candidate}")
```

**Upper bits only (e.g., upper 32 of 64):** Brute-force lower 32 bits:
```python
for low in range(2**32):
    state = (observed_upper << 32) | low
    next_state = (A * state + C) % M
    if (next_state >> 32) == next_observed_upper:
        print(f"Full state: {state}")
```

**Key insight:** LCG output truncation (modulo or upper bits only) hides part of the state, but consecutive outputs constrain it. When output is `state mod N`, iterate candidates by N through the modulus. When only upper bits are visible, brute-force the hidden lower bits and validate against the next output.

-

## Affine Cipher over Composite Modulus

Affine encryption `c = A*x + b (mod M)` with composite M: split into prime factor fields, invert independently, CRT recombine. See [advanced-math.md](advanced-math.md) for full chosen-plaintext key recovery and implementation.

-

## Ascon-like Reduced-Round Differential Cryptanalysis

**Pattern:** 4-round Ascon-like permutation with reduced diffusion. Key-dependent biases in output-bit differentials allow key recovery via chosen input differences.

**Attack:**
1. Reproduce the permutation exactly (critical: post-S-box x4 assignment order matters)
2. Invert the linear layer of x0 using a precomputed 64×64 GF(2) inverse matrix
3. For each bit position i, query with `diff = (1<<i, 1<<i)` across multiple samples
4. Measure empirical biases at output bits `j1 = (i+1) mod 64` and `j2 = (i+14) mod 64`
5. Classify key bits `(k0[i], k1[i])` via centroid-based clustering with sign-pattern mask
6. Verify candidate key in-session; refine low-margin bits with additional samples

**GF(2) linear layer inversion:**
```python
def build_inverse(shifts=(19, 28)):
    """Construct GF(2) inverse matrix for Ascon-like linear layer: x ^= rot(x,19) ^ rot(x,28)."""
    # Build 64x64 matrix over GF(2)
    M = [[0]*64 for _ in range(64)]
    for out_bit in range(64):
        M[out_bit][out_bit] = 1
        for shift in shifts:
            M[out_bit][(out_bit + shift) % 64] ^= 1
    # Gaussian elimination to find inverse
    aug = [row + [1 if i == j else 0 for j in range(64)] for i, row in enumerate(M)]
    for col in range(64):
        pivot = next(r for r in range(col, 64) if aug[r][col])
        aug[col], aug[pivot] = aug[pivot], aug[col]
        for r in range(64):
            if r != col and aug[r][col]:
                aug[r] = [a ^ b for a, b in zip(aug[r], aug[col])]
    return [row[64:] for row in aug]
```

**Centroid clustering for key classification:**
```python
# For each bit position, measure bias at two output positions
# 4 possible (k0[i], k1[i]) pairs → 4 centroid patterns
# Uses sign-pattern mask CMASK=0x73 to account for bit-position-dependent behavior
# Classify by minimum Euclidean distance in 2D bias space
CMASK = 0x73
for i in range(64):
    bias_j1, bias_j2 = measure_biases(i, samples)
    mask_bit = (CMASK >> (i % 8)) & 1
    centroids = centroid_table[mask_bit]  # Precomputed per-position centroids
    k0_bit, k1_bit = min(range(4), key=lambda c: euclidean_dist(
        (bias_j1, bias_j2), centroids[c]))
```

**Key insight:** Reduced-round lightweight ciphers (Ascon, GIFT, etc.) have exploitable biases when the number of rounds is insufficient for full diffusion. The linear layer's inverse can be computed algebraically, and differential biases measured across chosen-plaintext queries reveal individual key bits. This is practical even with noisy measurements if you collect enough samples.

-

## Bleichenbacher / PKCS#1 v1.5 RSA Padding Oracle

**Pattern:** RSA encryption with PKCS#1 v1.5 padding where the server reveals whether decrypted plaintext has valid `0x00 0x02` prefix. Adaptive chosen-ciphertext attack recovers the plaintext.

```python
import gmpy2

def bleichenbacher_oracle(c, n, e):
    """Returns True if RSA decryption has valid PKCS#1 v1.5 padding (0x00 0x02 prefix)."""
    resp = send_to_server(c)
    return resp.status_code != 400  # Server returns 400 on bad padding

def bleichenbacher_attack(c0, n, e, oracle, k):
    """
    c0: target ciphertext (integer)
    k: byte length of modulus
    """
    B = pow(2, 8 * (k - 2))

    # Step 1: Start with s1 = ceil(n / 3B)
    s = (n + 3 * B - 1) // (3 * B)

    # Step 2: Search for s where oracle(c0 * s^e mod n) is True
    while True:
        c_prime = (c0 * pow(s, e, n)) % n
        if oracle(c_prime, n, e):
            break
        s += 1

    # Step 3: Narrow interval [a, b] using s values
    # Repeat: find new s, narrow interval, until a == b
    # When interval collapses, plaintext = a * modinv(s, n) % n
    # (Full implementation requires interval tracking — use existing tools)
```

**Tools:**
```bash
# ROBOT attack scanner (modern Bleichenbacher variant)
python3 robot-detect.py -H target.com

# TLS-Attacker framework
java -jar TLS-Attacker.jar -connect target:443 -workflow_type BLEICHENBACHER
```

**Key insight:** The attack is adaptive — each oracle response narrows the range of possible plaintexts. Typically requires ~10,000 oracle queries for RSA-2048. The ROBOT attack (Return Of Bleichenbacher's Oracle Threat) showed this affects modern TLS implementations through subtle timing differences. Any server that distinguishes "bad padding" from "bad content" is vulnerable.

-

## Blum-Goldwasser Bit-Extension Oracle

**Pattern:** Exploit a decryption oracle for Blum-Goldwasser-style encryption by extending ciphertext length by one bit per query to leak plaintext via parity.

**Key insight:** Extend ciphertext by one bit (L+1), shift ciphertext left (`c << 1`), and submit a modified `y` value. The oracle reveals the LSB (parity) of each decrypted chunk. The squaring sequence `y = pow(y, 2, N)` can be manipulated to produce valid extended ciphertexts the server hasn't seen.

```python
# Iterative plaintext recovery via bit-extension
for i in range(msg_length):
    extended_c = original_c << 1        # Shift ciphertext left by 1
    new_y = pow(original_y, 2, N)       # Advance squaring sequence
    response = oracle(extended_c, new_y, msg_length + 1)
    leaked_bit = response & 1           # LSB reveals one plaintext bit
    plaintext_bits.append(leaked_bit)
    original_y = new_y
```

**When to use:** Blum-Goldwasser or BBS-based (Blum Blum Shub) encryption with a decryption oracle that accepts variable-length ciphertexts. The parity leak accumulates one bit per query.

-

## Weak Key Derivation via Public Key Hash XOR

**Pattern:** Hybrid RSA+AES encryption where the AES key is derived as `SHA256(DER_encoded_public_key) XOR seed`, with the seed hardcoded or predictable. Since the public key is public, the AES key is fully recoverable without the RSA private key.

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from hashlib import sha256

# Public key is available
pubkey = RSA.import_key(open("public.pem").read())
der_bytes = pubkey.export_key("DER")

# Seed from challenge (hardcoded/predictable)
seed = b'!'

# Derive AES key the same way the encryptor did
key_hash = sha256(der_bytes).digest()
aes_key = bytes(a ^ b for a, b in zip(key_hash, seed.ljust(32, b'\x00')))

# Decrypt
ct = open("flag.enc", "rb").read()
iv, ct_body = ct[:16], ct[16:]
cipher = AES.new(aes_key, AES.MODE_CBC, iv)
plaintext = cipher.decrypt(ct_body)
```

**Key insight:** Key derivation that incorporates only public information (public keys, known constants) provides zero security regardless of the hash function used. The "hybrid" design creates a false sense of security — RSA protects nothing if the AES key doesn't depend on the RSA private key.

**When to recognize:** Artifact set provides both a public key AND an encrypted file, but no private key or ciphertext for RSA. Look for key derivation code that hashes the public key, uses the public key's modulus/exponent as seed material, or XORs with a constant.

-

## SRP (Secure Remote Password) Protocol Bypass via Modular Arithmetic

SRP implementations that only check `A != 0` and `A != N` can be bypassed by sending `A = 2*N`, causing the server to compute a zero session key.

```python
from hashlib import sha256
import hmac

# SRP protocol: server computes session key from A (client's public value)
# S = (A * v^u) ^ b mod N
# If A = 2*N: S = (2*N * v^u) ^ b mod N = 0 (since 2*N mod N = 0)

N = server_modulus
# Send A = 2*N (bypasses checks for A != 0 and A != N)
A_malicious = 2 * N

# Server computes S = 0, so session key K = SHA256(0)
K = sha256(b'\x00').digest()

# Now compute valid HMAC proof with known K
proof = hmac.new(K, salt, sha256).hexdigest()
```

**Key insight:** SRP implementations must validate `A % N != 0`, not just `A != 0` and `A != N`. Sending `A = k*N` for any integer k forces the shared secret to zero, allowing authentication without knowing the password.

-

## Modified AES S-Box Brute-Force Recovery

AES implementation with a custom S-Box created by swapping 3 elements of the standard S-Box. Brute-force all C(256,3) * 2 = 5,527,040 possible permutations.

```cpp
// Three elements swapped from standard AES S-Box
// Total permutations: C(256,3) * 2 = ~5.5 million (feasible to brute-force)
#include <openssl/aes.h>

void bruteforce_sbox(uint8_t ciphertext[], uint8_t key[], int ct_len) {
    uint8_t standard_sbox[256]; // standard AES S-Box
    // Try all 3-element swaps
    for (int i = 0; i < 256; i++)
        for (int j = i+1; j < 256; j++)
            for (int k = j+1; k < 256; k++) {
                // Swap pairs: (i,j), (i,k), (j,k)
                uint8_t sbox[256];
                memcpy(sbox, standard_sbox, 256);
                swap(sbox[i], sbox[j]); // try each 2-element swap from the triple
                // Decrypt and check for valid plaintext
                if (try_decrypt_with_sbox(sbox, ciphertext, key, ct_len))
                    return; // found it
            }
}
```

**Key insight:** When a custom AES S-Box differs from standard by only a few element swaps, the search space is small enough to brute-force. For 3 swapped elements: C(256,3) permutation groups times the swap combinations within each group.

-

## Rabin Cryptosystem LSB Parity Oracle

**Pattern:** Server encrypts flag with the Rabin cryptosystem (`c = m^2 mod n`) and provides an LSB oracle — for any ciphertext, it returns the least significant bit of the decrypted plaintext. Binary search recovers the full plaintext in `log2(n)` queries.

```python
from Crypto.Util.number import long_to_bytes

def lsb_oracle_attack(enc_flag, N, oracle_fn):
    """Recover plaintext from Rabin/RSA LSB oracle via binary search."""
    lower = 0
    upper = N
    C = enc_flag
    # Rabin: encrypt(2,N) = 4; multiplying ciphertext by 4 doubles plaintext
    e2 = pow(2, 2, N)  # For Rabin; use pow(2, e, N) for RSA

    for i in range(N.bit_length()):
        C = (e2 * C) % N  # Multiply plaintext by 2
        lsb = oracle_fn(C)
        if lsb == 1:
            # 2*m > N (odd remainder after mod), increase lower bound
            lower = (upper + lower) // 2
        else:
            # 2*m < N (even remainder), decrease upper bound
            upper = (upper + lower) // 2
        # Progressive decryption visible:
        print(long_to_bytes(upper))
    return upper
```

**Key insight:** Rabin (and textbook RSA) are multiplicatively homomorphic: multiplying ciphertext by `2^e mod N` doubles the plaintext mod N. Since N is odd, doubling causes a modular wraparound iff the plaintext exceeds `N/2`, which changes the LSB parity. This creates a binary search: each oracle query halves the candidate range, recovering the full plaintext in exactly `log2(N)` queries (~1024 for RSA-1024).

-

## PBKDF2 Pre-Hash Bypass for Long Passwords

**Pattern:** PBKDF2 (and HMAC generally) pre-hashes passwords longer than the hash block size (64 bytes for SHA-1/SHA-256). If the target password exceeds 64 bytes, `PBKDF2(password)` equals `PBKDF2(SHA1(password))`, enabling authentication with the hash instead of the original password.

```python
import hashlib

original_password = "complexPasswordWhichContainsManyCharactersWithRandomSuffixeghjrjg"
# len > 64, so HMAC pre-hashes it
equivalent = hashlib.sha1(original_password.encode()).digest()
# Login with equivalent — PBKDF2 produces the same derived key
```

**Key insight:** HMAC's inner construction is `H((K XOR ipad) || message)`. When the key (password) exceeds the hash block size, HMAC first reduces it via `K = H(password)`. This means `HMAC(long_password,...)` equals `HMAC(H(long_password),...)`. Any system using PBKDF2/HMAC with an identity check after hash comparison may be vulnerable when passwords exceed the hash block size. This is HMAC-specified behavior, not an implementation bug.

-

## GHASH Key Recovery over Prime Modulus

**Pattern:** A custom GCM-like scheme computes `tag = c + sum(b_i * H^(i+1)) mod n` where `n` is a 128-bit prime (not `GF(2^128)`). The 12-byte nonce has 10 bytes fixed from the session ID plus 2 random bytes, so nonce collisions arrive in roughly 256 encryption queries (birthday bound). With two colliding nonces, the equations for `tag1` and `tag2` share the same `c = E_K(nonce || counter)`, so subtracting eliminates `c` and leaves a linear equation in `H` modulo prime `n` — solvable by a single modular inverse, not `GF(2^128)` polynomial factoring.

```python
from Crypto.Util.number import bytes_to_long, long_to_bytes, inverse

n = 327989969870981036659934487747327553919  # prime modulus (not GF(2^128))

# 1. Request encryptions with single-block messages until two share a nonce
# 2. With colliding (nonce, ct1, tag1) and (nonce, ct2, tag2):
m1 = bytes_to_long(ct1)  # single 16-byte block
m2 = bytes_to_long(ct2)
t1 = bytes_to_long(tag1)
t2 = bytes_to_long(tag2)
H = ((t1 - t2) * inverse(m1 - m2, n)) % n

# 3. Forge: encrypt "may i please have the galf", flip CTR bytes to 'flag'
#    then recompute tag using recovered H and c = tag - sum(b_i * H^(i+1))
c0 = (t1 - sum(bytes_to_long(b) * pow(H, i + 1, n) for i, b in enumerate(blocks1))) % n
forged_tag = (c0 + sum(bytes_to_long(b) * pow(H, i + 1, n) for i, b in enumerate(forged_blocks))) % n
```

**Key insight:** GCM's security rests on `GHASH` operating over `GF(2^128)` where inversion is hard without the key. Swapping the modulus to a plain prime `n` collapses the authentication to textbook linear algebra mod `n` — two nonce-colliding tags give one linear equation per unknown, solved with `inverse(m1 - m2, n)`. Short-nonce (2 random bytes) designs guarantee birthday collisions in ~256 queries. Contrast with the `GF(2^128)` AES-GCM forbidden attack in [modern-cipher-modes-and-forgery.md](modern-cipher-modes-and-forgery.md#aes-gcm-nonce-reuse-forbidden-attack), which needs polynomial factoring over binary fields.

-

## Noisy RSA LSB Oracle with Post-Hoc Error Correction

**Pattern:** Extension of the RSA LSB oracle binary search when the oracle occasionally returns incorrect results. Run the standard LSB oracle attack, then inspect decoded bytes. Non-ASCII or unexpected charset values indicate an oracle error within the last ~8 bits. Try single bit-flips at nearby oracle positions; the correct flip fixes the entire remaining decryption.

```python
def lsb_oracle_attack(ciphertext, e, n, oracle_fn, flips=None):
    """Recover plaintext from RSA LSB oracle, with optional error correction."""
    flips = flips or []
    lower, upper = 0, n
    mult = 1
    for i in range(n.bit_length()):
        ciphertext = (ciphertext * pow(2, e, n)) % n
        result = oracle_fn(ciphertext)
        if i in flips:
            result = not result  # correct known oracle error
        mid = (lower + upper) // 2
        if result == 0:
            upper = mid
        else:
            lower = mid
    return lower
```

**Key insight:** Sparse oracle errors produce localized corruption in the recovered plaintext. By inspecting character validity (e.g., expecting hex digits), the error position can be identified and corrected by flipping the oracle result at that query index.

-

## Sponge Hash Collision via Meet-in-the-Middle on Partial State

**Pattern:** A custom sponge hash uses AES with a known key, XORing 10-byte message blocks into a 16-byte state. Since only 10 of 16 state bytes are controllable per block, a direct preimage requires ~2^48 work. Meet-in-the-middle reduces this: precompute 2^24 forward AES encryptions keyed on their last 6 bytes, then search backward decryptions for matches in those 6 bytes.

```python
from Crypto.Cipher import AES
import os

aes = AES.new(b'\x00' * 16, AES.MODE_ECB)
forward = {}

# Forward: compute AES(random_10_bytes || 0x00*6), key on last 6 bytes
for _ in range(2**24):
    block = os.urandom(10) + b'\x00' * 6
    enc = aes.encrypt(block)
    forward[enc[-6:]] = block

# Backward: compute AES_dec(target XOR random_c), check last 6 bytes
target_state = b'\x77\x40\x56\x0a\x1d\x64'  # target hash
for _ in range(2**40):
    c_block = os.urandom(10) + target_state
    dec = aes.decrypt(c_block)
    if dec[-6:] in forward:
        a_block = forward[dec[-6:]]
        b_block = xor(aes.encrypt(a_block), dec)  # middle block
        break
```

**Key insight:** When a sponge rate is smaller than the state size, the uncontrolled bytes create a meet-in-the-middle opportunity. Precompute one direction, search the other — reducing 2^48 to 2^24 space + 2^24 time.

-

## SPN Cipher Partial Key Recovery via S-box Intersection

**Pattern:** A 3-round substitution-permutation network with 36-bit blocks and 6-bit S-boxes. Attack using chosen-plaintext pairs: for each pair of 6-bit sub-keys (rounds 2 and 3), partially decrypt through the last two rounds and check if the intermediate S-box input matches. Intersecting candidate key sets across ~200 plaintext-ciphertext pairs uniquely identifies each 6-bit sub-key, reducing a 108-bit brute force to six independent 12-bit searches.

```python
def recover_subkeys(pairs, sbox, perm):
    """Recover 6-bit subkeys via intersection across plaintext-ciphertext pairs."""
    for sbox_pos in range(6):  # 6 S-boxes per round
        candidates = None
        for pt, ct in pairs:
            valid = set()
            for k2 in range(64):  # 6-bit subkey round 2
                for k3 in range(64):  # 6-bit subkey round 3
                    # Partial decrypt through rounds 3 and 2
                    intermediate = inv_sbox[ct_bits[sbox_pos] ^ k3]
                    intermediate = inv_perm(intermediate)
                    if inv_sbox[intermediate ^ k2] == expected_from_pt:
                        valid.add((k2, k3))
            candidates = valid if candidates is None else candidates & valid
        assert len(candidates) == 1  # unique key pair
```

**Key insight:** SPN structures allow divide-and-conquer key recovery. Each S-box position can be attacked independently, and the intersection of valid key candidates across multiple plaintext-ciphertext pairs converges to a unique solution.

-

## Three-Round XOR Protocol Key Cancellation

**Pattern:** A custom protocol performs a three-message XOR key exchange:
1. Client sends `c1 = msg XOR clientKey`
2. Server responds `c2 = c1 XOR serverKey`
3. Client sends `c3 = c2 XOR clientKey`

All three ciphertexts are observable in a PCAP or network capture. Computing `c1 XOR c2 XOR c3` directly recovers the original `msg` because all key material cancels:

```python
# c1 = msg ^ clientKey
# c2 = msg ^ clientKey ^ serverKey
# c3 = msg ^ serverKey
# c1 ^ c2 ^ c3 = msg ^ clientKey ^ msg ^ clientKey ^ serverKey ^ msg ^ serverKey
#              = msg   (all keys cancel via XOR)
plaintext = bytes(a ^ b ^ c for a, b, c in zip(c1, c2, c3))
```

**Key insight:** Three-message XOR key exchange where the client applies its key twice creates an algebraic weakness: XOR of all three ciphertexts directly recovers the original message without knowledge of either key. Any protocol where the same key is applied an even number of times is trivially broken.

-

### GF(p) Linear-System AES Key Recovery from PCAP Matrix

**Pattern:** Service sends 40 plaintext/ciphertext pairs over the network. Extract from pcap with tshark, build a 40×40 matrix `A` and vector `b` over `GF(p)`, then solve for the unknown AES round-key bytes.

```python
from sage.all import matrix, GF
A = matrix(GF(p), 40, A_rows)
key = A.solve_right(vector(GF(p), b))
```

Use `tshark -r file.pcap -Y 'data.len>0' -T fields -e data` to dump the packet bytes, parse into rows, feed to Sage.

**Key insight:** Any protocol that reveals multiple "key applied to known input" samples collapses to linear algebra when the transformation is linear (or linear in a subfield). Sage's `solve_right` handles the rest.

-

### Cross-Session Cube-Root Recovery via CRT

**Pattern:** Service exposes `m^3 mod N_i` across multiple sessions with different moduli but the same small plaintext. Because `m^3 < N_1 * N_2 * N_3` for small `m`, Chinese Remainder Theorem recovers `m^3` as an integer, then `iroot` gives `m`.

```python
from sympy.ntheory.modular import crt
from gmpy2 import iroot
m_cubed, _ = crt([N1, N2, N3], [c1, c2, c3])
m, exact = iroot(int(m_cubed), 3)
assert exact
```

**Key insight:** Håstad broadcast attack for `e = 3` generalises to any scenario where you see `m^e mod N_i` across enough moduli that `m^e < prod(N_i)`. CRT joins them; integer root extraction finishes.

-

## Custom SPN Column-Wise XOR Brute-Force

**Pattern:** SPN (Substitution-Permutation Network) cipher with a seed-based sbox/pbox and a final XOR key layer. If the XOR key is applied column-wise (each key byte affects one column position independently), each key byte can be brute-forced separately using printable-text consistency as an oracle.

**Attack:**
1. Collect multiple ciphertext blocks (same key, different plaintexts)
2. For each column position `c` (0-15), try all 256 candidate key bytes `k`
3. Apply the inverse pbox and sbox to undo the SPN rounds, then XOR with candidate `k`
4. Keep only candidates where ALL blocks produce printable ASCII at position `c`
5. The intersection of valid candidates across blocks recovers each key byte

**Multi-round variant:** Peel one round at a time. After recovering the outermost XOR key, apply the inverse pbox/sbox for that round using the recovered bytes, then repeat for the next inner round.

**Seed-based permutation dependency:** When sbox and pbox are generated from a shared seed, recovering partial key bytes constrains the seed (and thus the remaining permutation entries). Use this to propagate partial solutions across columns with cross-column dependencies.

**Key insight:** Column-aligned XOR layers in SPN ciphers allow independent per-byte brute-force using printable-text consistency as an oracle. Cross-column key reuse from seed-based permutations propagates partial solutions.

-

### Iterated SHA-256 Timing Oracle on Character Match

**Pattern:** Server validates password character-by-character, and each correct character triggers an additional `sha256` iterated 9999 times. Correct characters therefore make the server respond ~0.66 s slower. Brute-force each position by timing responses.

```python
for ch in string.printable:
    t = time.time()
    send(prefix + ch)
    dt = time.time() - t
    if dt > baseline + 0.3:
        prefix += ch; break
```

**Key insight:** Any early-exit or variable-work validator using heavy hashing leaks position-by-position through total wall-time. Measure baseline vs. correct-char time, not absolute times.

-

