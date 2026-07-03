# RSA Technique Reference

Decision tree and operational workflow for RSA weak-key attacks and exploitation.

## Overview: RSA Attack Categories

RSA breaks into two families:

1. **Factorization-based**: recover `p` and `q` from `n`, then compute `d` and decrypt.
2. **Non-factorization**: exploit weak exponents, oracle leaks, or implementation flaws without directly factoring `n`.

**Decision logic**: start with non-factorization checks (faster, less compute). If they fail, escalate to factorization.

---

## Category 1: Non-Factorization Attacks

These require only public material and do not factor `n`.

### 1.1 Small Public Exponent (e = 3, 5, 17)

**Preconditions:**
- `e` is small (typically 3, 5, 17).
- Ciphertext `c = m^e mod n`.
- **Critical**: `m^e < n` (plaintext is short relative to modulus).

**Why it works:**
If `m^e < n`, then `c = m^e` (no modular reduction). Recover `m` by taking the `e`-th root of `c`.

**Operational:**

```python
from Crypto.Util.number import long_to_bytes
import math

# Check if m^e < n is likely
# (e.g., if n is 2048 bits and e=3, plaintext must be < 683 bits)

c = <ciphertext_integer>
e = 3

# Compute integer cube root
m = int(round(c ** (1/e)))

# Validate: check if m^e == c
if pow(m, e) == c:
    plaintext = long_to_bytes(m)
    print(plaintext)
else:
    # Floating-point error; refine with Newton's method
    m = <refine_with_newtons_method>(c, e)
```

**When to suspect:**
- Problem statement says "e is small" or "secure exponent was not used."
- Ciphertext < 683 bits (for 2048-bit n and e=3).
- Plaintext is not padded (OAEP, PKCS#1 v1.5).

**Tool**: `offensive-tools/cryptography/sagemath/` with Sage's `nth_root()` or custom Newton's method.

---

### 1.2 Wiener's Attack (Small Private Exponent)

**Preconditions:**
- `d < n^0.25` (extremely small private exponent).
- You have `n` and `e`.
- You do **not** need to directly know or factor `n`.

**Why it works:**
If `d` is small, it appears in the continued fraction expansion of `e/n`. Use CF to recover `p` and `q`.

**Operational:**

```python
from Crypto.Util.number import long_to_bytes
from fractions import Fraction

def wiener_attack(e, n):
    """Recover p, q, d if d < n^0.25"""
    cf = continued_fraction(Fraction(e, n))
    for k, d in convergents_for_d(cf):
        phi = (e * d - 1) // k
        # Solve x^2 - (n - phi + 1)*x + n = 0
        b = n - phi + 1
        discriminant = b*b - 4*n
        if discriminant >= 0:
            sqrt_disc = int(discriminant ** 0.5)
            if sqrt_disc * sqrt_disc == discriminant:
                p = (b + sqrt_disc) // 2
                q = (b - sqrt_disc) // 2
                if p * q == n:
                    return p, q, d
    return None

p, q, d = wiener_attack(e, n)
if p and q:
    plaintext = pow(c, d, n)
    print(long_to_bytes(plaintext))
```

**When to suspect:**
- Problem says "private exponent is small" or "non-standard key generation."
- Manual testing: compute `e * d mod φ(n)` and see if small `d` (< 10^30 for 2048-bit) appears in continued fraction.

**Tool**: `offensive-tools/cryptography/rsactftool/` (has Wiener built-in) or `offensive-tools/cryptography/sagemath/`.

---

### 1.3 Common Modulus Attack

**Preconditions:**
- Same `n` shared across multiple keypairs (same organization, weak key gen).
- You have `(e1, c1)` and `(e2, c2)`.
- `gcd(e1, e2) = 1` (exponents must be coprime).

**Why it works:**
If `gcd(e1, e2) = 1`, use Extended Euclidean to find `a, b` such that `a*e1 + b*e2 = 1`.
Then `m = (c1^a * c2^b) mod n`.

**Operational:**

```python
from math import gcd
from Crypto.Util.number import long_to_bytes

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd_val, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd_val, x, y

# Inputs
n = <shared_modulus>
e1, c1 = <first_keypair>
e2, c2 = <second_keypair>

g, a, b = extended_gcd(e1, e2)
if g != 1:
    print("Exponents not coprime; attack fails")
else:
    # Compute m = c1^a * c2^b mod n
    # Handle negative exponents
    if a < 0:
        c1_inv = pow(c1, -1, n)  # Python 3.8+
        m = pow(c1_inv, -a, n) * pow(c2, b, n) % n
    else:
        m = pow(c1, a, n) * pow(c2, b, n) % n
    
    plaintext = long_to_bytes(m)
    print(plaintext)
```

**When to suspect:**
- Multiple RSA keys or certificates share the same modulus.
- Organization uses shared infrastructure (all systems share same `n`).

**Tool**: `offensive-tools/cryptography/sagemath/` or direct Python (as above).

---

### 1.4 Hastad's Broadcast Attack

**Preconditions:**
- **Same plaintext** encrypted with different RSA keys.
- You have `e` ciphertexts `(n1, e, c1), (n2, e, c2), ..., (n_e, e, c_e)`.
- All use the **same small public exponent** `e`.

**Why it works:**
If you encrypt the same message with the same `e` and `e` different moduli, then:
- `c_i ≡ m^e (mod n_i)` for all `i`.
- Use CRT to find `C ≡ m^e (mod n1*n2*...*n_e)`.
- If `m^e < n1*n2*...*n_e`, then `C = m^e` exactly. Take `e`-th root.

**Operational:**

```python
def crt(residues, moduli):
    """Chinese Remainder Theorem"""
    total = 0
    prod = 1
    for m in moduli:
        prod *= m
    for r, m in zip(residues, moduli):
        p = prod // m
        total += r * p * pow(p, -1, m)
    return total % prod

# Inputs: list of (n_i, c_i) for same message, same e
e = 3
ciphertexts = [(n1, c1), (n2, c2), (n3, c3)]

moduli = [n for n, c in ciphertexts]
residues = [c for n, c in ciphertexts]

C = crt(residues, moduli)

# Take e-th root
m = int(round(C ** (1/e)))

plaintext = long_to_bytes(m)
print(plaintext)
```

**When to suspect:**
- Multiple RSA ciphertexts with the same `e`.
- Same plaintext encrypted for broadcast to multiple recipients.

**Tool**: `offensive-tools/cryptography/sagemath/` (CRT and root finding).

---

### 1.5 Padding Oracle Attacks (Bleichenbacher / Manger)

**Two distinct attacks — do not confuse them:**
- **Bleichenbacher (1998)**: PKCS#1 v1.5 encryption padding oracle (leaks whether plaintext starts with `0x00 0x02`). ~10^6 queries for 1024-bit key. Still relevant (ROBOT 2017/2018 revivals).
- **Manger (2001)**: RSAES-OAEP (PKCS#1 v2.x) oracle (leaks whether the leftmost byte of the OAEP-decoded plaintext is `0x00`). ~1100 queries for 1024-bit key — much faster than Bleichenbacher.

**Preconditions (both):**
- You can submit ciphertexts to an oracle (server, decryption service).
- Oracle leaks a padding/decoding validity bit via error message, status code, or timing.

**Bleichenbacher on PKCS#1 v1.5:**
A valid plaintext is `0x00 0x02 [random non-zero bytes] 0x00 [message]`. Choose blinding factor `s`, submit `(c * s^e) mod n`, and use the oracle response to narrow `[2B, 3B)` where `B = 2^(8*(k-2))`.

**Manger on OAEP:**
The oracle only tells you whether `f^d mod n < B = 2^(8*(k-1))` (i.e., MSB is 0). Halve the search interval each step with a chosen multiplier.

**Operational (high-level, Bleichenbacher):**

1. **Phase 1**: Find `s_1` such that `(c * s_1^e) mod n` yields a PKCS#1-conforming plaintext.
2. **Phase 2**: Narrow the set of possible messages using additional oracle queries.
3. **Phase 3**: Recover plaintext when the interval reduces to a single value.

```python
# Simplified illustration (real Bleichenbacher is more involved)
def padding_oracle(ct_int, n, e):
    """Returns True if decryption has valid PKCS#1 v1.5 padding"""
    m = pow(ct_int, d, n)  # We're the oracle
    return is_valid_pkcs1_padding(m)

# Phase 1: find blinding s_1 that yields a conforming plaintext
s = 1
while not padding_oracle((pow(s, e, n) * c) % n, n, e):
    s += 1

# Phase 2-3: interval narrowing per Bleichenbacher §3.2
# (Implementation requires careful oracle calls and state management)
```

**When to suspect:**
- A decryption server or service reveals padding-validity behavior.
- Timing differences between valid/invalid padding.
- Error messages like "bad padding" vs. "decryption OK."
- OAEP in use → target Manger, not Bleichenbacher.

**Tool**: `offensive-tools/cryptography/sagemath/` (for modular arithmetic) + custom oracle harness (pwntools).

---

## Category 2: Factorization-Based Attacks

Factor `n` into `p * q`, then recover `d`.

### 2.1 Pollard's p-1 Factorization

**Preconditions:**
- `p - 1` has small prime factors (or `q - 1`).
- Example: `p - 1 = 2 * 3 * 5 * 7 * 11 * 13 * ...` (all factors < bound).

**Why it works:**
If `p - 1` is `B`-smooth (all factors < B), then `a^(B!) ≡ 0 (mod p)` for any `a` not divisible by `p`.
Compute `gcd(a^(B!) - 1, n)` to recover `p`.

**Operational:**

```python
from math import gcd

def pollard_p_minus_1(n, B=100000):
    """Attempt factorization if p-1 is B-smooth"""
    a = 2
    # Compute a^(B!) mod n
    for i in range(2, B):
        a = pow(a, i, n)
    
    factor = gcd(a - 1, n)
    if 1 < factor < n:
        return factor
    return None

p = pollard_p_minus_1(n)
if p:
    q = n // p
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    m = pow(c, d, n)
    plaintext = long_to_bytes(m)
    print(plaintext)
```

**When to suspect:**
- Problem statement hints "small factors in p-1" or shows weak key generation.
- Manual check: factor a few `p - 1` candidates (if available) to see if smooth.

**Tool**: `offensive-tools/cryptography/rsactftool/` (has Pollard p-1 built-in).

---

### 2.2 Fermat Factorization

**Preconditions:**
- `p` and `q` are close (consecutive bits, near squares).
- Example: `p ≈ 2^1024` and `q ≈ 2^1024` (very close values).

**Why it works:**
If `p ≈ q`, then `n = p*q ≈ (p+q)^2 / 4`. Solve for `p` and `q` via `(p+q)/2` iteration.

**Operational:**

```python
def fermat_factor(n):
    """Factor n if p and q are close"""
    x = int(n**0.5)
    if x * x == n:
        return x, x  # Perfect square
    
    while True:
        x += 1
        y2 = x*x - n
        y = int(y2**0.5)
        if y*y == y2:
            p = x + y
            q = x - y
            if p * q == n:
                return p, q
            # Backtrack if too far
            if x > n**0.5 + 1000000:
                return None
    return None

p, q = fermat_factor(n)
if p and q:
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    m = pow(c, d, n)
    plaintext = long_to_bytes(m)
```

**When to suspect:**
- Problem mentions "consecutive primes" or "primes of similar size."
- Manual inspection: check if `sqrt(n)` is very close to an integer.

**Tool**: `offensive-tools/cryptography/rsactftool/` or `offensive-tools/cryptography/sagemath/`.

---

### 2.3 Elliptic Curve Method (ECM)

**Preconditions:**
- `n` has a small factor (100–1000 bits).
- Pollard p-1 and trial division have failed.

**Why it works:**
ECM uses elliptic curve point multiplication over modular arithmetic. By varying curves and parameters, you find factors faster than generic methods.

**Operational:**

```bash
# Use a dedicated ECM tool (not hand-coding)
# Typical: "ecm" command-line tool

# Input: n
# Output: factors

# Example: find a 60-bit factor in a 2048-bit number
# ecm -pm1 1e6 n  # Pollard p-1 variant
# ecm -ecm 1e7 n  # ECM variant
```

**When to suspect:**
- Pollard p-1 failed but you suspect a small factor exists.
- Key generation, metadata, or factor-size signals suggest a hidden small factor.

**Tool**: `offensive-tools/cracking/*` (has ECM integrations).

---

### 2.4 Quadratic Sieve (QS) / General Number Field Sieve (GNFS)

**Preconditions:**
- `n` is "hard" (no small factors, not Fermat-able, etc.).
- You have significant compute (hours to weeks).

**Why it works:**
QS and GNFS find factor by constructing a linear dependency mod `n`. Highly optimized, but beyond manual implementation.

**Operational:**

```bash
# Use CADO-NFS or msieve for general factorization
# Example: 200-digit number takes ~1000 compute-hours

# Input: n
# Output: p, q
```

**When to suspect:**
- The modulus appears genuinely hard (no weak exponent, no special structure).
- You have days/weeks of compute available.

**Tool**: `offensive-tools/cryptography/rsactftool/` (delegates to CADO-NFS or msieve internally).

---

## Category 3: Advanced Non-Factorization Attacks

### 3.1 Franklin-Reiter Related Message Attack

**Preconditions:**
- `e = 3` (or another small public exponent).
- Two ciphertexts `c1`, `c2` encrypt related messages: `m2 = a*m1 + b` for known constants `a`, `b`.
- Same key `(n, e)`.

**Why it works:**
If `c1 = m1^e mod n` and `c2 = (a*m1 + b)^e mod n`, then `gcd(m - m1, (a*x + b)^e - c2)` computed over the polynomial ring `Z_n[x]` reveals `m1`.

**Operational:**

```python
from sage.all import *

def franklin_reiter(n, e, c1, c2, a, b):
    """Recover m1 from two related RSA ciphertexts (m2 = a*m1 + b)."""
    R.<x> = PolynomialRing(Zmod(n))
    f1 = x^e - c1
    f2 = (a*x + b)^e - c2
    # GCD of polynomials over Z_n reveals the plaintext
    def pgcd(g1, g2):
        while g2:
            g1, g2 = g2, g1 % g2
        return g1.monic()
    g = pgcd(f1, f2)
    if g.degree() == 1:
        m1 = int(-g[0])
        return m1
    return None

# e=3, m2 = m1 + 1 (a=1, b=1)
m1 = franklin_reiter(n, e=3, c1=c1, c2=c2, a=1, b=1)
```

**When to suspect:**
- Server encrypts `m` and `m + r` (e.g., with random padding added to the same plaintext).
- Two signatures or ciphertexts relate by a known linear function.

---

### 3.2 gcd(e, phi(n)) > 1 — Partial Decryption

**Preconditions:**
- `gcd(e, phi(n)) = g > 1`.
- Standard `d = e^-1 mod phi(n)` does not exist.
- `n` is factored (or small), allowing you to compute `phi(n)`.

**Why it works:**
Reduce `e' = e / g`. Compute `d' = e'^-1 mod phi(n)`. Decrypt `m^g = c^(d') mod n`, then take the `g`-th root iteratively or via `nthroot_mod`.

**Operational:**

```python
from math import gcd
from sympy.ntheory.residues import nthroot_mod

# Assume p, q known (or n factored)
phi = (p - 1) * (q - 1)
g = gcd(e, phi)
e_prime = e // g
d_prime = pow(e_prime, -1, phi)

m_g = pow(c, d_prime, n)  # = m^g mod n

# Take g-th root mod n (may have multiple solutions)
candidates = nthroot_mod(m_g, g, n, all_roots=True)
for m in candidates:
    try:
        plaintext = bytes.fromhex(hex(m)[2:]).decode('utf-8')
        print(plaintext)
    except:
        pass
```

**When to suspect:**
- `e` is small and `n` has many prime factors all ≡ 1 (mod e).
- Decryption fails with the standard formula because `gcd(e, phi) != 1`.

---

### 3.3 Factoring n from a Multiple of phi(n)

**Preconditions:**
- You have any value `k` that is a multiple of `phi(n)` (e.g., `e*d - 1`, a leaked key, or a protocol error).
- `n = p * q` (biprime).

**Why it works:**
`phi(n) = (p-1)(q-1)` divides `k`. Write `k = 2^s * d` (odd `d`). For random `a`, `a^(k/2)` is a non-trivial square root of 1 mod `n` with probability ≥ 1/2, revealing `p` via `gcd(a^(k/2) - 1, n)`.

**Operational:**

```python
import random
from math import gcd

def factor_from_phi_multiple(n, k):
    """Factor n given any multiple k of phi(n)."""
    s, d = 0, k
    while d % 2 == 0:
        s += 1
        d //= 2
    for _ in range(100):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            prev = x
            x = pow(x, 2, n)
            if x == n - 1:
                break
            if x == 1:
                p = gcd(prev - 1, n)
                if 1 < p < n:
                    return p, n // p
        if x != n - 1:
            p = gcd(x - 1, n)
            if 1 < p < n:
                return p, n // p
    return None

# From a leaked (e, d) pair or any re*rd - 1 value:
k = e * d - 1
p, q = factor_from_phi_multiple(n, k)
```

**When to suspect:**
- Server reveals `d` in a protocol error, or you know a key pair `(e, d)` for the same `n`.
- Leaked partial key material (including from key export bugs).

---

### 3.4 Batch GCD for Shared Prime Factors

**Preconditions:**
- Large set of RSA moduli `n1, n2, ..., nk` (hundreds to millions).
- Some pairs share a prime (due to weak RNG at key generation time).

**Why it works:**
If `gcd(ni, nj) > 1` for any pair, both factor instantly. Naive pairwise GCD is O(k²); product-tree-based batch GCD runs in O(k log²k).

**Operational:**

```python
from math import gcd
from functools import reduce

def batch_gcd(moduli):
    """Find all moduli sharing a prime factor. O(k^2) version for small sets."""
    n = len(moduli)
    factors = {}
    for i in range(n):
        for j in range(i + 1, n):
            g = gcd(moduli[i], moduli[j])
            if g > 1 and g != moduli[i]:
                factors[i] = (g, moduli[i] // g)
                factors[j] = (g, moduli[j] // g)
    return factors

# Large-scale variant: build product tree for O(k log^2 k)
# See: github.com/fionn/batch-gcd (DJB algorithm)
# Original paper: Heninger et al. "Mining Your Ps and Qs" (USENIX Security 2012)

moduli = [n1, n2, n3, ...]  # collected from target PKI or certificate dump
weak = batch_gcd(moduli)
for idx, (p, q) in weak.items():
    d = pow(e, -1, (p-1)*(q-1))
    m = pow(c_list[idx], d, moduli[idx])
    print(f"n[{idx}] cracked: {bytes.fromhex(hex(m)[2:])}")
```

**When to suspect:**
- Target uses many RSA keys generated by the same device or system.
- Embedded systems, routers, IoT devices with weak hardware RNG.
- Certificate dumps from a closed ecosystem.

---

### 3.5 Partial dp/dq Key Recovery

**Preconditions:**
- You have the CRT parameters: `dp = d mod (p-1)`, `dq = d mod (q-1)`, or their partial values.
- `n` is known but not yet factored.

**Why it works:**
If `dp` is known: `e * dp ≡ 1 (mod p-1)`, so `e * dp - 1 = k*(p-1)`. Try values of `k` (usually `k < e`) to recover `p`.

**Operational:**

```python
from math import gcd

def factor_from_dp(n, e, dp):
    """Recover p from n, e, and dp = d mod (p-1)."""
    for k in range(1, e):
        # e * dp - 1 = k * (p - 1)
        p_minus_1 = (e * dp - 1) // k
        if (e * dp - 1) % k != 0:
            continue
        p = p_minus_1 + 1
        if p > 1 and n % p == 0:
            q = n // p
            return p, q
    return None

# Example
p, q = factor_from_dp(n, e, dp)
phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)
m = pow(c, d, n)
```

**When to suspect:**
- CRT private key components leaked (PKCS#8 export, memory dump, side channel).
- Server returns CRT parameters in an error response.

---

### 3.6 RSA Signature Forgery (Multiplicative Homomorphism)

**Preconditions:**
- Signing oracle will sign arbitrary messages **except** the target `m`.
- RSA is used in textbook (unpadded) form.

**Why it works:**
Unpadded RSA is multiplicatively homomorphic: `sign(a) * sign(b) ≡ sign(a*b) mod n`.
If `m = a * b`, request signatures for `a` and `b` separately, then multiply them.

**Operational:**

```python
def forge_signature(target_m, n, sign_oracle):
    """Forge signature for target_m by factoring into signable parts."""
    # Find a divisor that the oracle will sign
    for divisor in range(2, 1000):
        if target_m % divisor == 0:
            part1 = divisor
            part2 = target_m // divisor
            # Verify oracle accepts both parts
            sig1 = sign_oracle(part1)
            sig2 = sign_oracle(part2)
            if sig1 and sig2:
                forged = (sig1 * sig2) % n
                return forged
    return None
```

**When to suspect:**
- Signing oracle with a blacklist (refuses to sign the exact target but accepts factors).
- Unpadded or "textbook" RSA signatures in the protocol.

---

### 3.7 Coppersmith: Linearly Related Primes

**Preconditions:**
- RSA primes satisfy a known linear relation: `q = a*p + b` for small known constants.
- Or more generally: a polynomial relationship between `p` and `q`.

**Why it works:**
Substitute `q = a*p + b` into `n = p*q`. This gives a quadratic in `p`. Use Coppersmith's `small_roots()` on the polynomial `p*(a*p + b) - n`.

**Operational:**

```python
from sage.all import *

def coppersmith_related_primes(n, a, b, bits_p):
    """Factor n when q ≈ a*p + b using Coppersmith's method."""
    P.<x> = PolynomialRing(ZZ)
    # n = x * (a*x + b), so a*x^2 + b*x - n = 0 mod n
    f = a * x^2 + b * x - n
    # Reduce modulo a factor of n (use Zmod)
    R.<y> = PolynomialRing(Zmod(n))
    g = a * y^2 + b * y - n
    roots = g.small_roots(X=2^(bits_p // 2), beta=0.4)
    for r in roots:
        if r > 0 and n % r == 0:
            p = int(r)
            q = n // p
            return p, q
    return None
```

**When to suspect:**
- Problem shows two primes generated from a shared seed or a recurrence.
- Primes differ by a small constant or have a visible linear relationship.

---

## Decision Tree

```
START: You have n, e, c.

Q1: Is e small (3, 5, 17)?
  YES → Try cube/fifth root (§1.1)
        Do you have two related ciphertexts? → Franklin-Reiter (§3.1)
  NO → Continue

Q2: Can you measure timing / error from oracle?
  YES → Padding oracle (§1.5)
  NO → Continue

Q3: Do you have another (n, e', c') with same n?
  YES → Common modulus attack (§1.3)
  NO → Continue

Q4: Do you have e ciphertexts with same e and message?
  YES → Hastad broadcast (§1.4)
  NO → Continue

Q5: Does d appear small? (infer from problem statement)
  YES → Wiener's attack (§1.2)
  NO → Continue

Q6: Do you have a signing oracle?
  YES → RSA homomorphic forgery (§3.6)
  NO → Continue

Q7: Do you have dp, dq, or a multiple of phi(n)?
  YES (dp/dq) → Factor via dp recovery (§3.5)
  YES (phi multiple) → Factor from phi multiple (§3.3)
  NO → Continue

Q8: Are primes linearly related?
  YES → Coppersmith linearly-related primes (§3.7)
  NO → Continue

Q9: Large set of keys from same ecosystem?
  YES → Batch GCD for shared primes (§3.4)
  NO → Continue

Q10: gcd(e, phi(n)) > 1?
  YES → Partial decryption via nthroot_mod (§3.2)
  NO → Continue

Q11: Factorization
  Q11.1: Does p-1 or q-1 have small factors?
    YES → Pollard p-1 (§2.1)
    NO → Continue
  Q11.2: Are p and q close?
    YES → Fermat factorization (§2.2)
    NO → Continue
  Q11.3: Use RSA tool (rsactftool) for full factorization
    → Attempts: Pollard rho, ECM, QS, GNFS in sequence
    → Return factors p, q
    → Recover d and decrypt

DECRYPT:
  d = pow(e, -1, (p-1)*(q-1))
  m = pow(c, d, n)
  plaintext = bytes_from_int(m)
```

---

## Output Validation

Once you've recovered plaintext:

1. **Check encoding**: is it UTF-8, ASCII, or binary?
2. **Check format**: does it look like a secret, key, file header, or valid protocol message?
3. **Re-encrypt**: compute `m^e mod n` and verify it equals original `c`.
4. **If multiple candidates**: test all against the oracle or service.

---

## Common Pitfalls

- Assuming `e` is always 65537. Weak keys use smaller `e`.
- Forgetting to validate padding before decrypting. Custom padding may differ from PKCS#1.
- Running factorization when non-factorization works faster (e.g., small `e` first).
- Using weak RNG for `a` in Pollard p-1. Use `a=2` consistently.

