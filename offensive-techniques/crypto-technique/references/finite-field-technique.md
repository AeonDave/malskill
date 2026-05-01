# Finite Field Technique Reference

Operations over finite fields `GF(p)` and extension fields `GF(p^k)` arise frequently when
analyzing custom cryptographic constructions — especially secret sharing schemes, polynomial
commitments, and problems that present multiple field evaluations as output.

---

## Category 1: Shamir Secret Sharing Recovery

Shamir's scheme represents a secret as the constant term of a random polynomial of degree `k-1`
over `GF(p)`. Any `k` distinct evaluations allow exact reconstruction via Lagrange interpolation.

### 1.1 Recognizing Shamir-Style Problems

**Symptoms:**
- Problem provides `n` tuples `(x_i, y_i)` where `x_i` are small integers and `y_i` are large field elements.
- Description mentions "shares", "threshold", or "secret splitting".
- The prime modulus `p` is provided or easily inferred from share magnitudes.
- Polynomial degree is stated (e.g., "any 3 shares reconstruct the secret") → degree = threshold - 1.

**Disambiguation:**
- If `x_i` are the indices 1, 2, ..., n with `y_i` as evaluations: direct Shamir.
- If `y_i = f(x_i)` where `f` is defined over `GF(p)` (not ZZ): use `GF(p)` field arithmetic.
- If `x_i` are elements of `GF(p^k)`: the polynomial is over the extension field.

---

### 1.2 Sage Lagrange Interpolation

Sage provides `lagrange_polynomial()` to directly recover the polynomial from shares.

```python
from sage.all import *

# Known parameters
p = <prime_modulus>  # GF(p) field prime
threshold = <k>      # Minimum shares needed (polynomial degree = k-1)

# Shares: list of (x_i, y_i) pairs, x_i are field indices, y_i are evaluations
raw_shares = [
    (1, <y_1>),
    (2, <y_2>),
    (3, <y_3>),
    # ... at least threshold shares
]

# Construct the field
F = GF(p)

# Convert shares to field elements
shares = [(F(x), F(y)) for x, y in raw_shares[:threshold]]

# Recover the polynomial via Lagrange interpolation
R = PolynomialRing(F, 'x')
poly = R.lagrange_polynomial(shares)

# The secret is the constant term (coefficient of x^0)
secret = int(poly[0])
print(f"Recovered secret: {secret}")
print(f"As hex: {hex(secret)}")
```

**Validate reconstruction:**
```python
# Re-evaluate polynomial at all share x-values to confirm correctness
all_valid = True
for x_raw, y_raw in raw_shares:
    x_f, y_f = F(x_raw), F(y_raw)
    if poly(x_f) != y_f:
        print(f"MISMATCH at x={x_raw}: expected {y_raw}, got {int(poly(x_f))}")
        all_valid = False

if all_valid:
    print("All shares validate correctly.")
```

---

### 1.3 Manual Lagrange Interpolation

When Sage is not available or you need to implement the logic explicitly:

```python
def lagrange_reconstruct(shares, p):
    """Reconstruct secret from k shares over GF(p)."""
    # shares: list of (x_i, y_i) as integers
    secret = 0
    k = len(shares)

    for i, (x_i, y_i) in enumerate(shares):
        # Compute Lagrange basis polynomial l_i(0)
        num = 1
        den = 1
        for j, (x_j, _) in enumerate(shares):
            if i != j:
                num = (num * (-x_j)) % p
                den = (den * (x_i - x_j)) % p

        # l_i(0) = num * den^{-1} mod p
        li_at_0 = (num * pow(den, -1, p)) % p
        secret = (secret + y_i * li_at_0) % p

    return secret


# Usage
shares = [(1, <y1>), (2, <y2>), (3, <y3>)]
p = <prime>
secret = lagrange_reconstruct(shares, p)
print(f"Secret: {secret} = {hex(secret)}")
```

---

## Category 2: Field Extension Operations

### 2.1 GF(p^k) Arithmetic

When the polynomial is defined over a field extension rather than a prime field:

```python
from sage.all import *

p = <prime>
k = <extension_degree>  # e.g., 2, 3
F = GF(p**k)

# Elements are represented as polynomials modulo an irreducible polynomial
# GF(p^k) = GF(p)[x] / P(x) where P(x) is irreducible of degree k

# Construct an element
gen = F.gen()                          # generator 'a' of the extension
elem = F([1, 2, 0])                    # represents 1 + 2*a + 0*a^2 in GF(p^3)

# Arithmetic
a = F(<some_value>)
b = F(<other_value>)
print(f"a + b = {a + b}")              # Addition (= XOR for GF(2^k))
print(f"a * b = {a * b}")              # Multiplication in the field
print(f"a^{-1} = {a^(-1)}")           # Multiplicative inverse
print(f"a^p = {a^p}")                  # Frobenius automorphism

# Convert to integer representation
print(f"Integer form: {int(a)}")
```

**Shares over GF(p^k):**
```python
from sage.all import *

p = <prime>
k = <ext_degree>
F = GF(p**k)

# Shares as extension field elements
shares = [
    (F(<x1>), F(<y1>)),
    (F(<x2>), F(<y2>)),
    (F(<x3>), F(<y3>)),
]

R = PolynomialRing(F, 'x')
poly = R.lagrange_polynomial(shares)

# Secret is constant term (field element over GF(p^k))
secret_elem = poly[0]
print(f"Secret element: {secret_elem}")
print(f"Integer form: {int(secret_elem)}")
```

---

### 2.2 Extracting Key Bytes from Field Element

```python
# Convert recovered field element (integer) to bytes for use as key
secret_int = int(poly[0])
secret_bytes = secret_int.to_bytes((secret_int.bit_length() + 7) // 8, 'big')
print(f"Key bytes: {secret_bytes.hex()}")

# Alternatively, if the key is expected to be exactly N bytes:
from Crypto.Util.number import long_to_bytes
key = long_to_bytes(secret_int)
print(f"Key: {key.hex()}")
```

---

## Category 3: Polynomial Commitment and Evaluation Problems

### 3.1 Recovering a Polynomial from Evaluations

When a problem provides evaluations of a secret polynomial at known points (not necessarily a secret sharing scheme), the same interpolation technique applies.

```python
from sage.all import *

p = <prime>
F = GF(p)
degree = <known_or_inferred_degree>

# Points (x_i, f(x_i)) where f is the secret polynomial of given degree
eval_points = [
    (F(0), F(<f_at_0>)),
    (F(1), F(<f_at_1>)),
    (F(2), F(<f_at_2>)),
    # degree+1 points needed
]

R = PolynomialRing(F, 'x')
poly = R.lagrange_polynomial(eval_points)

print(f"Recovered polynomial: {poly}")
print(f"Coefficients: {poly.list()}")

# Extract specific coefficients
# poly.list() = [a_0, a_1, ..., a_n] (constant term first)
a0 = poly[0]   # Constant (often the secret)
a1 = poly[1]   # Linear coefficient
```

---

## Common Pitfalls

1. **Wrong field**: If shares are computed over `GF(p)` but you use `ZZ`, interpolation will produce wrong results. Always construct `GF(p)` first.

2. **Off-by-one in share indices**: Shamir often uses `x = 1, 2, ..., n` (not `0, 1, ..., n-1`). Using index 0 as a share makes `f(0)` trivially the secret — check whether the problem uses 0-indexed or 1-indexed shares.

3. **Insufficient shares**: Lagrange interpolation over a degree-`k` polynomial requires exactly `k+1` points. Using fewer gives wrong results with no error.

4. **Extension field generator mismatch**: If the problem uses a specific irreducible polynomial, specify it in Sage via `GF(p^k, modulus=<poly>)`. Using a different irreducible gives a different field isomorphism.

5. **Integer conversion order**: When converting field elements to bytes, confirm big-endian vs. little-endian. Use `long_to_bytes` for consistency.

---

## Decision Tree

```
START: Problem provides multiple tuples (x_i, y_i) and a prime p.

Q1: Are all x_i small consecutive integers (1, 2, 3, ...)?
  YES → Likely Shamir shares → Lagrange interpolation over GF(p) (§1.2)
  NO → Continue

Q2: Is there a stated threshold or polynomial degree?
  YES → Collect that many shares; interpolate
  NO → Try interpolating with progressively more shares until constant term stabilizes

Q3: Are x_i or y_i elements of GF(p^k) (i.e., very large or presented as polynomials)?
  YES → Use GF(p^k) arithmetic (§2.1–2.2)
  NO → GF(p) is sufficient

Q4: Is the secret the constant term of the recovered polynomial?
  USUALLY YES → poly[0] is the secret
  UNSURE → Check problem description; may need a specific evaluation point instead

Q5: Interpolation seems correct but decryption fails
  → Verify share correctness by re-evaluating poly at given x_i
  → Check field prime matches the one used to generate shares
```

---

## References and Tools

- **Sage**: `GF(p)`, `GF(p^k)`, `PolynomialRing(F, 'x').lagrange_polynomial(shares)`.
- **pycryptodome**: `Crypto.Util.number.long_to_bytes` for key conversion.

Load `offensive-tools/cryptography/sagemath/` for Sage execution environment.
