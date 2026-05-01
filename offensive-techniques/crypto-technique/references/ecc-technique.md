# ECC and DSA Technique Reference

Decision tree and operational workflow for Elliptic Curve Cryptography (ECC) and DSA attacks.

---

## Overview: ECC Attack Categories

ECC breaks reduce to:

1. **Discrete Log Problem (DLP) solving**: recover private key `x` from public point `Q = x*G`.
2. **Signature attack**: exploit weak nonces, nonce reuse, or implementation flaws.
3. **Curve property exploitation**: singular curves, anomalous curves, small-order subgroups.

---

## Category 1: ECDLP (Elliptic Curve Discrete Log Problem)

### 1.1 Pohlig-Hellman Attack (Smooth Curve Order)

**Preconditions:**
- Curve order `n` is smooth (factors into small primes).
- Example: `n = 2^30 * 3^20 * 5^15 * 7^10 * ...`

**Why it works:**
Solve discrete log in each small subgroup separately, then use CRT to combine solutions.

**Operational:**

```python
from sage.all import *

# Curve and public key
E = EllipticCurve(GF(p), [a, b])
G = E(Gx, Gy)  # Base point
Q = E(Qx, Qy)  # Public key

# Get curve order
n = E.order()

# Factor order
factors = factor(n)  # Returns [(p1, e1), (p2, e2), ...]

# Solve DLP in each subgroup and CRT combine
dlogs = []
for prime_factor, exponent in factors:
    # Reduce to subgroup of order prime_factor
    cofactor = n // (prime_factor ** exponent)
    G_reduced = cofactor * G
    Q_reduced = cofactor * Q
    
    # Solve DLP in small subgroup
    x_prime = discrete_log(Q_reduced, G_reduced, operation='+')
    dlogs.append((x_prime, prime_factor ** exponent))

# CRT combine
x = crt([d for d, _ in dlogs], [m for _, m in dlogs])
print(f"Private key: {x}")

# Verify
assert x * G == Q
```

**When to suspect:**
- Problem gives curve order `n` and it's clearly smooth (many small factors).
- Curve is non-standard or custom-defined.

**Tool**: `offensive-tools/cryptography/sagemath/` (Sage's `discrete_log()` and CRT).

---

### 1.2 Small Subgroup Attack

**Preconditions:**
- Curve has a cofactor `h > 1` (order of curve is `h * n` where `n` is prime).
- You can control point multiplication or repeated encryption.
- Example: Curve25519 has cofactor 8.

**Why it works:**
If attacker can choose points of small order (in the subgroup of order `h`), they can recover the private key mod `h`.

**Operational:**

```python
from sage.all import *

# Curve with cofactor
E = EllipticCurve(GF(p), [a, b])
cofactor = E.order() / (large_prime)  # h = cofactor

# Find a point of order cofactor (or divisor of it)
# Trial: multiply random point by (order / divisor)
R = E.random_element()
for divisor in divisors(cofactor):
    T = (E.order() // divisor) * R
    if T.order() == divisor:
        print(f"Found point of order {divisor}")
        break

# If we can make the target sign/encrypt with T:
# secret_recovered_mod_divisor = recover_from_small_order_attack(T)

# Repeat for different divisors of cofactor, CRT combine
```

**When to suspect:**
- Curve has cofactor > 1 (check curve specs).
- Protocol allows you to choose or influence public key choices.

**Tool**: `offensive-tools/cryptography/sagemath/`.

---

### 1.3 Singular Curves and Additive Reduction

**Preconditions:**
- Curve is singular: discriminant `4*a^3 + 27*b^2 ≡ 0 (mod p)`.
- Example: `y^2 = x^3` (cusp) or `y^2 = x^2*(x+1)` (node).

**Why it works:**
A cusp maps to the additive group Z/pZ (trivially solved DLP). A node maps to the multiplicative group GF(p)* (solved by standard DLP). Both are drastically weaker than ECDLP on non-singular curves.

**Detection:**
```python
a, b = <curve_params>
disc = (4 * a**3 + 27 * b**2) % p
if disc == 0:
    print("SINGULAR curve — ECDLP is easy")
```

**Cusp reduction (y^2 = x^3): map to additive group Z/pZ:**
```python
def singular_cusp_to_additive(x, y, p):
    """Map a point (x, y) on y^2=x^3 to an element of Z/pZ."""
    return (x * pow(y, -1, p)) % p

# After mapping:
# G_mapped = cusp_map(Gx, Gy, p)
# Q_mapped = cusp_map(Qx, Qy, p)
# Private key x = Q_mapped * inverse(G_mapped, p) mod p
G_mapped = singular_cusp_to_additive(Gx, Gy, p)
Q_mapped = singular_cusp_to_additive(Qx, Qy, p)
x = (Q_mapped * pow(G_mapped, -1, p)) % p
```

**Node reduction (y^2 = x^3 + x^2): map to multiplicative group GF(p)*:**
```python
from sage.all import GF, Mod, discrete_log

def singular_node_to_multiplicative(px, py, alpha, p):
    """Map a point on a nodal cubic to GF(p)* for alpha = sqrt(a) mod p."""
    # alpha is the "slope" of the node tangent
    t = (py - alpha * px) * pow(py + alpha * px, -1, p) % p
    return t

# Solve DLP in GF(p)*
G_t = singular_node_to_multiplicative(Gx, Gy, alpha, p)
Q_t = singular_node_to_multiplicative(Qx, Qy, alpha, p)
x = discrete_log(Mod(Q_t, p), Mod(G_t, p))
```

**When to suspect:**
- Curve is custom or unusual (not secp256k1, P-256, Curve25519, etc.).
- Challenge computes discriminant as zero or nearly zero.

**Tool**: `offensive-tools/cryptography/sagemath/`.

---

### 1.4 Anomalous Curves (Order = p) — Smart's Attack

**Preconditions:**
- Curve order equals field size `p` (anomalous).
- `#E(GF(p)) = p`.

**Why it works:**
Smart's attack lifts points to the p-adics and computes a "p-adic logarithm" that maps the ECDLP into a DLP in Z/pZ (additive group), which is trivially solvable in O(1) operations.

**Sage automatic (use this first):**
```python
from sage.all import *
E = EllipticCurve(GF(p), [a, b])
G = E(Gx, Gy)
Q = E(Qx, Qy)
if E.order() == p:
    secret = G.discrete_log(Q)  # Sage handles anomalous automatically
    print(f"Private key: {secret}")
```

**Manual p-adic lift (when Sage's auto method fails):**
```python
from sage.all import *

def smart_attack(p, a, b, Gx, Gy, Qx, Qy):
    E = EllipticCurve(GF(p), [a, b])
    Ep = EllipticCurve(pAdicField(p, 2), [a, b])

    # Lift both points to the p-adic field
    Gp_lifts = Ep.lift_x(ZZ(Gx), all=True)
    Qp_lifts = Ep.lift_x(ZZ(Qx), all=True)

    for Gp in Gp_lifts:
        for Qp in Qp_lifts:
            try:
                pG = p * Gp
                pQ = p * Qp
                # Extract p-adic logarithm ratio
                x_G = ZZ(pG[0]) / ZZ(pG[1])
                x_Q = ZZ(pQ[0]) / ZZ(pQ[1])
                secret = int(ZZ(x_Q / x_G) % p)
                if E(Gx, Gy) * secret == E(Qx, Qy):
                    return secret
            except (ZeroDivisionError, ValueError, AttributeError):
                continue
    return None

secret = smart_attack(p, a, b, Gx, Gy, Qx, Qy)
```

**When to suspect:**
- `E.order() == p` — always check this first.
- Challenge generates a custom curve; verify `order` immediately.

**Tool**: `offensive-tools/cryptography/sagemath/`.

---

## Category 2: Signature Attacks

### 2.1 ECDSA Nonce Reuse

**Preconditions:**
- Same nonce `k` used for two different messages.
- You have signatures `(r1, s1, m1)` and `(r2, s2, m2)`.
- `r1 == r2` (same nonce → same `r` value).

**Why it works:**
In ECDSA: `s = k^-1 (H(m) + x*r) mod n`. If `k` reused with different messages:
```
s1 = k^-1 (H(m1) + x*r) mod n
s2 = k^-1 (H(m2) + x*r) mod n

s1 - s2 = k^-1 (H(m1) - H(m2)) mod n
k = (H(m1) - H(m2)) / (s1 - s2) mod n
x = r^-1 * (s*k - H(m)) mod n
```

**Operational:**

```python
from Crypto.Hash import SHA256
from Crypto.Util.number import bytes_to_long, long_to_bytes

# Signatures and messages
m1, m2 = b"message1", b"message2"
r1, s1 = <sig1>
r2, s2 = <sig2>

# Verify r1 == r2 (nonce reuse)
assert r1 == r2, "Nonces not reused; attack fails"

# Hash messages
h1 = bytes_to_long(SHA256.new(m1).digest())
h2 = bytes_to_long(SHA256.new(m2).digest())

# Recover nonce k
k = ((h1 - h2) * pow(s1 - s2, -1, n)) % n
print(f"Nonce k: {k}")

# Recover private key x
x = (r1 * pow(k, -1, n) * (s1*k - h1)) % n
print(f"Private key x: {x}")

# Verify
assert x * G == Q
```

**When to suspect:**
- Multiple ECDSA signatures available.
- Check if `r` values repeat (nonce reuse).

**Tool**: Direct Python or `offensive-tools/cryptography/sagemath/`.

---

### 2.2 Limited Nonce Brute Force

**Preconditions:**
- Nonce `k` drawn from small space (e.g., 1000 values).
- You have signature `(r, s, m)` and partial information about `k`.

**Why it works:**
If nonce space is small, iterate through all candidates and check which one produces the observed signature.

**Operational:**

```python
# Known: signature (r, s), message m
# Unknown: nonce k (assumed to be in range [start, end])

for k_candidate in range(start, end):
    # Check if this k produces the observed signature
    r_check = (k_candidate * G).x() % n
    if r_check == r:
        # Found k; recover x
        x = r^-1 * (s*k_candidate - h) % n
        return x

# Complexity: O(nonce_space_size)
# Feasible for nonce_space < 2^30
```

**When to suspect:**
- PRNG is weak or biased (uses `random.randint()` instead of `secrets`).
- Multiple signatures hint at clustering in nonce values.

**Tool**: Custom Python or hashcat (if nonce space is huge but bounded).

---

### 2.3 DSA with Biased Nonce (Lattice Attack)

**Preconditions:**
- Multiple DSA/ECDSA signatures available.
- Nonce `k` is biased (e.g., high bits are zero or known).

**Why it works:**
Each signature gives a linear constraint on the private key and nonce. Lattice reduction (LLL) can recover both from biased nonces.

**Operational:**

```python
# This is advanced; for simplicity, outline only

# Build constraint matrix: each signature gives equation
# s_i = k_i^-1 (H(m_i) + x*r_i) mod n
# Rearrange to get linear system mod n

# If nonce bits are known/biased, augment constraints
# Use LLL to reduce lattice and find short vectors
# Extract x from reduced basis

# Tool: Sage's LLL implementation
```

**When to suspect:**
- Problem says "nonce bits are known" or "nonce has low entropy."
- Many signatures available (> 10).

**Tool**: `offensive-tools/cryptography/sagemath/` with lattice techniques (see lattice-lwe-technique.md).

---

### 2.4 DSA Nonce Reuse (Classic DSA)

**Preconditions:**
- Classic DSA (not ECDSA) using the same prime-field group.
- Same nonce `k` reused across two signatures `(r, s1, m1)` and `(r, s2, m2)`.

**Why it works:**
DSA: `s = k^-1 * (H(m) + x * r) mod q`. Same `k` gives same `r`. Recover `k` and then `x` using the same algebra as ECDSA.

**Operational:**

```python
from Crypto.Hash import SHA1
from Crypto.Util.number import bytes_to_long

q = <group_order>
r, s1, s2 = <shared_r>, <s1>, <s2>
h1 = bytes_to_long(SHA1.new(m1).digest())
h2 = bytes_to_long(SHA1.new(m2).digest())

k = ((h1 - h2) * pow(s1 - s2, -1, q)) % q
x = (r * pow(k * s1 - h1, -1, q)) % q   # alternate form
# or: x = ((s1 * k - h1) * pow(r, -1, q)) % q
print(f"DSA private key: {x}")
```

**When to suspect:**
- Two DSA signatures share the same `r` value.
- PRNG for nonce generation is deterministic or seeded from a known value.

---

### 2.5 Ed25519 Same-Nonce Key Recovery

**Preconditions:**
- Ed25519 signing oracle that signs with the same deterministic nonce twice — or a system where the nonce derivation is broken (e.g., constant nonce or externally controlled).
- Two messages with signatures that share the same `R` component.

**Why it works:**
Ed25519 normally derives `r` deterministically from the private key and message (RFC 8032). If a broken implementation reuses `r` across messages, the linear relation `S = r + x*H(R, pk, m)` gives the private scalar directly.

**Operational:**

```python
# Ed25519 signature: (R, S) where S = r + x * H(R, A, m) mod l
# l = Ed25519 subgroup order = 2^252 + 27742317777372353535851937790883648493

from hashlib import sha512
from Crypto.Util.number import bytes_to_long

l = 2**252 + 27742317777372353535851937790883648493

def H_ed(R_bytes, pk_bytes, m_bytes):
    h = sha512(R_bytes + pk_bytes + m_bytes).digest()
    return bytes_to_long(h) % l

# If R is the same for two messages (nonce reuse):
# S1 = r + x * H1, S2 = r + x * H2  (mod l)
# S1 - S2 = x * (H1 - H2)
# x = (S1 - S2) * inverse(H1 - H2, l) mod l

R_bytes, pk_bytes = <R>, <public_key_bytes>
S1, S2 = <S1_int>, <S2_int>
H1 = H_ed(R_bytes, pk_bytes, m1)
H2 = H_ed(R_bytes, pk_bytes, m2)

x = ((S1 - S2) * pow(H1 - H2, -1, l)) % l
print(f"Ed25519 private scalar: {x}")
```

**When to suspect:**
- Two Ed25519 signatures share the same `R` point (check the first 32 bytes of each signature).
- Custom Ed25519 implementation that does not follow RFC 8032 nonce derivation.

---

## Category 3: Curve Property Exploitation

### 3.1 Invalid Curve Point Attack

**Preconditions:**
- Attacker can send points not on the curve.
- Curve validation is missing or weak in the implementation.
- Example: server accepts `(x, y)` without checking `y^2 ≡ x^3 + ax + b (mod p)`.

**Why it works:**
Points off the curve may reduce to small-order subgroups. Recover private key mod subgroup order.

**Operational:**

```python
# Find points of small order not on the curve
# Multiply server's response by cofactor of false curve
# Build CRT combine as in Pohlig-Hellman

# Complex; requires understanding server's curve arithmetic
```

**When to suspect:**
- Problem allows arbitrary point input.
- Curve validation is not mentioned or seems missing.

**Tool**: `offensive-tools/cryptography/sagemath/`.

---

## Category 4: ECDLP in Extension Fields

Extension field DLP `GF(p^k)` arises when the problem uses a group of points over a field extension rather than a prime field. The DLP is often structurally easier than over `GF(p)`.

### 4.1 DLP in GF(p^k)

**Preconditions:**
- Scalar multiplication is performed in a group over `GF(p^k)` rather than `GF(p)`.
- Example: a Kewiri-style server sends a factored modulus, asks you to solve a DLP step in `GF(p^3)`.
- Group order factors into small primes (smooth order within the extension field).

**Why it works:**
The multiplicative group of `GF(p^k)` has order `p^k - 1`. If this is smooth, Pohlig-Hellman applies directly. The `log()` function in Sage handles this when given a generator and target element.

**Operational:**

```python
from sage.all import *

# Construct the extension field
p = <prime>
k = 3  # Field extension degree
F = GF(p**k)

# Elements of interest
g = F(<generator_value>)   # Generator of a subgroup
A = F(<target_value>)      # Element whose discrete log you want

# Compute discrete log
# Sage's log() finds the exponent: g^x = A
x = discrete_log(A, g)
print(f"DLP solution: {x}")

# For factored group order (Pohlig-Hellman):
# Sage handles this automatically when group order is smooth
order = g.multiplicative_order()
print(f"Group order: {order} = {factor(order)}")

# If order is smooth, log() will succeed; if not, try subgroup approach
```

**Kewiri-style server protocol (factored DLP request):**
```python
from sage.all import *

# Server sends: p, k, g, A where you must find x s.t. g^x = A in GF(p^k)
p = <prime_from_server>
k = <ext_degree_from_server>
F = GF(p**k)

g_elem = F(<g_from_server>)
A_elem = F(<A_from_server>)

# Solve
x = discrete_log(A_elem, g_elem)
# send x back to server
```

**When to suspect:**
- Problem description involves `GF(p^k)` or "extension field" explicitly.
- Server's math request returns a non-prime modulus whose factors are small primes raised to powers.
- Group order prints as a highly composite number.

---

## Category 5: EC-Based PRNG and Hybrid Attacks

When an elliptic curve is used as the state update function for a PRNG (EC-LCG), the attacker can recover the internal state from a sequence of output points using linearization + LLL.

### 5.1 EC-LCG State Recovery (Blessed Pattern)

**What is EC-LCG:**
An EC-based LCG generates a sequence of points `P_0, P_1, ...` where `P_{i+1} = k * P_i` for a fixed secret scalar `k`. Given several consecutive output points, recover `k`.

**Preconditions:**
- You observe a sequence of EC points `P_0, P_1, P_2, ...` (at least 3).
- Points are generated by `P_{i+1} = k * P_i` mod curve.
- Scalar `k` is the same across rounds.

**Why it works:**
Each step `P_{i+1} = k * P_i` gives a polynomial relation. Collecting multiple steps creates a system of polynomial equations. Use Sage's `Sequence.coefficients_monomials()` to extract the linear system, then LLL to find the short solution corresponding to `k`.

**Operational:**

```python
from sage.all import *

# Setup
p = <curve_prime>
a, b = <curve_params>
E = EllipticCurve(GF(p), [a, b])

# Observed points (3+ consecutive outputs from EC-LCG)
P0 = E(<x0>, <y0>)
P1 = E(<x1>, <y1>)
P2 = E(<x2>, <y2>)

# We know P1 = k*P0, P2 = k*P1
# Let's recover k using the relation:
# x(k * P0) = x1  (modular polynomial in k)
# x(k * P1) = x2

# Create polynomial ring for the scalar
R = PolynomialRing(GF(p), 'k')
k_var = R.gen()

# For small k (or bounded k), enumerate or use Sage's discrete_log directly
# If k is small:
n = E.order()
k_recovered = discrete_log(P1, P0, operation='+', order=n)
print(f"Recovered scalar k: {k_recovered}")

# Verify
assert k_recovered * P0 == P1
assert k_recovered * P1 == P2

# With k recovered, predict next output:
P3_predicted = k_recovered * P2
print(f"Predicted next point: {P3_predicted}")
```

**Linearization via Sequence (Blessed pattern for algebraic state):**
```python
from sage.all import *

# When EC-LCG output is used to derive further algebraic values,
# model each observation as a polynomial in the unknown state.
# Sequence().coefficients_monomials() extracts the linear system.

# Collect polynomial expressions for each observation:
polys = []
for i, obs in enumerate(observations):
    f = <polynomial_in_state_variable_matching_obs>
    polys.append(f - obs)

# Extract coefficient matrix
seq = Sequence(polys)
M, monoms = seq.coefficients_monomials()

# M is a matrix over the base field
# Find the kernel: short vector in kernel = secret state
ker = M.right_kernel()
for v in ker.basis():
    candidate = v
    # Map back to field element
    state_candidate = sum(int(candidate[i]) * m for i, m in enumerate(monoms))
    print(f"Candidate state: {state_candidate}")
```

**When to suspect:**
- Protocol uses the same scalar `k` to generate each step.
- Output is a sequence of points and you have at least 3 consecutive ones.
- Problem text mentions "PRNG seeded with EC scalar" or shows a loop generating EC points.

---

## Category 6: Algebraic Groups — Clock Group DLP

Some protocols implement Diffie-Hellman not on an elliptic curve but on an alternative algebraic group. The clock group (unit circle mod p) is one such structure.

### 6.1 Clock Group (x²+y²=1 mod p)

**Pattern:**
DH-style key exchange uses the unit circle group `{(x,y) : x²+y²=1 mod p}` with multiplication law `(x1,y1)·(x2,y2) = (x1*y2+y1*x2, y1*y2-x1*x2) mod p`. Group order is `p+1`, not `p-1`.

**Why this is weak:**
`p+1` is often smooth (attack if it is), whereas `p-1` is the target for standard DH. The isomorphism to `GF(p²)*` elements of norm 1 means Pohlig-Hellman applies when `p+1` factors into small primes.

**Group operations:**
```python
def clock_mul(P, Q, p):
    """Multiply two points in the clock group mod p."""
    x1, y1 = P
    x2, y2 = Q
    return ((x1*y2 + y1*x2) % p, (y1*y2 - x1*x2) % p)

def clock_pow(P, n, p):
    """Compute n-th power of point P in clock group."""
    result = (0, 1)  # Identity element
    base = P
    while n > 0:
        if n & 1:
            result = clock_mul(result, base, p)
        base = clock_mul(base, base, p)
        n >>= 1
    return result
```

**Attack workflow:**
```python
from math import gcd
from functools import reduce
from sympy.ntheory import factorint
from sympy.ntheory.modular import crt

# Step 1: recover p if unknown (given points on the circle)
def recover_p(known_points):
    vals = [x**2 + y**2 - 1 for x, y in known_points]
    p = reduce(gcd, vals)
    # Remove small spurious factors
    for small in [2, 3, 5, 7, 11, 13]:
        while p % small == 0:
            p //= small
    return p

# Step 2: factor p+1
p = <prime>
order = p + 1
factors = factorint(order)
print(f"p+1 = {order} = {factors}")

# Step 3: Pohlig-Hellman in clock group
G = (<Gx>, <Gy>)   # Generator (base point)
Q = (<Qx>, <Qy>)   # Public key point (target)

residues, moduli = [], []
for prime_factor, exp in factors.items():
    pe = prime_factor ** exp
    cofactor = order // pe
    G_sub = clock_pow(G, cofactor, p)  # Generator of subgroup of order pe
    Q_sub = clock_pow(Q, cofactor, p)  # Target in subgroup

    # Brute-force DLP in small subgroup
    acc = (0, 1)
    for k in range(pe):
        if acc == Q_sub:
            residues.append(k)
            moduli.append(pe)
            break
        acc = clock_mul(acc, G_sub, p)

# Step 4: CRT combine
secret, _ = crt(moduli, residues)
print(f"Private key: {secret}")

# Step 5: verify
assert clock_pow(G, secret, p) == Q
```

**When to suspect:**
- Protocol description uses "circle group", "unit circle", or points satisfy `x²+y²=1 mod p`.
- Server reveals points and performs power-style operations — check if `p+1` is smooth.
- Challenge explicitly names a "clock" or "circular" group.

---

## Decision Tree

```
START: You have curve E (or group G), base point G, public key Q.

Q1: Is curve order smooth (many small prime factors)?
  YES → Pohlig-Hellman (§1.1)
  NO → Continue

Q2: Do multiple ECDSA signatures exist with same r?
  YES → ECDSA nonce reuse → recover private key directly (§2.1)
  NO → Continue

Q3: Do two DSA signatures share the same r value?
  YES → DSA nonce reuse (§2.4)
  NO → Continue

Q4: Do two Ed25519 signatures share the same R bytes?
  YES → Ed25519 same-nonce recovery (§2.5)
  NO → Continue

Q5: Is nonce k likely small or biased?
  YES → Brute force or lattice attack (§2.2, §2.3)
  NO → Continue

Q6: Is curve singular or anomalous?
  YES → Check curve type:
    discriminant == 0 → cusp/node reduction (§1.3)
    order == p → Smart's attack (§1.4)
  NO → Continue

Q7: Is the group over GF(p^k) with k > 1?
  YES → Extension field DLP → Pohlig-Hellman or Sage discrete_log in GF(p^k) (§4.1)
  NO → Continue

Q8: Do you have a sequence of EC points from a PRNG?
  YES → EC-LCG state recovery via discrete_log or linearization (§5.1)
  NO → Continue

Q9: Is the group a clock group (x²+y²=1 mod p)?
  YES → Check if p+1 is smooth → Clock Group Pohlig-Hellman (§6.1)
  NO → Continue

Q10: No direct weaknesses found
  → ECDLP is hard; use best-known algorithms (Pollard rho, Pohlig-Hellman if possible)
  → Or challenge is not exploitable by discrete-log attacks
```

---

## Output Validation

- Recovered private key `x` should satisfy `x * G == Q`.
- For signatures, validate all available signatures with recovered key.

