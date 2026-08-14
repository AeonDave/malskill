# CTF Crypto - Elliptic Curve Attacks

## Table of Contents
- [Small Subgroup Attacks](#small-subgroup-attacks)
- [Invalid Curve Attacks](#invalid-curve-attacks)
- [Singular Curves](#singular-curves)
- [Smart's Attack (Anomalous Curves)](#smarts-attack-anomalous-curves)
- [ECC Fault Injection](#ecc-fault-injection)
- [Clock Group DLP via Pohlig-Hellman]
- [ECDSA Nonce Reuse]
- [Ed25519 Torsion Side Channel]
- [DSA Nonce Reuse for Private Key Recovery]
- [DSA Limited k-Value Brute Force]
- [ECC Shared Prime Factor via GCD]
- [DSA Key Recovery via MD5 Collision on k-Generation]
- [Ed25519 Same-Nonce Key Recovery]
- [Singular Curve ECDLP to Additive/Multiplicative Group]
- [BLS Aggregate Signature Rogue-Key Attack]

-

## Small Subgroup Attacks

- Check curve order for small factors
- Pohlig-Hellman: solve DLP (Discrete Logarithm Problem) in small subgroups, combine with CRT (Chinese Remainder Theorem)

```python
# SageMath ECC basics
E = EllipticCurve(GF(p), [a, b])
G = E.gens()[0]  # generator
order = E.order()
```

**Key insight:** When the curve order has small prime factors, Pohlig-Hellman decomposes the DLP into small subgroup problems solvable independently, then combines results with CRT. Always factor the curve order first - if it is smooth (all small factors), the DLP is trivially solvable.

-

## Invalid Curve Attacks

If point validation is missing, send points on weaker curves. Craft points with small-order subgroups to leak secret key bits.

**Key insight:** Invalid curve attacks exploit missing point-on-curve validation. Send crafted points that lie on a different curve with a small-order subgroup, and the server will compute scalar multiplication on the weak curve, leaking secret key bits modulo the small order.

-

## Singular Curves

If discriminant delta = 0, curve is singular. DLP becomes easy (maps to additive/multiplicative group).

**Key insight:** Check the discriminant `4a^3 + 27b^2 mod p` first. If it is zero, the curve is singular and the ECDLP reduces to a simple discrete log in the additive group (cusp) or multiplicative group (node) of the field, both solvable in polynomial time.

-

## Smart's Attack (Anomalous Curves)

**When to use:** Curve order equals field characteristic p (anomalous curve). Solves ECDLP in O(1) via p-adic lifting.

**Key insight:** Always check `E.order() == p` first. If the curve order equals the field prime, the ECDLP is solved instantly via p-adic lifting (Smart's attack). SageMath's `discrete_log` handles this automatically, but manual p-adic lift code is needed when the built-in method fails.

**Detection:** `E.order() == p` — always check this first!

**SageMath (automatic):**
```python
E = EllipticCurve(GF(p), [a, b])
G = E(Gx, Gy)
Q = E(Qx, Qy)
# Sage's discrete_log handles anomalous curves automatically
secret = G.discrete_log(Q)
```

**Manual p-adic lift (when Sage's auto method fails):**
```python
def smart_attack(p, a, b, G, Q):
    E = EllipticCurve(GF(p), [a, b])
    Qp = pAdicField(p, 2)  # p-adic field with precision 2
    Ep = EllipticCurve(Qp, [a, b])

    # Lift points to p-adics
    Gp = Ep.lift_x(ZZ(G[0]), all=True)  # try both lifts
    Qp_point = Ep.lift_x(ZZ(Q[0]), all=True)

    for gp in Gp:
        for qp in Qp_point:
            try:
                # Multiply by p to get points in kernel of reduction
                pG = p * gp
                pQ = p * qp
                # Extract p-adic logarithm
                x_G = ZZ(pG[0] / pG[1]) / p  # or pG.xy()
                x_Q = ZZ(pQ[0] / pQ[1]) / p
                secret = ZZ(x_Q / x_G) % p
                if E(G) * secret == E(Q):
                    return secret
            except (ZeroDivisionError, ValueError):
                continue
    return None
```

**Multi-layer decryption after key recovery:** Challenge may wrap flag in AES-CBC + DES-CBC or similar — just busywork once the ECC key is recovered. Derive keys with SHA-256 of shared secret.

-

## ECC Fault Injection

**Pattern:** Bit flip during ECC computation reveals private key bits.

**Attack:** Compare correct vs faulty ciphertext, recover key bit-by-bit:
```python
# For each key bit position:
# If fault at bit i changes output -> key bit i affects computation
# Binary distinguisher: faulty_output == correct_output -> bit is 0
```

-

## Clock Group DLP via Pohlig-Hellman

**Pattern:** Diffie-Hellman on unit circle group: x^2 + y^2 = 1 (mod p).

**Key facts:**
- Group law: (x1,y1) * (x2,y2) = (x1*y2 + y1*x2, y1*y2 - x1*x2)
- **Group order = p + 1** (not p - 1!)
- Isomorphic to GF(p^2)* elements of norm 1

**Group operations:**
```python
def clock_mul(P, Q, p):
    x1, y1 = P
    x2, y2 = Q
    return ((x1*y2 + y1*x2) % p, (y1*y2 - x1*x2) % p)

def clock_pow(P, n, p):
    result = (0, 1)  # identity
    base = P
    while n > 0:
        if n & 1:
            result = clock_mul(result, base, p)
        base = clock_mul(base, base, p)
        n >>= 1
    return result
```

**Recovering hidden prime p:**
```python
# Given points on the curve, p divides (x^2 + y^2 - 1)
from math import gcd
vals = [x**2 + y**2 - 1 for x, y in known_points]
p = reduce(gcd, vals)
# May need to remove small factors
```

**Attack when p+1 is smooth:**
```python
# 1. Recover p from points: gcd(x^2 + y^2 - 1) across known points
# 2. Factor p+1 into small primes
# 3. Pohlig-Hellman: solve DLP in each small subgroup, CRT combine
# 4. Compute shared secret, derive AES key (e.g., via MD5)
```

**Identification:** the prompt mentions "clock", "circle", or gives points satisfying x^2+y^2=1. Always check if p+1 (not p-1) is smooth.

-

## Ed25519 Torsion Side Channel

**Pattern:** Ed25519 signing oracle derives per-user keys as `user_key = MASTER_KEY * uid mod l` (where `l` is the Ed25519 subgroup order). Goal: recover `MASTER_KEY` from oracle queries.

**The attack exploits Ed25519's cofactor h=8:**
- Full curve order = `8*l`, but scalars are reduced mod `l`
- When `MASTER_KEY * 2^t` wraps around `l`, multiplication produces a torsion component visible as y-coordinate change

**Key extraction via binary decomposition:**
```python
# Query sign(uid=3, 2^t) for t = 0..255
# S_t = (MASTER_KEY * 2^t mod l) * P3
# Check: does doubling S_t match S_{t+1}?

bits = []
for t in range(255):
    S_t = query_sign(3, 2**t)
    S_t1 = query_sign(3, 2**(t+1))
    doubled = point_double(S_t)
    # Wrap occurred if doubled.y != S_{t+1}.y (torsion shift)
    bits.append(0 if doubled.y == S_t1.y else 1)

# Reconstruct: MASTER_KEY ≈ l * (0.bit0 bit1 bit2...)_binary
# Try all 8 torsion corrections for exact value
```

**Key insight:** Ed25519's cofactor creates an observable side channel: when scalar multiplication wraps around the subgroup order `l`, the result shifts by a torsion element (one of 8 points). By querying powers of 2 and checking y-coordinate consistency, each bit of the secret scalar is leaked. Libraries like `ecpy` that reduce mod `l` are vulnerable to this when used in multi-user key derivation schemes.

**Detection:** Ed25519 signing oracle with user-controlled UID or multiplier. Key derivation formula `key = master * uid mod l`.

-

## ECDSA Nonce Reuse

**Pattern:** ECDSA signatures on secp256k1 with constant nonce `k`. When two signatures share the same `r` value, the nonce and private key are recoverable.

**Recovery:**
```python
from hashlib import sha256

# Two signatures (r, s1) and (r, s2) with same r → same nonce k
h1 = int(sha256(msg1).hexdigest(), 16)
h2 = int(sha256(msg2).hexdigest(), 16)
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # secp256k1 order

k = ((h1 - h2) * pow(s1 - s2, -1, n)) % n
d = ((s1 * k - h1) * pow(r, -1, n)) % n  # private key
```

**Key insight:** Same `r` value across multiple ECDSA signatures means the nonce `k` was reused. This is the same class of bug that compromised the PlayStation 3 signing key. Always check for repeated `r` values in signature datasets.

**Detection:** Multiple ECDSA signatures with identical `r` component. the prompt mentions "nonce", "deterministic signing", or provides a signing oracle.

-

## ECDSA Partially-Known Nonce (Hidden Number Problem)

**Pattern:** nonces are not reused but are *biased* — the top or bottom bits are fixed, leaked, or derived from a counter/timestamp. Every `r` differs, so the reuse check finds nothing. Look for an oracle that discloses nonce structure (`{"high_parts":[...], "low_bits":128}`), a truncated RNG, or `k` built from a short random field.

**Reduction (eliminate the key first — keeps the lattice small).** With `k_i = A_i + u_i` where `A_i` is known and `0 <= u_i < B`, each signature gives `s_i·k_i = h_i + r_i·d (mod n)`. Solve signature 0 for `d`, substitute into signature `i`, and every unknown key term cancels:

```python
c       = pow(r0, -1, n) * ri % n
alpha_i = c * s0 % n * pow(si, -1, n) % n
beta_i  = (hi + c * (s0 * A0 - h0) - si * Ai) % n * pow(si, -1, n) % n
# u_i = alpha_i * u_0 + beta_i (mod n),  all u < B
```

Then recover `u_0` as a short vector of the `(m+1)`-dimensional lattice whose rows are
`[1, alpha_2, …, alpha_m, 0]`, `n·e_i` for each `i`, and `[0, beta_2, …, beta_m, B]`; the target lattice point is `(u_0, …, u_m, B)`. Finally `d = (s0·(A0+u_0) - h0) · r0⁻¹ mod n`.

**How many signatures:** the attack needs `B^m < n^(m-1)`, so with `B = sqrt(n)` (half the bits known) `m >= 3`; use 5–6 for margin. A 1-bit bias needs hundreds and BKZ rather than LLL.

**Validate, don't assume:** derive the public key/address from each candidate `d` and compare against the known signer — LLL returns several short vectors and only one is the key.

**Detection:** a signing oracle that publishes nonce metadata, "biased nonce" wording, nonces described as counter-derived, or many signatures with distinct `r` where reuse recovery fails.

-

## DSA Nonce Reuse for Private Key Recovery

**Pattern:** Two DSA (Digital Signature Algorithm) signatures sharing the same nonce k (same r value) leak the private key. Identical in principle to ECDSA nonce reuse but uses DSA-specific group parameters.

```python
# Two signatures (r, s1, H(m1)) and (r, s2, H(m2)) with same r
k = ((H_m1 - H_m2) * pow(s1 - s2, -1, q)) % q
x = ((s1 * k - H_m1) * pow(r, -1, q)) % q  # private key
# Then forge signatures for arbitrary messages
```

**Key insight:** DSA nonce reuse is identical in principle to ECDSA nonce reuse. Look for repeated r values in any DSA/ECDSA signature set. The same recovery formula applies to both.

-

## DSA Limited k-Value Brute Force

DSA implementation generates k from a restricted space (e.g., only 1024 possibilities). Given multiple signatures, brute-force k values and solve for the private key.

```python
from Crypto.Util.number import inverse

def recover_dsa_key(signatures, q, g, p):
    """Recover DSA private key when k has limited possible values"""
    (r1, s1, h1), (r2, s2, h2) = signatures[0], signatures[1]

    for k1 in range(1, 1024):
        for k2 in range(1, 1024):
            # From DSA: s = k^-1 * (h + x*r) mod q
            # With two signatures: x = (s2*k2*h1 - s1*k1*h2) / (s1*k1*r2 - s2*k2*r1) mod q
            num = (s2 * k2 * h1 - s1 * k1 * h2) % q
            den = (s1 * k1 * r2 - s2 * k2 * r1) % q
            if den == 0:
                continue
            x = (num * inverse(den, q)) % q
            # Verify: check if r1 == (g^k1 mod p) mod q
            if pow(g, k1, p) % q == r1:
                return x
    return None
```

**Key insight:** Standard DSA nonce reuse attacks require k1 == k2. When k values are drawn from a small space (e.g., 1024 values), brute-force all (k1, k2) pairs across two signatures to solve the linear system for private key x.

-

## ECC Shared Prime Factor via GCD

Multiple ECC public keys generated with a flawed prime generator that filters `prime % 3 == 2`, reducing the keyspace enough for shared factors to appear.

```python
from math import gcd
from Crypto.Util.number import inverse

# Collect moduli from multiple ECC public keys
moduli = [key.n for key in public_keys]

# Find shared factors via pairwise GCD
for i in range(len(moduli)):
    for j in range(i + 1, len(moduli)):
        g = gcd(moduli[i], moduli[j])
        if 1 < g < moduli[i]:
            p = g
            q = moduli[i] // p
            print(f"Key {i} factored: p={p}, q={q}")
            # Now decrypt using recovered factors
```

**Key insight:** When a prime generator excludes primes based on modular conditions (e.g., `p % 3 == 2`), the reduced keyspace makes GCD collisions between independently generated keys much more likely. Always try pairwise GCD across multiple public keys.

-

## DSA Key Recovery via MD5 Collision on k-Generation

**Pattern:** When DSA nonce `k` is derived from `MD5(prefix + counter)`, generate MD5 prefix collisions to force two different counter values to produce the same `k`, enabling the standard nonce-reuse private key recovery.

```python
# k = int(MD5("K = {n: " + str(counter) +...))
# Use fastcoll to find MD5 collision on prefix "K = {n: "
# Two different counter values -> same MD5 -> same k -> nonce reuse

import subprocess
# Generate collision pair
subprocess.run(["fastcoll", "-p", prefix_file, "-o", "col1", "col2"])

# Get two signatures with same k (same r value)
sig1 = sign(msg1, counter1)  # uses MD5(prefix + counter1)
sig2 = sign(msg2, counter2)  # uses MD5(prefix + counter2) = same hash!

# Standard DSA nonce reuse recovery
k = (hash1 - hash2) * modinv(sig1.s - sig2.s, q) % q
private_key = (sig1.s * k - hash1) * modinv(sig1.r, q) % q
```

**Key insight:** MD5 collision generators like `fastcoll` produce pairs of inputs with identical hashes from a chosen prefix. When a signature scheme derives its nonce from an MD5 hash of controllable data, manufacturing a collision produces nonce reuse, enabling standard private key recovery.

-

## Ed25519 Same-Nonce Key Recovery

**Pattern:** An Ed25519 signer reuses the same private-key scalar with deterministic nonce derivation, but the public key changes between signatures (fault injection or swapped key material). Two signatures `(R1, S1, h1)` and `(R2, S2, h2)` share `a`, so `a = (S1 - S2) * inverse(h1 - h2) mod L`.

```python
L = 2**252 + 27742317777372353535851937790883648493
a = (S1 - S2) * pow(h1 - h2, -1, L) % L   # recovered scalar
```

**Key insight:** Ed25519 is deterministic, but any implementation bug that desyncs `(r, k)` from `(H(privkey, msg))` produces classical nonce-reuse. Check implementations that sign across key rotations — the scalar often survives rekey.

-

## Singular Curve ECDLP to Additive/Multiplicative Group

**Pattern:** Challenge publishes an "elliptic curve" that is actually singular — its discriminant is zero. Compute the singularity by finding the double root of `f(x) = x^3 + ax + b`. Map the curve to either the additive group `(GF(p), +)` (cusp) or the multiplicative group `GF(p)^*` (node) where DLP is easy.

```python
# Find singular point r
P.<x> = PolynomialRing(GF(p))
f = x^3 + a*x + b
r = (f.derivative()).roots()[0][0]
# Shift curve so singularity is at origin
# Then map (x, y) -> (x - r) / y  for nodal singularity
```

**Key insight:** Discriminant `-16(4a^3 + 27b^2)` zero means singular. Singular curves are either cusps (map to `(GF(p), +)`) or nodes (map to `GF(p)^*`) — both with polynomial-time DLP.

---

## BLS Aggregate Signature Rogue-Key Attack

**Pattern:** A service accepts BLS12-381 public-key registrations, aggregates all member keys, then verifies one aggregate signature. If proof-of-possession (PoP) is missing, optional, or separated from aggregate verification, register a crafted rogue key so the aggregate collapses to a key the attacker controls.

### Primitives

- Minimal-pubkey-size BLS12-381: pubkeys ∈ G1 (48-byte compressed), signatures ∈ G2 (96-byte compressed).
- `FastAggregateVerify(pks, msg, agg_sig)` checks `e(AggPk, H(msg)) == e(G1, agg_sig)` where `AggPk = Σ pk_i`.
- PoP: before joining an aggregate, each key owner proves knowledge of the secret key by signing `pk` itself.
- Without PoP, the rogue-key attack is trivial.

### Attack math

```
S   = Σ pk_i          # sum of existing legitimate public keys
T   = target point    # key the attacker can sign for (knows sk)
R   = T − S           # rogue key to register
```

After the service includes `R`, the aggregate becomes `S + R = T`. The attacker then signs the message with their secret key `sk` and the service accepts it as a valid aggregate signature.

### py_ecc implementation

```python
from py_ecc.bls import G2ProofOfPossession as bls
from py_ecc.bls.g2_primitives import pubkey_to_G1, G1_to_pubkey
from py_ecc.optimized_bls12_381 import add, neg

# 1. Enumerate keys included in aggregate verification
existing_pks_bytes = [pk1, pk2, pk3]          # raw 48-byte keys from service
existing_pts = [pubkey_to_G1(pk) for pk in existing_pks_bytes]

# 2. Choose a controlled key
sk = 42
pk_controlled = bls.SkToPk(sk)
target_pt = pubkey_to_G1(pk_controlled)

# 3. Compute S = sum of existing keys
S = existing_pts[0]
for p in existing_pts[1:]:
    S = add(S, p)

# 4. Compute rogue key R = target − S
rogue_pt = add(target_pt, neg(S))
rogue_pk = G1_to_pubkey(rogue_pt)        # register this with the service

# 5. After registration: aggregate = S + R = target_pt
#    Sign the message normally and submit
message = b"the message all members sign"
sig = bls.Sign(sk, message)
```

### Investigation checklist

1. Which keys does the service include in `FastAggregateVerify`? (all / only-verified / only-active / cached snapshot)
2. Is PoP required before joining the aggregate, optional, deferred to a separate endpoint, or interactive?
3. Does `join`/`register` accept a key with no PoP?
4. Are duplicate public keys allowed? (multiplicity shifts aggregate by a known amount)
5. Is there a `list` vs `unveil`/`verify` asymmetry — unverified members appear in the roster but are excluded from the aggregate?
6. Does the service use a fixed target message or one derived from state the attacker can observe?

### Triage pivots

- **Rogue key accepted, service still rejects:** wrong key-set in the aggregate — compare your local `FastAggregateVerify` call with the exact set and message bytes the server uses.
- **PoP blocks registration:** check if PoP verification happens before or after the key is stored; a race or optional path may skip it.
- **Duplicate keys accepted:** add `k` copies of a key you control to shift the aggregate by `k * pk`; combine with rogue math.
- **Separate `list` and `aggregate` trust domains:** treat only the set actually passed to `FastAggregateVerify` as the target sum.

**Key insight:** BLS aggregate security relies entirely on proof-of-possession. Any protocol that separates key registration from PoP, makes PoP optional, or caches a stale member set is vulnerable to rogue-key manipulation. The attack requires only one point subtraction — no DL computation.
