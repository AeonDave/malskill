# CTF Crypto - Exotic Algebraic Structures

## Table of Contents
- [Hash-Based One-Time Signatures (WOTS+/XMSS/LMS) — Reuse and Dominance Forgery](#hash-based-one-time-signatures-wotsxmsslms--reuse-and-dominance-forgery)
- [Braid Group DH — Alexander Polynomial Multiplicativity]
- [Monotone Function Inversion with Partial Output](#monotone-function-inversion-with-partial-output)
- [Tropical Semiring Residuation Attack]
- [Paillier Cryptosystem Attack]
- [Hamming Code Error Correction with Helical Interleaving]
- [ElGamal Universal Re-encryption]
- [Paillier Oracle Size Bypass via Ciphertext Factoring]
- [Format-Preserving Encryption Feistel Brute-Force]
- [Icosahedral Symmetry Group Cipher]
- [Goldwasser-Micali Ciphertext Replication Oracle]

-

## Hash-Based One-Time Signatures (WOTS+/XMSS/LMS) — Reuse and Dominance Forgery

**Recognise it:** a "post-quantum"/"quantum-proof" signature that is an array of ~67 hash words plus a Merkle `auth_path`, `leaf_index`, `pub_seed`, and a committed `root`. Parameters `w=16, len1=64, len2=3` mean the digest is split into 64 nibbles plus a 3-nibble checksum, and word `i` is the hash chain from the secret start, iterated `digits[i]` times.

**Dominance forgery — what one signature already gives you.** A signature over digest `A` publishes chain `i` at index `A_i`. Chains only run forward, so any digest `T` with `T_i >= A_i` for **all** `len` positions is forgeable by continuing each chain `T_i - A_i` steps. The checksum blocks are what stop trivial abuse: raising message nibbles lowers the checksum, so a single signature yields a valid `T` with probability ~`0.53^len` ≈ 2⁻⁵⁹ — do not try to grind this from one sample.

**Reuse is the real break.** If the same leaf ever signs twice, take the per-index minimum: `m_i = min` over samples, keeping that sample's word. `m_i` is the minimum of K uniform draws over `0..w-1`, so K≈64–80 drives almost every `m_i` to 0 — then a chosen digest dominates `m` on the first or second grind and you can sign **anything** for that leaf.

```python
# per-chain minima across K signatures under one leaf
for digest, sig in samples:
    d = digits(digest)
    for i in range(LEN):
        if d[i] < mins[i]:
            mins[i], best[i] = d[i], sig[i]
# forge for any target whose digits dominate mins
forged = [chain(best[i], i, mins[i], dt[i] - mins[i], pub_seed) for i in range(LEN)]
```

**Where reuse comes from — audit the state, not the maths.** These schemes are *stateful*: security holds only while the leaf counter advances monotonically and is durable. The implementation is usually correct; the surrounding system is not. Look for a snapshot/restore, chain reorg, backup rollback, HSM re-seed, container restart, or a "rewind"/"replay" endpoint that resets the counter while the key material persists. Prove it by requesting two signatures across the reset and comparing `leaf_index`. The same reasoning applies to LMS and to any Lamport/Winternitz variant.

**Grind the target, not the key.** When the verifying application hashes attacker-controlled fields (an EIP-712 struct with a free `salt`, a nonce, a memo), grind that field until `digits(target)` dominates `mins`; you never need to invert the signer's domain separation.

-

## Braid Group DH — Alexander Polynomial Multiplicativity

**Pattern:** Diffie-Hellman key exchange built over mathematical braids. Public keys are derived by connecting a private braid to public info, then scrambled with Reidemeister-like moves. Shared secret = `sha256(normalize(calculate(connect(my_priv, their_pub))))`. The `calculate()` function computes the Alexander polynomial of the braid.

**Protocol structure:**
```python
import sympy as sp
import hashlib

t = sp.Symbol('t')

def compose(p1, p2):
    return [p1[p2[i]] for i in range(len(p1))]

def inverse(p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return inv

def connect(g1, g2):
    """Concatenate two braids with a swap at the junction."""
    x1, o1 = g1
    x2, o2 = g2
    l = len(x1)
    new_x = list(x1) + [v + l for v in x2]
    new_o = list(o1) + [v + l for v in o2]
    # Swap at junction
    new_x[l-1], new_x[l] = new_x[l], new_x[l-1]
    return (new_x, new_o)

def sweep(ap):
    """Compute winding number matrix from arc presentation."""
    l = len(ap)
    current_row = [0] * l
    matrix = []
    for pair in ap:
        c1, c2 = sorted(pair)
        diff = pair[1] - pair[0]
        s = 1 if diff > 0 else (-1 if diff < 0 else 0)
        for c in range(c1, c2):
            current_row[c] += s
        matrix.append(list(current_row))
    return matrix

def mine(point):
    x, o = point
    return sweep([*zip(x, o)])

def calculate(point):
    """Compute Alexander polynomial from braid."""
    mat = sp.Matrix([[t**(-x) for x in y] for y in mine(point)])
    return mat.det(method='bareiss') * (1 - t)**(1 - len(point[0]))

def normalize(calculation):
    """Convert Laurent polynomial to standard form."""
    poly = sp.expand(sp.simplify(calculation))
    all_exp = [term.as_coeff_exponent(t)[1] for term in poly.as_ordered_terms()]
    min_exp = min(all_exp)
    poly = sp.expand(sp.simplify(poly * t**(-min_exp)))
    if poly.coeff(t, 0) < 0:
        poly *= -1
    return poly

# Key exchange:
# alice_pub = scramble(connect(pub_info, alice_priv), 1000)
# bob_pub = scramble(connect(pub_info, bob_priv), 1000)
# shared = sha256(str(normalize(calculate(connect(alice_priv, bob_pub)))))
```

**The fatal vulnerability — Alexander polynomial multiplicativity:**

The Alexander polynomial satisfies `Δ(β₁·β₂) = Δ(β₁) × Δ(β₂)` under braid concatenation. This makes the scheme abelian:

```python
# Eve computes shared secret from public values only:
calc_pub = normalize(calculate(pub_info))
calc_alice = normalize(calculate(alice_pub))
calc_bob = normalize(calculate(bob_pub))

# Recover Alice's private polynomial
calc_alice_priv = sp.cancel(calc_alice / calc_pub)  # exact division

# Shared secret = calc(alice_priv) * calc(bob_pub) = calc(bob_priv) * calc(alice_pub)
shared_poly = normalize(sp.expand(calc_alice_priv * calc_bob))
shared_hex = hashlib.sha256(str(shared_poly).encode()).hexdigest()

# Decrypt XOR stream cipher
key = bytes.fromhex(shared_hex)
while len(key) < len(ciphertext):
    key += hashlib.sha256(key).digest()
plaintext = bytes(a ^ b for a, b in zip(ciphertext, key))
```

**Computational trick for large matrices:**

Direct sympy Bareiss on rational-function matrices (e.g., 30×30 with entries `t^(-w)`) is extremely slow. Clear denominators first:

```python
# Winding numbers range from w_min to w_max (e.g., -1 to 5)
# Multiply all entries by t^w_max to get polynomial matrix
k = max(abs(w) for row in winding_matrix for w in row)
n = len(winding_matrix)

# Original: M[i][j] = t^(-w[i][j])
# Scaled:   M'[i][j] = t^(k - w[i][j])  (all non-negative powers)
mat_poly = sp.Matrix([[t**(k - w) for w in row] for row in winding_matrix])
det_scaled = mat_poly.det(method='bareiss')  # Much faster!

# Recover true determinant: det(M) = det(M') / t^(k*n)
det_true = sp.cancel(det_scaled / t**(k * n))
# Then: (1-t)^(n-1) divides det_true (topological property)
result = sp.cancel(det_true * (1 - t)**(1 - n))
```

**Validation — palindromic property:**
All valid Alexander polynomials are palindromic (coefficients read the same forwards and backwards). Use this as a sanity check on intermediate results:
```python
def is_palindromic(poly, var=t):
    coeffs = sp.Poly(poly, var).all_coeffs()
    return coeffs == coeffs[::-1]
```

**When to recognize:** the prompt mentions braids, knots, permutation pairs, winding numbers, Reidemeister moves, or "topological key exchange." The key mathematical insight is that the Alexander polynomial — while a powerful knot/braid invariant — is multiplicative, making it fundamentally unsuitable as a one-way function for Diffie-Hellman.

**Key lessons:**
- **Diffie-Hellman requires non-abelian hardness.** If the invariant used for the shared secret is multiplicative/commutative under the group operation, Eve can compute it from public values.
- **Scrambling (Reidemeister moves) doesn't help** — the Alexander polynomial is an invariant, so scrambled braids produce the same polynomial.
- **Large symbolic determinants** need the denominator-clearing trick: multiply by `t^k` to get polynomials, compute det, divide back.

-

## Monotone Function Inversion with Partial Output

**Pattern:** A flag is converted to a real number, pushed through an invertible/monotone function (e.g., iterated map, spiral), then some output digits are masked/erased. Recover the masked digits to invert and get the flag.

**Identification:**
- Output is a high-precision decimal number with some digits replaced by `?`
- The transformation is smooth/monotone (invertible via root-finding)
- Flag format constrains the input to a narrow range
- Challenge hints like "brute won't cut it" or "binary search"

**Key insight:** For a monotone function `f`, knowing the flag format constrains the output to a tiny interval. Many "unknown" output digits are actually **fixed** across all valid inputs and can be determined immediately.

**Attack: Hierarchical Digit Recovery**

1. **Determine fixed digits:** Compute `f(flag_min)` and `f(flag_max)` for all valid flags. Digits that are identical in both outputs are fixed regardless of flag content.

2. **Sequential refinement:** Determine remaining unknown digits one at a time (largest contribution first). For each candidate value (0-9), invert `f` and check if the result is a valid flag (ASCII, correct format).

3. **Validation:** The correct digit produces readable ASCII text; wrong digits produce garbage bytes in the flag.

```python
import mpmath

# Match SageMath's RealField(N) precision exactly:
# RealField(256) = 256-bit MPFR mantissa
mpmath.mp.prec = 256  # BINARY precision (not decimal!)
# For decimal: mpmath.mp.dps = N sets decimal places

phi = (mpmath.mpf(1) + mpmath.sqrt(mpmath.mpf(5))) / 2

def forward(x0):
    """The challenge's transformation (e.g., iterated spiral)."""
    x = x0
    for i in range(iterations):
        r = mpmath.mpf(i) / mpmath.mpf(iterations)
        x = r * mpmath.sqrt(x*x + 1) + (1 - r) * (x + phi)
    return x

def invert(y_target, x_guess):
    """Invert via root-finding (Newton's method)."""
    def f(x0):
        return forward(x0) - y_target
    return mpmath.findroot(f, x_guess, tol=mpmath.mpf(10)**(-200))

# Hierarchical search: determine unknown digits sequentially
masked = "?7086013?3756162?51694057..."
unknown_positions = [0, 8, 16, 25, 33,...]

# Step 1: Fix digits that are constant across all valid flags
# (compute forward for min/max valid flag, compare)

# Step 2: For each remaining unknown (largest positional weight first):
for pos in remaining_unknowns:
    for digit in range(10):
        # Set this digit, others to middle value (5)
        output_val = construct_number(known_digits | {pos: digit})
        x_inv = invert(output_val, x_guess=0.335)
        flag_int = int(x_inv * mpmath.power(10, flag_digits))
        flag_bytes = flag_int.to_bytes(30, 'big')

        # Check: starts with prefix? Ends with suffix? All ASCII?
        if is_valid_flag(flag_bytes):
            known_digits[pos] = digit
            break
```

**Why it works:** Each unknown digit affects a different decimal scale in the output number. The largest unknown (earliest position) shifts the inverted value by the most, determining several bytes of the flag. Fixing it and moving to the next unknown reveals more bytes. Total work: `10 * num_unknowns` inversions (linear, not exponential).

**Precision matching:** SageMath's `RealField(N)` uses MPFR with N-bit mantissa. In mpmath, set `mp.prec = N` (NOT `mp.dps`). The last few output digits are precision-sensitive and will only match with the correct binary precision.

**Derivative analysis:** For the spiral-type map `x → r*sqrt(x²+1) + (1-r)*(x+φ)`, the per-step derivative is `r*x/sqrt(x²+1) + (1-r) ≈ 1`, so the total derivative stays near 1 across all 81 iterations. This means precision is preserved through inversion — 67 known output digits give ~67 digits of input precision.

-

## Tropical Semiring Residuation Attack

**Pattern:** Diffie-Hellman key exchange using tropical matrices (min-plus algebra). Per-character shared secret XOR'd with encrypted flag.

**Tropical algebra:**
- Addition = `min(a, b)`
- Multiplication = `a + b`
- Matrix multiply: `(A*B)[i,j] = min_k(A[i,k] + B[k,j])`

**Tropical residuation recovers shared secret from public data:**
```python
def tropical_residuate(M, Mb, aM, n):
    """Recover shared secret from public matrices.
    M = public matrix, Mb = M*b (Bob's public), aM = a*M (Alice's public)
    """
    # Right residual: b*[j] = max_i(Mb[i] - M[i][j])
    b_star = [max(Mb[i] - M[i][j] for i in range(n)) for j in range(n)]
    # Shared secret: aMb = min_j(aM[j] + b*[j])
    aMb = min(aM[j] + b_star[j] for j in range(n))
    return aMb

# Decrypt per-character: key = aMb % 32; plaintext = key ^ ciphertext
for i, enc_char in enumerate(encrypted):
    key = shared_secret % 32
    plaintext_char = chr(key ^ ord(enc_char))
```

**Key insight:** Tropical DH is broken because the min-plus semiring lacks cancellation — given `M` and `M*b`, the "residual" `b*` can be computed directly via `max(Mb[i] - M[i][j])`. Unlike standard DH where recovering `b` from `g^b` is hard, tropical residuation recovers enough of `b`'s effect to compute the shared secret. This makes tropical matrix DH insecure for any matrix size.

**Detection:** the prompt mentions "tropical", "min-plus", "exotic algebra", or defines custom matrix multiplication using `min` and `+`.

-

## Paillier Cryptosystem Attack

The Paillier cryptosystem is a homomorphic encryption scheme where `c = g^m * r^n mod n^2`. When given oracle equations involving c, o, h values:

1. **Recover n:** Compute lower bound `sqrt(max(c, o, h))` to approximate n, then brute-force nearby values
2. **Validate n:** Check equation `h = (c * o) % (n^2)` for correctness
3. **Factor n:** Use standard methods (e.g., factordb) to find p, q
4. **Decrypt:** Apply Paillier decryption:

```python
from sympy import lcm, mod_inverse

# n = p * q (factored)
lam = lcm(p - 1, q - 1)  # Carmichael function
n2 = n * n

def L(x):
    return (x - 1) // n

# Compute mu
g_lam = pow(g, lam, n2)
mu = mod_inverse(L(g_lam), n)

# Decrypt
c_lam = pow(c, lam, n2)
m = (L(c_lam) * mu) % n
```

**Key insight:** Paillier operates mod n^2, so ciphertext values are much larger than RSA. The homomorphic property `E(m1) * E(m2) = E(m1 + m2)` can leak relationships between plaintexts.

-

## Hamming Code Error Correction with Helical Interleaving

When data is protected by Hamming(31,26) codes with helical scan interleaving:

1. **Determine matrix dimensions:** Brute-force width/height (30x30 search space) by testing which dimensions produce valid Hamming codewords
2. **Read data in helical pattern:** Extract bits diagonally from the interleaved matrix
3. **Apply Hamming parity check:** Multiply codeword by parity check matrix H to detect/correct errors

```python
import numpy as np

def check_hamming(codeword, H):
    """Syndrome = H * c^T; zero syndrome means valid codeword"""
    syndrome = np.dot(H, codeword) % 2
    return np.all(syndrome == 0)

# Brute-force dimensions
for w in range(1, 31):
    for h in range(1, 31):
        # Reshape data into w x h matrix
        matrix = data[:w*h].reshape(h, w)
        # Read diagonals (helical scan)
        bits = read_helical(matrix)
        # Check if bits form valid Hamming codewords
        if validate_hamming_stream(bits, H):
            print(f"Dimensions: {w}x{h}")
```

**Key insight:** Try 8 different bit alignment offsets when the start position is unknown. Valid Hamming codewords have zero syndrome under multiplication by the parity check matrix.

-

## ElGamal Universal Re-encryption

Given an ElGamal-like ciphertext tuple (a, b, c, d) = (g^r, h^r, g^s, m*h^s), produce a different valid ciphertext decrypting to the same message without knowing the private key:

Transform exponents r -> 2r, s -> r+s:

```python
def reencrypt(a, b, c, d, p):
    return [
        (a * a) % p,    # g^(2r)
        (b * b) % p,    # h^(2r)
        (a * c) % p,    # g^(r+s)
        (d * b) % p     # m*h^(r+s)
    ]
```

**Key insight:** ElGamal's homomorphic property allows re-randomizing ciphertexts by multiplying components. The relationship between exponents must remain consistent: both pairs must share the same exponent offset.

-

## Paillier Oracle Size Bypass via Ciphertext Factoring

When a Paillier decryption oracle rejects messages exceeding a size limit, exploit the homomorphic property to factor the encrypted flag into smaller pieces:

1. **Paillier additive homomorphism:** `E(m1) * E(m2) mod n^2 = E(m1 + m2 mod n)`
2. **Multiplicative (scalar):** `E(m)^k mod n^2 = E(k*m mod n)`
3. **Factoring ciphertext:** Divide n into small ranges, query oracle with `E(flag) * E(-offset)^1` to determine which range contains the flag
4. **Chunk extraction:** Split the flag value into pieces that each fit within the oracle's size limit, decrypt individually, sum to recover original

```python
from Crypto.Util.number import inverse

def paillier_sub(c, plaintext_sub, n):
    """Compute E(m - plaintext_sub) from E(m) using homomorphic property"""
    n2 = n * n
    # E(-plaintext_sub) = E(n - plaintext_sub) = (n+1)^(n-plaintext_sub) * r^n mod n^2
    neg_enc = pow(n + 1, n - plaintext_sub, n2)
    return (c * neg_enc) % n2

# Binary search for flag value using oracle
def recover_flag(enc_flag, n, oracle_decrypt):
    low, high = 0, n
    while high - low > 1:
        mid = (low + high) // 2
        test_ct = paillier_sub(enc_flag, mid, n)
        result = oracle_decrypt(test_ct)
        if result < n // 2:  # Positive (flag > mid)
            low = mid
        else:  # Negative (flag < mid, wraps around)
            high = mid
    return low
```

**Key insight:** Paillier's additive homomorphism allows computing `E(flag - offset)` without decryption. If the oracle reveals whether the decrypted value is "small" (within limit) or "large" (rejected/wraps), binary search recovers the flag in O(log n) queries.

-

## Format-Preserving Encryption Feistel Brute-Force

**Pattern:** Format-preserving encryption (FPE) using a Feistel network with a small round key. The 96-bit key splits into three components with different roles: a brute-forceable core, a GF(2) mixing matrix, and an affine offset.

**Key structure:**
- `s` (16 bits): Feistel round subkey — only 2^16 = 65536 possibilities
- `seed56` (56 bits): Generates an invertible GF(2) affine mixing matrix `M` (24x24)
- `b24` (24 bits): Affine offset applied after mixing

**Attack:**
1. **Collect encrypt pairs:** Get multiple `(plaintext, ciphertext)` pairs from the FPE oracle
2. **Brute-force `s`:** For each of 65536 candidate round keys, run the Feistel network on known plaintexts. If the Feistel core is correct, the remaining transformation is affine over GF(2)
3. **Solve linear system:** With correct `s`, the relationship `ciphertext = M * feistel_output XOR b24` is linear. Collect 24+ pairs, build a GF(2) matrix equation, solve for `M` and `b24` via Gaussian elimination

```python
import numpy as np

def feistel_encrypt(pt_24bit, s, rounds=3):
    """24-bit Feistel with 16-bit round key s."""
    L, R = pt_24bit >> 12, pt_24bit & 0xFFF
    for r in range(rounds):
        f = (R * s + r) & 0xFFF  # Round function (example)
        L, R = R, L ^ f
    return (L << 12) | R

# Brute-force s (16-bit)
for s_candidate in range(1 << 16):
    feistel_outputs = [feistel_encrypt(pt, s_candidate) for pt in known_pts]
    # Check if feistel_outputs -> known_cts is affine over GF(2)
    # Build system: for each bit position, collect equations
    # If consistent -> found correct s, solve for M and b24
```

**When to recognize:** the prompt mentions "format-preserving encryption", "FPE", or uses a Feistel structure with suspiciously small key components. Any round key under 32 bits is brute-forceable.

**Key lessons:**
- FPE with small Feistel round keys is trivially broken despite the total key looking large (96 bits)
- After recovering the Feistel core, the remaining affine layer is solvable as a linear system over GF(2)
- Collect enough plaintext-ciphertext pairs to overdetermine the linear system

-

## Icosahedral Symmetry Group Cipher

**Pattern:** Encryption maps message bytes to face permutations of a dodecahedron. The icosahedral symmetry group has order 120 (the rotation group of a regular dodecahedron/icosahedron), so each "digit" in base-120 encodes one group element as a specific arrangement of 12 face labels.

**How it works:**
1. Message is converted to a large integer and expressed in base 120
2. Each base-120 digit selects one of 120 possible face permutations
3. The dodecahedron is rendered from a fixed viewing angle, showing only 6 of 12 faces
4. Despite only 6 faces being visible, collisions between the 120 permutations are rare enough for unique recovery

**Attack:**
1. **Build lookup table:** Probe the encryption API with all 120 single-digit inputs (0-119 in base 120), capture the rendered face arrangement for each
2. **Match visible faces:** For each encrypted symbol in the ciphertext, compare the visible face pattern against the lookup table to recover the base-120 digit
3. **Reconstruct message:** Convert the sequence of base-120 digits back to an integer, then to bytes

```python
import itertools

# Build lookup: probe API with single-digit values
lookup = {}
for digit in range(120):
    # Send digit, capture 6 visible face labels from rendered image
    visible = get_visible_faces(encrypt_single(digit))
    lookup[tuple(visible)] = digit

# Decrypt ciphertext
base120_digits = []
for symbol in ciphertext_symbols:
    visible = get_visible_faces(symbol)
    base120_digits.append(lookup[tuple(visible)])

# Convert base-120 to bytes
value = sum(d * 120**i for i, d in enumerate(reversed(base120_digits)))
plaintext = value.to_bytes((value.bit_length() + 7) // 8, 'big')
```

**When to recognize:** Challenge involves polyhedra, dodecahedra, icosahedra, or mentions "120 rotations", "symmetry group", or shows 3D-rendered geometric objects with labeled faces.

**Key insight:** The icosahedral rotation group is small enough (order 120) that a complete lookup table fits easily in memory. Even with partial information (only 6 of 12 faces visible), the permutations are sufficiently distinct to avoid collisions in practice.

-

## Goldwasser-Micali Ciphertext Replication Oracle

**Pattern:** A "proof of knowledge" protocol encrypts a user-chosen AES key using Goldwasser-Micali (GM) bit-by-bit encryption. The service decrypts GM ciphertext bits to reconstruct the AES key, then uses it to decrypt and hash a probe payload. The vulnerability: individual GM ciphertext values can be replayed, and 128 copies of the same GM-encrypted bit produce an AES key of either `0x00...00` or `0xFF...FF`.

**Goldwasser-Micali basics:**
- Encrypts one bit at a time: bit 0 → quadratic residue mod n, bit 1 → non-residue
- Decryption tests whether each ciphertext value is a quadratic residue
- Each ciphertext value independently encodes exactly one bit

**The vulnerability:**
The service accepts 128 GM ciphertext lines as the AES key. By sending the SAME GM ciphertext value 128 times, the decrypted key is either all-zeros (if the bit was 0) or all-ones (if the bit was 1). Since you control the probe plaintext and IV, you can precompute both possible SHA-256 hashes and compare against the service response.

**Attack:**

```python
from Crypto.Cipher import AES
import hashlib

def recover_bit(gm_ciphertext_line, probe_ct, probe_iv, oracle):
    """Determine if a single GM ciphertext encodes 0 or 1."""
    # Replicate the single GM bit 128 times as the AES key
    key_all_zero = b'\x00' * 16
    key_all_ones = b'\xff' * 16

    # Precompute expected hashes for both possible keys
    hash0 = hashlib.sha256(
        AES.new(key_all_zero, AES.MODE_CBC, probe_iv).decrypt(probe_ct)
    ).hexdigest()
    hash1 = hashlib.sha256(
        AES.new(key_all_ones, AES.MODE_CBC, probe_iv).decrypt(probe_ct)
    ).hexdigest()

    # Query oracle with replicated GM line
    result_hash = oracle.query(gm_ciphertext_line, copies=128)

    if result_hash == hash0:
        return 0
    elif result_hash == hash1:
        return 1

# Recover all 128 bits of the AES key
captured_gm_lines = parse_transcript(transcript)  # 128 GM ciphertext values
key_bits = [recover_bit(line, probe_ct, probe_iv, oracle)
            for line in captured_gm_lines]

# Reconstruct AES key and decrypt the captured payload
aes_key = bits_to_bytes(key_bits)
plaintext = AES.new(aes_key, AES.MODE_CBC, captured_iv).decrypt(captured_ct)
```

**Key insight:** Goldwasser-Micali's bit-by-bit encryption means each ciphertext value independently encodes one bit. If a protocol allows replaying individual GM values as components of a larger key, each bit can be isolated and determined via a distinguishing oracle (here, SHA-256 hash comparison). This reduces key recovery from 2^128 brute-force to 128 linear queries.

**When to recognize:** Challenge uses bit-by-bit public-key encryption (GM, Rabin) combined with a symmetric key derivation step. The service decrypts individual ciphertext values without binding them to a position or preventing replay.

**Broader principle:** Any protocol that (1) encrypts a key bit-by-bit and (2) provides an oracle on the reconstructed key is vulnerable to bit-by-bit recovery via replication. The specific oracle (hash, decryption check, timing) varies but the attack structure is the same.

## BB-84 Quantum Key Distribution MITM Attack

**Pattern:** In simulated BB-84 QKD without authentication, perform a full man-in-the-middle by independently negotiating with both Alice and Bob.

```python
# Strategy: Always use basis Z, always send value 1 to Bob
# Alice side: measure in random bases, record results
# Bob side: always receives 1 in basis Z
# Bob's key = all 1s (known to attacker)
# Alice's key = attacker's measured qbit values

# Heuristic: throttle Bob's correct-guess count to match Alice's
# Both parties verify by comparing subset of bits — attacker controls both sides
for qbit in alice_qbits:
    my_basis = 'Z'  # always measure in Z basis
    my_value = measure
    send_to_bob  # always send 1

# After basis reconciliation:
# key_with_alice = [measured values where bases matched]
# key_with_bob = [all 1s]
```

**Key insight:** BB-84 QKD is secure only with authenticated classical channels. Without authentication, an attacker can independently negotiate keys with both parties. Forcing a constant value to one party makes their key entirely predictable, while the other party's key is captured through measurement.

-

## ElGamal Trivial DLP When B = p-1

**Pattern:** ElGamal public key `B = g^key mod p`. If `B + 1 == p`, then `B = p-1 = -1 mod p`. By Euler's criterion, `g^((p-1)/2) ≡ -1 (mod p)` for any primitive root `g`. Therefore `g^key ≡ g^((p-1)/2) (mod p)`, so `key = (p-1)/2` directly. No DLP algorithm needed.

```python
# Check for trivial case
if (B + 1) == p:
    key = (p - 1) // 2
    # Verify
    assert pow(g, key, p) == B
    # Decrypt ElGamal: shared_secret = pow(ephemeral, key, p)
```

**Key insight:** The generator raised to `(p-1)/2` always equals `-1 mod p` (Euler's criterion for quadratic residues). When the public key `B` equals `p-1`, the private key is trivially `(p-1)/2`. Always check `B == p-1` (and `B == 1` for key=0) before attempting general DLP.

-

## Paillier LSB Oracle via Homomorphic Doubling

**Pattern:** Paillier encryption is additively homomorphic: multiplying a ciphertext by itself (`ct^2 mod n^2`) doubles the plaintext. Doubling repeatedly and observing when the LSB changes (due to modular reduction by n) reveals plaintext bits one at a time — a binary search identical to the RSA LSB oracle.

**Attack:**
```python
def paillier_double(ct, n):
    """Homomorphically double the plaintext."""
    return pow(ct, 2, n * n)

def recover_plaintext(ct, oracle_lsb, n):
    """Oracle returns LSB of decrypted plaintext."""
    lower, upper = 0, n
    current_ct = ct
    for _ in range(n.bit_length()):
        current_ct = paillier_double(current_ct)
        lsb = oracle_lsb(current_ct)
        mid = (lower + upper) // 2
        if lsb == 1:
            lower = mid  # plaintext > n/2, wraparound occurred
        else:
            upper = mid
    return lower

# Alternative: homomorphic subtraction to isolate each bit
def paillier_encrypt_scalar(m, n, g=None):
    """Encrypt scalar m under Paillier (with r=1 for known randomness)."""
    g = g or (n + 1)
    return pow(g, m, n * n)  # simplified (r=1)

def subtract_plaintext(ct, val, n):
    """Compute E(pt - val) = ct * E(-val) mod n^2."""
    neg_enc = paillier_encrypt_scalar(n - val, n)
    return (ct * neg_enc) % (n * n)
```

**Key insight:** Paillier's additive homomorphism enables a binary search oracle: doubling the plaintext via `ct^2` and observing LSB changes reveals one bit per query. Equivalently, use homomorphic subtraction of known masks to isolate each bit. Total queries: log2(n) ≈ 2048 for 2048-bit modulus.

-

## Differential Privacy Laplace Noise Cancellation

**Pattern:** Server implements differential privacy by adding Laplace noise (mean 0, scale λ) to character ordinals before returning them. Since Laplace noise has zero mean, querying the same position many times and averaging the results cancels the noise via the Law of Large Numbers.

```python
import requests
import statistics

def recover_char(position, num_queries=1000):
    """Average 1000 noisy responses to cancel Laplace noise."""
    samples = []
    for _ in range(num_queries):
        noisy_val = query_server(position)
        samples.append(noisy_val)
    # Mean converges to true value as queries → ∞
    true_val = round(statistics.mean(samples))
    return chr(true_val)

flag = ''.join(recover_char(i) for i in range(flag_length))
```

**Key insight:** Laplace differential privacy with zero mean is breakable with sufficient queries — averaging N samples reduces noise variance by factor N (standard error ∝ 1/sqrt(N)). With λ=1 and 1000 queries, the mean is within ±0.1 of the true value. Round to nearest integer to recover the exact character ordinal. This applies to any additive zero-mean noise mechanism.

-

## Homomorphic Encryption Oracle Bit-Extraction

**Pattern:** An encryption oracle has homomorphic properties — you can add 1 to the plaintext by performing a known operation on the ciphertext. Extract bits from an unknown plaintext by observing how the ciphertext changes as the plaintext value crosses power-of-2 boundaries.

**Low-bit extraction:**
```python
# Increment plaintext by 1 repeatedly via homomorphic add-1
# Detect when bit N overflows: ciphertext "wraps" at value 2^N
ct = target_ciphertext
for bit_pos in range(num_bits):
    threshold = 2 ** bit_pos
    # Add 1 repeatedly until bit flips
    increments = 0
    prev_ct = ct
    while True:
        ct = homomorphic_add_one(ct)
        increments += 1
        if bit_has_flipped(ct, prev_ct, bit_pos):
            low_bits = (threshold - increments) % threshold
            break
```

**High-bit extraction (divide by 2 on even values):**
```python
# Subtract recovered low bits to make value even
even_ct = homomorphic_subtract(target_ct, low_bits)
# Repeatedly divide by 2 and observe the resulting high bits
for i in range(high_bit_count):
    even_ct = homomorphic_halve(even_ct)
    high_bits = (high_bits << 1) | observe_lsb(even_ct)
```

**Key insight:** Homomorphic oracles enable bit-extraction: detect overflow in specific bit positions when incrementing for low bits; use division-by-2 on even numbers for high bits. The total number of queries scales linearly with the bit count of the plaintext.

-

## ElGamal over Matrices via Jordan Normal Form

**Pattern:** Discrete log on matrices: convert generator G to Jordan normal form, then extract exponent from off-diagonal elements.

```sage
G = Matrix(GF(p), [[...]])  # generator matrix
H = Matrix(GF(p), [[...]])  # H = G^alpha
J, P = G.jordan_form(transformation=True)
H_prime = ~P * H * P  # H in Jordan basis
# For Jordan block with eigenvalue lambda:
# J^alpha has alpha * lambda^(alpha-1) on super-diagonal
# alpha = J[3][3] * H_prime[3][4] / H_prime[3][3]
alpha = int(J[3][3] * H_prime[3][4] / H_prime[4][4])
```

**Key insight:** Matrix DLP reduces to scalar DLP when the matrix is diagonalizable, or to polynomial extraction when Jordan blocks have repeated eigenvalues. The super-diagonal element of J^alpha is `alpha * lambda^(alpha-1)`, giving alpha directly via division when lambda is known. For diagonalizable matrices, the DLP decomposes into independent scalar DLPs per eigenvalue. Always compute the Jordan form first to determine which reduction applies.

-

## OSS (Ong-Schnorr-Shamir) Signature Forgery via Pollard's Method

**Pattern:** Given two valid OSS signatures, forge a signature for the product of their messages using Pollard's composition formula:

```python
# OSS signature: (x, y) valid for message m if x^2 + k*y^2 = m (mod n)
# Pollard's forgery for m1*m2:
def forge_product(x1, y1, x2, y2, k, n):
    X = (x1*x2 + k*y1*y2) % n
    Y = (x1*y2 - x2*y1) % n
    return X, Y
# (X, Y) is a valid signature for m1*m2 mod n
```

**Key insight:** The OSS signature scheme is based on the quadratic form `x^2 + ky^2 = m (mod n)`. Pollard showed that these forms compose multiplicatively - given signatures for m1 and m2, you can forge a signature for m1*m2 without the private key. This is a fundamental algebraic break, not an implementation bug. To sign an arbitrary target message `m_target`, factor it as a product of signed messages, or use the homomorphic property with `m1 = known_signed_message` and construct `m2 = m_target * modinv(m1, n)` if a signature for m2 is obtainable.

-

## Cayley-Purser Decryption Without Private Key

**Pattern:** Cayley-Purser is a matrix-based public-key system using 2x2 matrices modulo a prime. Public key is `(alpha, beta, gamma)` where `gamma = alpha^r * beta * alpha^(-r)` and `epsilon = gamma^s`. The private key is `r`, but decryption only needs a matrix `H` that satisfies `H * gamma = gamma * H`.

**Exploit:** Any matrix `H` commuting with `gamma` decrypts correctly, and the Cayley-Hamilton theorem lets you build one entirely from public values — no need to recover `r`.

```python
from sage.all import matrix, identity_matrix
import operator

# Given public alpha, beta, gamma, epsilon, mu (ciphertext)
invalpha = alpha.inverse()
# Recover scaling entry h via elementwise division
h_elems = (invalpha * gamma - gamma * beta)
h_denom = (beta - invalpha)
h = matrix([[h_elems[i][j] / h_denom[i][j] for j in range(2)] for i in range(2)])

H = h[0][0] * identity_matrix(2) + gamma
plaintext = (H.inverse() * epsilon * H) * mu * (H.inverse() * epsilon * H)
```

**Key insight:** Any commuting matrix works as the decryption key. Cayley-Hamilton guarantees that `H = c1 * I + c2 * gamma` commutes with `gamma`, and the needed scalar `c1` can be read off by comparing entries of `alpha^(-1) * gamma` against `gamma * beta`. Always check whether "private key" operations can be replaced by a commutation-equivalent derived from public data.

-

## BIP39 Partial-Mnemonic Brute Force via Checksum

**Pattern:** Artifact set provides 23 of 24 BIP39 mnemonic words (Japanese wordlist) and the target flag = `md5(entropy)`. Each word encodes 11 bits, so the missing word costs only `2^11 = 2048` guesses. Validate each candidate by running BIP39's built-in SHA-256 checksum over the reassembled entropy — only the correct guess passes.

```python
from mnemonic import Mnemonic
lg = Mnemonic("japanese")
known = ["...23 words..."]
for w in lg.wordlist:
    try:
        if lg.check(" ".join(known + [w])):
            entropy = lg.to_entropy(" ".join(known + [w]))
            print(md5(entropy).hexdigest())
    except Exception: pass
```

**Key insight:** BIP39 has a built-in 4-bit-per-word checksum, so partial mnemonics are self-verifying. Same trick applies to Electrum's seed format and any mnemonic scheme with internal parity.

-

## Asmuth-Bloom Threshold Secret Sharing via CRT

**Pattern:** Instead of Shamir's polynomial interpolation, Asmuth-Bloom splits a secret `S` into shares `(s_i, p_i)` where each `s_i = S mod p_i` and `p_i` are pairwise-coprime primes. Recover `S` by applying the Chinese Remainder Theorem to any threshold number of shares.

```python
from sympy.ntheory.modular import crt
# shares = [(s1,p1), (s2,p2),..., (sk,pk)]
residues = [s for s, _ in shares]
moduli   = [p for _, p in shares]
S, M = crt(moduli, residues)
flag = long_to_bytes(int(S))
```

**Key insight:** Threshold sharing schemes can be CRT-based, not polynomial. Recognise Asmuth-Bloom by the `(residue, modulus)` share format; Shamir's scheme only publishes `(x, y)` coordinates without moduli.

-

## Rabin Cryptosystem with Polynomial Primes

**Pattern:** Rabin key generator derives `p, q` from a polynomial in a base value `r`, e.g. `p = r^2 + 3`, `q = r^2 + 7`. Modulus `N = p*q` is a polynomial in `r`; solve for `r` via `iroot(N - known_constant, 4)`, then recover both primes and decrypt the four sqrt candidates in the usual way.

```python
from gmpy2 import iroot
# N = (r^2+3)(r^2+7) = r^4 + 10 r^2 + 21
r, _ = iroot(N - 21, 4)
p, q = r*r + 3, r*r + 7
x_p = pow(ct, (p+1)//4, p)
x_q = pow(ct, (q+1)//4, q)
# CRT combine x_p, x_q; flag is the candidate with known padding
```

**Key insight:** Any cryptosystem whose primes come from a polynomial in a small variable collapses under integer-root extraction. Recognize these by plotting `N` against hypothetical `r` guesses, or by seeing suspicious constant differences.

-

## LCG Period Detection for Unlimited Output Prediction

**Pattern:** Server uses an LCG for RNG with a short period. Send repeated requests until you see a previously-observed output — you've found the period. From that point forward, every future value is known because the LCG cycles.

```python
seen = {}
for i in itertools.count():
    v = fetch_next()
    if v in seen:
        period = i - seen[v]
        break
    seen[v] = i
# Now predict: future[i] == history[(i - period_start) % period]
```

**Key insight:** All LCGs are periodic and the period is bounded by `m`. Any output buffer long enough to contain the period gives you free prediction for the rest of the game.

-

## Polynomial Coefficient Recovery via Vandermonde Linear System

**Pattern:** Oracle evaluates a hidden degree-`n` polynomial at `n+1` points. Build the Vandermonde matrix of evaluation inputs and solve the linear system for coefficients; recovered polynomial reveals the secret constants.

```python
from sage.all import matrix, vector, GF
pts = [(x_i, f(x_i)) for x_i in range(degree+1)]
A = matrix([[xi**k for k in range(degree+1)] for xi, _ in pts])
b = vector([yi for _, yi in pts])
coeffs = A.solve_right(b)
```

**Key insight:** Any secret polynomial, Shamir-style sharing, or "interpolate a curve" oracle falls to a Vandermonde solve with `degree + 1` points. Sage's `solve_right` handles huge degrees.

-

## Rabin Decryption via Four-Roots CRT Combination

**Pattern:** Rabin encrypts `c = m^2 mod n` with `n = p*q` and `p, q ≡ 3 mod 4`. Once `p, q` are recovered (here by Fermat-style square-root search because `q = nextPrime(p+1)` sits right next to `p`), compute `mp = c^((p+1)/4) mod p` and `mq = c^((q+1)/4) mod q`, then combine via extended GCD to yield four square roots `±r, ±s`. Only one of the four decodes to readable text — that's the plaintext.

```python
from Crypto.Util.number import inverse

def ext_gcd(a, b):
    c0, c1, a0, a1, b0, b1 = a, b, 1, 0, 0, 1
    while c1:
        q, r = divmod(c0, c1)
        c0, c1 = c1, r
        a0, a1 = a1, a0 - q * a1
        b0, b1 = b1, b0 - q * b1
    return a0, b0, c0

# p, q already recovered (e.g. via Fermat: p ~ sqrt(n))
pe, qe = (p + 1) // 4, (q + 1) // 4
mp, mq = pow(c, pe, p), pow(c, qe, q)
yp, yq, _ = ext_gcd(p, q)                      # yp*p + yq*q == 1

r1 = (yp * p * mq + yq * q * mp) % n
r2 = n - r1
s1 = (yp * p * mq - yq * q * mp) % n
s2 = n - s1

for cand in (r1, r2, s1, s2):
    try:
        pt = bytes.fromhex(hex(cand)[2:])
        if pt.isascii(): print(pt)            # pick the readable one
    except Exception: pass
```

**Key insight:** Rabin decryption inherently produces four candidates because `x^2 ≡ c mod n` has four roots mod `n = p*q`. When `p, q ≡ 3 mod 4`, per-prime roots are the closed-form exponentiation `c^((p+1)/4) mod p` — no Tonelli-Shelanks needed. Combine with Bezout coefficients `yp*p + yq*q = 1` to get the four CRT candidates `±(yp*p*mq ± yq*q*mp) mod n`, and select by plaintext sanity (ASCII, magic bytes, known prefix). The four-root ambiguity is why Rabin typically needs redundancy in the plaintext to be useful as a cryptosystem.
