# Problem Diagnosis — Crypto Technique Reference

Before attempting any attack, extract and understand the cryptographic artifacts. This reference guides you through reading problems, dumping parameters, and identifying weakness signals.

## Section 1: Source Code Review Checklist

If you have access to the implementation (Python, C, Go, Java), systematically check:

### A) Key Generation

- **Entry point**: look for functions like `generate_key()`, `keygen()`, or initialization code.
- **Random source**: is it `random` (weak), `secrets` (OK), or `os.urandom()` (good)?
- **Seed**: if seeded, is the seed predictable (timestamp, PID, known constant)?
- **Prime generation**: are the primes distinct? Are they checked to be prime (Miller-Rabin)?
- **Key reuse**: are keys generated once and reused across multiple ciphertexts/signatures?

**Red flags:**
- `random.seed(int(time.time()))` — predictable seed.
- `random.randint()` for cryptographic operations — use `secrets.randbelow()`.
- Hardcoded primes or keys in code.
- No prime validation or validation with insufficient rounds.

### B) Modulus and Exponent Properties

**RSA:**
- Are `p` and `q` distinct primes? Check: `gcd(p, q) == 1`.
- Is `e` small (3, 5, 17, 65537)? → Potential cube/fifth-root attacks.
- Is `d` abnormally small? → Wiener's attack territory (d < n^0.25).
- Do `p-1` or `q-1` have small factors? → Pollard p-1 or ECM.

**ECC:**
- What curve? Secp256k1, P-256, Curve25519, or custom?
- Custom curves: are `a`, `b`, `p` params defined inline? → High risk of singular or weak curves.
- What is the order of the base point? Is it prime? Smooth?
- Is there a cofactor? If > 1, small-subgroup attack possible.

### C) Cipher Mode and Key Derivation

- **Mode**: ECB, CBC, CTR, GCM, or custom?
- **ECB**: always vulnerable to pattern leakage.
- **CBC**: predictable or reused IV? → Bit-flipping attacks.
- **CTR/Stream**: is the nonce reused? → XOR keystream and recover plaintext.
- **Key derivation**: PBKDF2, scrypt, Argon2, or weak hash (MD5, SHA1 stretched)?
- **Salt**: is salt present and random? Or hardcoded?

**Red flags:**
- ECB mode with large plaintext blocks.
- IV derived from counter, PID, or timestamp.
- Key stretching with SHA1 or MD5, insufficient rounds.
- No salt in KDF.

### D) Padding and Validation

- **RSA padding**: PKCS#1 v1.5, OAEP, or none?
- **AES padding**: PKCS#7 or custom?
- **Validation**: does the code check padding *before* decryption? → Padding oracle possible.
- **Signature verification**: does it validate length, zero bytes, or use constant-time comparison?

**Red flags:**
- Custom padding schemes.
- Returning error messages that distinguish "invalid padding" from "valid but garbled."
- Non-constant-time comparison (`==` in Python instead of `hmac.compare_digest()`).

### E) Randomness and Nonce

- **Nonce/IV generation**: is it random or deterministic?
- **Nonce reuse**: can the same nonce be used twice with different messages? → XOR-based attacks.
- **Counter mode**: is the counter initialized randomly or from 0? → Nonce collision risk.
- **DSA/ECDSA**: is `k` generated with good entropy? Is `k` reused across signatures?

**Red flags:**
- Nonce from `time.time()` or `random.getrandbits()`.
- Counter always starting from 0 or incrementing globally.
- No uniqueness check on nonce.

---

## Section 2: Parameter Extraction Workflow

Once you have the code or API access, dump all cryptographic parameters.

### RSA Parameter Extraction

```python
from Crypto.PublicKey import RSA
from Crypto.Util.number import long_to_bytes, bytes_to_long

# Load public key
pubkey = RSA.import_key(open('key.pem').read())
n = pubkey.n
e = pubkey.e

# Dump to file or terminal
print(f"n = {n}")
print(f"e = {e}")

# If ciphertext available:
c = bytes_to_long(open('ciphertext.bin', 'rb').read())
print(f"c = {c}")

# Check size and properties
print(f"n bit size: {n.bit_length()}")
print(f"e size: {e}")
print(f"Is e small? {e < 1000}")

# For factorization signal, check if p-1 or q-1 may be smooth
# (you won't know p, q until factored, but can hint from small factors of related numbers)
```

### ECC Parameter Extraction

```python
from sage.all import *

# If curve params given (e.g., Bitcoin's secp256k1)
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a = 0
b = 7
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Construct curve in Sage
E = EllipticCurve(GF(p), [a, b])

# Public key (point)
Q = E([Qx, Qy])

# Check curve properties
print(f"Curve order: {E.order()}")
print(f"Is order smooth? Check factor(E.order())")

# For custom curves, check singularity
try:
    E.j_invariant()
    print("Curve is non-singular")
except:
    print("Curve is SINGULAR — potential Smart's attack or additive reduction")
```

### DSA/ECDSA Signature Extraction

```python
# Collect multiple signatures
signatures = [
    (r1, s1, m1_hash),
    (r2, s2, m2_hash),
    # ... more signatures
]

# Check for nonce reuse: if k reused, then r values match
rs_values = [r for r, s, m_hash in signatures]
if len(rs_values) != len(set(rs_values)):
    print("Nonce reuse detected!")

# Check if k is small or biased (requires comparison to many signatures)
# Large variance in r? Small r values? Clustered r? → Weak PRNG
```

### PRNG and Random State Extraction

```python
# Collect output samples
outputs = [get_next_output() for _ in range(100)]

# Test for bias (chi-squared test, entropy calc)
import math
from collections import Counter
counts = Counter(outputs)
entropy = -sum((c/len(outputs)) * math.log2(c/len(outputs)) for c in counts.values())
print(f"Entropy per sample: {entropy} bits")
print(f"Expected for random N-bit: {N} bits")

# Test for pattern: plot outputs, check periodicity
# Test for autocorrelation: does output[i] correlate with output[i+k]?

# If state leaked or partially known:
# → Try recovery via LLL (see lattice-lwe-technique.md)
```

---

## Section 3: Weakness Signal Checklist

Once you've extracted parameters, look for these weakness patterns:

| Weakness | Indicator | Reference Section |
|----------|-----------|------------------|
| **Small RSA exponent** | e ∈ {3, 5, 17} and c < n | rsa-technique.md § 1 |
| **Wiener attack** | e ≈ n or d < n^0.25 (inferred) | rsa-technique.md § 2 |
| **Common modulus** | Same n, different e | rsa-technique.md § 3 |
| **Hastad broadcast** | Same message, different e and n | rsa-technique.md § 4 |
| **Pollard p-1** | p-1 has small factors | rsa-technique.md § 5 |
| **Fermat factorization** | p and q close (consecutive bits similar) | rsa-technique.md § 6 |
| **Padding oracle** | Service responds differently to invalid padding | prng-oracle-technique.md § 3 |
| **Timing oracle** | Response time varies with ciphertext | prng-oracle-technique.md § 4 |
| **DSA nonce reuse** | Multiple signatures with same r | ecc-technique.md § 2 |
| **ECDLP smooth order** | Curve order factors into small primes | ecc-technique.md § 1 |
| **Singular curve** | j-invariant undefined or curve is rational map | ecc-technique.md § 3 |
| **PRNG bias** | Output entropy < expected, clustering | prng-oracle-technique.md § 1 |
| **ECB mode** | Repeated blocks in ciphertext reveal pattern | symmetric-cipher-technique.md § 1 |
| **CBC nonce reuse** | Same IV used for different plaintexts | symmetric-cipher-technique.md § 2 |
| **Stream cipher reuse** | Same keystream applied to multiple messages | symmetric-cipher-technique.md § 3 |

---

## Section 4: Oracle Characterization

If you're attacking an oracle service (padding oracle, timing leak, signature verification error):

### Baseline Measurement

```python
import time

# Measure response time for N random inputs
times = []
for i in range(1000):
    input_data = os.urandom(128)
    t0 = time.perf_counter()
    result = service.query(input_data)
    t1 = time.perf_counter()
    times.append(t1 - t0)

# Characterize distribution
import statistics
print(f"Mean: {statistics.mean(times):.6f}s")
print(f"Stdev: {statistics.stdev(times):.6f}s")
print(f"Min: {min(times):.6f}s, Max: {max(times):.6f}s")
```

### Signal-to-Noise Ratio (SNR)

```python
# Measure times for two distinct oracle behaviors
times_true = [measure_time(valid_input) for _ in range(100)]
times_false = [measure_time(invalid_input) for _ in range(100)]

mean_true = statistics.mean(times_true)
mean_false = statistics.mean(times_false)
stdev_true = statistics.stdev(times_true)
stdev_false = statistics.stdev(times_false)

# SNR = |mean_true - mean_false| / sqrt(stdev_true^2 + stdev_false^2)
snr = abs(mean_true - mean_false) / math.sqrt(stdev_true**2 + stdev_false**2)
print(f"SNR: {snr}")

# SNR > 5 is good (attack feasible)
# SNR 1-5 is marginal (noisy, many retries needed)
# SNR < 1 is too noisy
```

### Oracle Error Classification

```python
# Test oracle responses to understand failure modes
test_cases = [
    ("valid_padding", valid_ciphertext),
    ("invalid_padding", invalid_ciphertext),
    ("truncated", ciphertext[:16]),
    ("all_zeros", b'\x00' * 128),
    ("all_ones", b'\xff' * 128),
]

for label, ct in test_cases:
    try:
        result = service.decrypt(ct)
        print(f"{label}: OK — {result[:16]}...")
    except Exception as e:
        print(f"{label}: ERROR — {type(e).__name__}: {str(e)[:50]}")
```

---

## Section 5: Parameter Validation Checklist

Before declaring a weakness, confirm:

1. **Key size matches claim**: 1024-bit RSA should have n ≈ 2^1024.
2. **Exponents in valid ranges**: 1 < e < φ(n) for RSA; 0 < d < φ(n).
3. **Curve parameters correct**: point multiplication works, order checks out.
4. **No off-by-one or encoding issues**: UTF-8 vs. ASCII, big/little endian, padding.
5. **Oracle is deterministic**: same input always produces same output (barring timeout/network jitter).

---

## Next Steps

Once you've diagnosed the weakness and extracted parameters:

1. Consult the **technique reference** for your category (RSA, ECC, PRNG, symmetric).
2. Confirm the attack **preconditions** are met.
3. Load the appropriate **tool skill** from `offensive-tools/cryptography/`.
4. **Execute the attack** and validate results.

