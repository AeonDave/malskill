# Lattice and LWE Technique Reference

Methodology for lattice-based attacks, LLL reduction, Coppersmith's method, and LWE embedding.

---

## Overview: When Lattice Attacks Apply

**First question to ask: what is supposed to be small?**
- The secret itself (LWE, NTRU)
- The error vector (LWE)
- The nonce difference (ECDSA HNP)
- A subset indicator vector in {0,1}^n (subset-sum / knapsack)
- A correction term caused by modular wraparound (truncated LCG)

**SVP vs CVP — the key decision:**
- **SVP** (Shortest Vector Problem): "find an unusually short non-zero lattice vector." Use LLL/BKZ with an embedding matrix. Choose when you only know a relation must be short.
- **CVP** (Closest Vector Problem): "find the lattice vector closest to a known target." Use Babai nearest-plane after LLL/BKZ reduction. Choose when you already have a target vector and want the nearest valid lattice point.

Use lattices when:
1. You have partial information (high/low bits known) about a secret.
2. Problem reduces to solving a system of linear equations modulo a number.
3. PRNG state is biased or truncated.
4. Modulus construction has mathematical shortcuts.

Common cryptographic problems that map to lattices:
- RSA with known/biased bits of `d` (Wiener, Boneh-Durfee).
- PRNG state recovery from biased output.
- LWE (Learning With Errors) problem.
- Subset sum and knapsack problems.
- ECDSA/DSA with biased or partial nonce leakage (HNP).

---

## Category 1: LLL Lattice Reduction

### 1.1 Basics: Building and Reducing a Lattice

**What is a lattice?**
A lattice is a set of integer linear combinations of basis vectors. In cryptanalysis, we construct a lattice such that the "short vector" in the reduced basis reveals the secret.

**LLL Algorithm:**
LLL (Lenstra-Lenstra-Lovász) reduces a lattice basis to find short vectors efficiently. The algorithm is polynomial-time but practical.

**Operational (Sage):**

```python
from sage.all import *

# Example: Wiener's attack or similar
# We want to find a short vector in a lattice

# Step 1: Construct basis matrix B
# Each row is a basis vector
B = matrix(ZZ, [
    [1, e, 0, 0],
    [0, n, 0, 0],
    [0, 0, e, 0],
    [0, 0, 0, n],
])

# Step 2: LLL reduce
B_reduced = B.LLL()

# Step 3: Extract short vectors (first few rows)
# Short vectors may contain the secret

# Example: if secret is a solution to ax + by = c mod n
# A short vector [a, b, c] may appear in reduced basis
```

**Sage's LLL Interface:**
```python
# Simplest usage
B = matrix(ZZ, [...])
B_reduced = B.LLL()

# More control
B_reduced = B.LLL(delta=0.99, eta=0.501)
# delta: smaller = more reduction (slower)
# eta: parameter for Gram-Schmidt

# For very large lattices, use fplll (external tool)
# B_reduced = matrix(ZZ, fplll(B))
```

---

### 1.2 Coppersmith's Method

**Preconditions:**
- You have a polynomial `f(x) ≡ 0 (mod N)` with small unknown `x`.
- Example: recover unknown bits of RSA private key `d`.

**Why it works:**
Construct a lattice of polynomials that all vanish at the secret root. Reduce lattice to find the root via LLL.

**Operational (Sage's `small_roots()`):**

```python
from sage.all import *

# Polynomial with unknown small root
# Example: f(x) = 2*x + a ≡ 0 (mod N)
# Find x < N^(1/2)

R.<x> = PolynomialRing(ZZ)
f = 2*x + a  # a is known, x is unknown small root

# Sage's small_roots computes this automatically
roots = f.small_roots(X=N^(1/2), beta=0.4)
# X: upper bound on |root|
# beta: parameterizes which moduli to use (0.4 is typical)

if roots:
    x_recovered = roots[0]
    print(f"Found root: {x_recovered}")
else:
    print("No small root found")
```

**Example: RSA Boneh-Durfee (partial `d` recovery):**

```python
# Given: n, e, and high bits of d
# Recover: full d

d_high = <known_high_bits>  # e.g., top 100 bits of d
# Unknown: low bits (x)

# Construct polynomial: e*x ≡ 1 + k*φ(n) (mod n)
# Rearrange: e*x - 1 ≡ k*φ(n) (mod n)
# φ(n) ≈ n - (p+q)

# Use Coppersmith to find k and low bits of d

R.<x, y> = PolynomialRing(ZZ)
f = e*x - 1 - y*(n - 1)  # y ≈ (p+q)/2, x ≈ low bits of d

# This is multivariate; Sage may not solve directly
# Instead, construct 1D polynomial and use univariate small_roots
```

---

### 1.3 Multivariate Coppersmith via Sylvester Determinant

**Preconditions:**
- You have two polynomials `f(x, y)` and `g(x, y)` that share a common root.
- Example: two related RSA error terms `(e1, e2)` satisfy `f(e1, e2) ≡ 0 (mod N)`.
- Unknowns are small relative to modulus.

**Why it works:**
Eliminate one variable by computing the **resultant** of the two polynomials (Sylvester matrix determinant). Reduces to a univariate polynomial, then apply `small_roots()`.

**Operational:**

```python
from sage.all import *

# Two polynomials in variables x, y sharing a common root (e1, e2)
# Example from error-term recovery:
# f(x, y) = (a - x)^e mod n  — polynomial relating e1 to public value
# g(x, y) = (b - y)^e mod n  — polynomial relating e2 to public value

P.<x, y> = PolynomialRing(ZZ)

# Define the two polynomials
f = <polynomial_in_x_and_y>
g = <polynomial_in_x_and_y>

# Eliminate y by computing resultant w.r.t. y
# res = resultant(f, g) — polynomial in x only
res = f.resultant(g, y)

# res is now univariate in x; find its small root
Rx.<t> = PolynomialRing(ZZ)
res_uni = Rx(res.univariate_polynomial())

roots = res_uni.small_roots(X=error_bound, beta=0.4)

if roots:
    e1 = int(roots[0])
    print(f"Recovered e1: {e1}")
    # Substitute back to recover e2
    # f(e1, y) = 0 → solve for y
    fy = P(f).subs(x=e1)
    roots_e2 = Rx(fy.univariate_polynomial()).roots()
    if roots_e2:
        e2 = int(roots_e2[0][0])
        print(f"Recovered e2: {e2}")
else:
    print("No root found; adjust X bound or beta")
```

**Sylvester Matrix:**
```python
# For explicit control over resultant construction
from sage.all import *

P.<x, y> = PolynomialRing(ZZ)
f = <poly_f>
g = <poly_g>

# sylvester_matrix builds the matrix whose determinant is the resultant
# This is equivalent to f.resultant(g, y) but lets you inspect the matrix
S = f.sylvester_matrix(g, y)
print(f"Sylvester matrix size: {S.dimensions()}")
res = S.det()
print(f"Resultant polynomial: {res}")
```

**When to suspect:**
- You have two separate equations relating truncated or erroneous values.
- You know bounds on errors/unknowns but they are too large for univariate Coppersmith alone.
- Problem structure produces two polynomials with shared variable.

---

## Category 2: Learning With Errors (LWE)

### 2.1 LWE Problem and Recognition

**What is LWE?**
Given samples `(a_i, b_i)` where `b_i ≈ <a_i, s> (mod q)` with small error, recover secret `s`.

**Recognizing LWE in cryptography:**
- Ring-LWE: used in lattice-based encryption (Kyber, NewHope).
- Module-LWE: generalization.
- NTRU: similar structure.
- Biased PRNG output: can be modeled as LWE.

**Operational:**

```python
# Given: samples (a_i, b_i) where a_i is random, b_i = <a_i, s> + noise
# Recover: s

# Embed LWE into lattice problem
# Construct lattice basis from sample matrix

# For small number of samples and moderate noise:
# Use BKZ or specialized LWE solvers

# Sage + BKZ (requires fplll)
# A = matrix(ZZ, [[a_1, 1, 0, ...], [a_2, 0, 1, ...], ...])
# A_reduced = A.BKZ()
# Extract s from reduced basis structure
```

---

### 2.2 Babai Nearest Plane (CVP via fpylll)

**When to use:**
You have a target vector `t` (from known partial observation) and need the nearest lattice point. Reduce the basis first with LLL/BKZ, then apply Babai.

```python
from sage.all import *
from fpylll import IntegerMatrix, CVP

# Build your lattice basis as a Sage matrix
B_sage = matrix(ZZ, [...])  # (n x n) basis

# Reduce
B_red = B_sage.LLL()  # or .BKZ(block_size=25)

# Convert to fpylll format
B_fplll = IntegerMatrix.from_matrix(B_red.change_ring(ZZ))

# Target vector (the observed/known value you want to approximate)
target = [...]  # list of integers, same length as basis rows

# Babai nearest plane
closest = CVP.babai(B_fplll, target)
print(f"Closest lattice vector: {list(closest)}")

# Extract the secret from the difference: target - closest
residual = [target[i] - closest[i] for i in range(len(target))]
print(f"Error/residual: {residual}")
```

**Rule of thumb:**
- After BKZ(block_size=25), Babai succeeds for LWE errors up to ~q/10.
- If Babai fails, increase BKZ block size (slow) or collect more samples.

---

### 2.3 Hidden Number Problem (HNP): Partial Nonce Leakage

**Pattern:** Signatures (ECDSA, DSA, Schnorr) or RNG equations leak a few bits of the hidden nonce `k`. HNP converts this into a lattice problem whose short vector encodes the private key and nonce corrections.

**Generic form:**

Each signature gives: `a_i * x + b_i ≡ e_i (mod q)` where `e_i` is small (the leaked correction).

**When to use:**
- ECDSA with leaked high/low bits of nonce `k_i`.
- Any signing scheme where each `k_i = known_i * 2^t + hidden_i` and `hidden_i` is small.
- LCG-like recurrences where partial state is observable.

**ECDSA partial-nonce lattice skeleton:**

```python
from sage.all import Matrix, ZZ

def build_ecdsa_hnp_lattice(q, rs, ss, hs, leaked, t):
    """
    Build HNP lattice for ECDSA with partially known nonces.

    q       : group order
    rs, ss  : signature components (lists)
    hs      : hashes of signed messages (as integers)
    leaked  : known high bits of each nonce (k_i >> t)
    t       : number of unknown low bits per nonce
    """
    n = len(rs)
    M = Matrix(ZZ, n + 2, n + 2)

    # q * I block (modular reduction rows)
    for i in range(n):
        M[i, i] = q

    # Coefficients row: s_i contributions
    for i in range(n):
        M[n, i] = ss[i]

    # Constant row: adjusted hash contributions
    for i in range(n):
        M[n + 1, i] = (hs[i] - ss[i] * leaked[i] * (1 << t)) % q

    # Scaling entries for private key and bound
    M[n, n] = 1
    M[n + 1, n + 1] = q // (1 << t)

    return M

# Usage:
M = build_ecdsa_hnp_lattice(q, rs, ss, hs, leaked, t)
R = M.LLL()

# Inspect short rows for plausible private key d
for row in R[:5]:
    candidate_d = int(row[n]) % q
    # Verify: check that d * G == public_key
    if verify_key(candidate_d, public_key, signatures):
        print(f"Private key: {candidate_d}")
        break
```

**What to do next:**
1. Collect ≥8 signatures with partial nonce leakage.
2. Build the lattice.
3. Run LLL.
4. Inspect short rows for a plausible `d`.
5. Verify `d` against all signatures.
6. If one or two bits are off, brute-force the remaining uncertainty.

---

### 2.4 LWE via Embedding and CVP

**Pattern:** Given `A`, `b`, modulus `q` where `b = A*s + e (mod q)` with small error vector `e`.

**Embedding lattice construction:**

```python
from sage.all import *

# LWE parameters
n = <secret_dimension>
m = <number_of_samples>
q = <modulus>

A = matrix(ZZ, m, n, ...)  # m x n public matrix
b = vector(ZZ, ...)         # m-dimensional observation

# Embedding trick: add one extra coordinate for error scaling
# Build lattice [q*I_m | 0; A^T | I_n; b | 0...1]
# The short vector encodes (e || s || -1) after LLL

# Simple embedding lattice:
lattice_rows = []

# q*I_m block
for i in range(m):
    row = [0]*m + [0]*n
    row[i] = q
    lattice_rows.append(row)

# [A^T | I_n] block
for j in range(n):
    row = [int(A[i][j]) for i in range(m)] + [0]*n
    row[m + j] = 1
    lattice_rows.append(row)

B = matrix(ZZ, lattice_rows)
B_red = B.LLL()

# The first short row should encode the error e in the first m coordinates
for row in B_red[:5]:
    e_candidate = row[:m]
    s_candidate = row[m:]
    if all(abs(x) <= error_bound for x in e_candidate):
        print(f"Secret s: {s_candidate}")
        break
```

**For ternary or sparse secrets:**
```python
# Scale column for each secret coordinate by sigma (expected std dev)
# or use BKZ(block_size=30) instead of LLL for harder instances
B_red = B.BKZ(block_size=30)
```

**When to suspect:**
- Challenge description says "error is small", "noise-free" LWE, or gives a matrix + biased observations.
- Equation system mod `q` with small additive errors.

---

## Category 3: Biased PRNG State Recovery

### 3.1 Truncated LCG Recovery

**Preconditions:**
- LCG: `x_{i+1} = (a*x_i + c) mod m`.
- You see truncated outputs: only high bits of each state.
- Example: `rand()` in C returns top 16 bits of internal state.

**Why it works:**
Use lattice to model the unknowns (hidden bits) as variables. Reduce to find the state.

**Operational:**

```python
# LCG with outputs [y_1, y_2, y_3, ...] (truncated)
# y_i = truncate(x_i)
# x_{i+1} = (a*x_i + c) mod m

# Unknown: hidden bits of each x_i
# Model: y_i + h_i = x_i (where h_i is hidden)

# Lattice basis:
# Each row encodes: x_{i+1} = a*x_i + c (mod m)
# Augment with bounds on h_i

# Use LLL to find valid sequence of states

# Tool: custom Sage script or external LCG solver
```

---

## Category 4: Constraint Modeling

### 4.1 Building Custom Lattices

When the problem doesn't fit standard templates, manually construct the lattice.

**Steps:**
1. Identify unknowns (what you want to recover).
2. Identify equations (constraints from known data).
3. Augment with bounds (bit lengths, modular reductions).
4. Construct basis matrix.
5. Reduce with LLL.
6. Extract short vectors and solve.

**Example: Recover two unknowns `x` and `y` from:**
```
x + y ≡ a (mod N)
x * y ≡ b (mod N)
x, y < B
```

Construct lattice:
```python
# Let x, y be the unknowns
# Constraint 1: x + y - a ≡ 0 (mod N)
# Constraint 2: x*y - b ≡ 0 (mod N)

# Build polynomial f(x, y) from constraints
# Then use Sage to find small roots (multivariate case)

from sage.all import *
R.<x, y> = PolynomialRing(ZZ)
f = x + y - a  # Linear
g = x*y - b    # Nonlinear

# Compute Gröbner basis or use heuristic small_roots if available
```

---

### 4.2 Matrix Augmentation and Stacking Patterns

When modeling partial information from multiple independent equations, the lattice basis is constructed by stacking constraints into one matrix. This is the core pattern for recovering a message or secret from partial linear observations.

**Stacking constraint equations:**

Each observed linear relation over `Q` becomes one row. Unknowns become columns. The lattice basis encodes all relations simultaneously.

```python
from sage.all import *

# Scenario: you observe k values each equal to a linear combination of unknowns
# y_i = sum(a_ij * x_j) + noise_i,  for i = 0..k-1
# You want to recover (x_0, x_1, ..., x_n) as a short vector.

# Build basis matrix:
# - First block: identity matrix scaled by modulus M (for unknown x_j)
# - Second block: observed coefficients a_ij
# - Third block: identity scaled by 1 (for auxiliary variables)

n_unknowns = 4
k_observations = 4
M = 2**128  # Modulus bounding residues

B = identity_matrix(QQ, n_unknowns) * M

# Stack observation rows
obs_matrix = matrix(QQ, [[a[i][j] for j in range(n_unknowns)] for i in range(k_observations)])
B = B.stack(obs_matrix)

# Augment with scale column for objective alignment
scale_col = vector(QQ, [0]*n_unknowns + [1]*k_observations)
B = B.augment(scale_col)

# LLL reduce
B_reduced = B.LLL()

# Inspect first rows for short vectors
for row in B_reduced[:5]:
    print(row)
```

**Identity + augment pattern (Verilicious-style partial key recovery):**
```python
from sage.all import *

# Given: partial key observations encoded as linear constraints over QQ
# Each constraint: known_coeff * secret + known_term ≡ 0 (mod N)

observations = [...]  # list of (coeff, term) pairs

# Build constraint matrix
n = len(observations)
rows = []
for coeff, term in observations:
    row = [0] * (n + 1)
    row[0] = N          # modular reduction column
    row[1] = coeff      # coefficient for secret
    # extend as needed
    rows.append(row)

B = matrix(ZZ, rows)
B = identity_matrix(ZZ, n).augment(B)  # Augment identity for slack variables

B_reduced = B.LLL()

# The short vector in the first row of B_reduced encodes the secret
candidate = B_reduced[0]
secret = int(candidate[0])  # Extract from first component (by construction)
print(f"Candidate secret: {secret}")
```

**When to suspect:**
- You have multiple independent linear observations about a single secret.
- Direct linear algebra (mod N) does not uniquely solve (too many unknowns).
- Secret is bounded: `|secret| < 2^k` for known `k`.

---

## Category 5: GF(2^N) Polynomial Constraint Solving

This category covers problems where the state space is a finite extension field of characteristic 2, not the integers. Bitwise operations (XOR, rotation) map directly to polynomial arithmetic in `GF(2)[x]`.

### 5.1 Modeling Bitwise Operations as GF(2^N) Polynomials

**When this applies:**
- Custom cipher with XOR, bit-rotation, or shift.
- State update is a sequence of XOR/rotation steps.
- You need to algebraically invert the state update to recover the key or initial state from observed output.

**Why it works:**
In `GF(2^N)`, every element is a polynomial with binary coefficients. XOR is polynomial addition. Bit rotation is polynomial multiplication by `x^k mod P(x)` where `P(x)` is the field's reducing polynomial.

```python
from sage.all import *

N = 128
# Construct the finite field GF(2^128)
# Using a known reducing polynomial, or let Sage choose:
F = GF(2**N, name='a')
a = F.gen()

# Represent a 128-bit state as a field element
state_int = 0xDEADBEEF_DEADBEEF_DEADBEEF_DEADBEEF  # example
state_bits = [(state_int >> i) & 1 for i in range(N)]
state_elem = sum(b * a^i for i, b in enumerate(state_bits))

# XOR corresponds to field addition
state2 = state_elem + other_state_elem  # XOR = +

# Bit rotation by r positions = multiplication by a^r mod P
def rotate_left(elem, r, field):
    a = field.gen()
    return elem * a^r  # Rotation is polynomial multiply by x^r in GF(2^N)

# Rotation-based cipher example: output = rotate(state, r) XOR key
# Given: output, r → recover key
# key = output XOR rotate(state, r) = output + rotate(state, r)  in GF
# key = output + state * a^r
```

### 5.2 Factoring Polynomials in GF(2)[x]

```python
from sage.all import *

R = PolynomialRing(GF(2), 'x')
x = R.gen()

# Define a polynomial over GF(2)
p = x^7 + x^6 + x^5 + x^4 + x^3 + x^2 + x + 1  # example

# Factor it
factors = p.factor()
print(f"Factors: {factors}")
# Returns list of (irreducible_poly, multiplicity)

# Check irreducibility
for f, m in factors:
    print(f"Factor: {f}, degree: {f.degree()}, irreducible: {f.is_irreducible()}")
```

### 5.3 Inverting a Round Function to Recover State

When a cipher applies a sequence of invertible operations (XOR, rotation, polynomial multiply), model it as a single polynomial equation and solve.

```python
from sage.all import *

N = 128
F = GF(2**N, name='a')
a = F.gen()

# Known: final output element O, known operations applied
# Operation sequence: O = R(key) * S(state) + T(nonce)
# Where R, S, T are known linear maps over GF(2^N)

# Recover: state
# state = S_inv * (O + T(nonce)) / R(key)  (all operations in F)

O = F(<output_bits_as_element>)
T_nonce = F(<nonce_as_element>)
R_key = F(<key_as_element>)

# In GF(2^N), division is multiplication by inverse
state = (O + T_nonce) / R_key  # '+' is XOR, '/' is field divide

print(f"Recovered state: {int(state):#x}")
```

**When to suspect:**
- Cipher source code shows XOR and rotation as primary operations.
- State is represented as a fixed-width integer (128-bit, 64-bit, etc.).
- Protocol runs multiple rounds; each round's output is observable or known.

**When not to use:**
- Operations involve multiplication by secret-dependent values over integers → not linear over GF(2).
- Cipher is AES or another S-box-based cipher → GF field model does not simplify S-boxes.

---

## Category 6: Subset Sum and Knapsack via Lattice Reduction

### 6.1 Merkle-Hellman Knapsack / Subset Sum

**Pattern:** Given a public key vector `W = [w_0, ..., w_{n-1}]` and a ciphertext `C = sum(w_i * b_i)` for unknown binary `b_i`, recover the bit vector `b`.

**Why LLL works:**
Reformulate as SVP: build a matrix whose short vector encodes the solution `b_i ∈ {0,1}`.

**Operational (Sage):**

```python
from sage.all import *

def knapsack_lll(pubkey, ciphertext):
    """
    Recover binary plaintext from a knapsack ciphertext using LLL.

    pubkey     : list of public key values [w_0, ..., w_{n-1}]
    ciphertext : target sum C = sum(w_i * b_i)
    """
    n = len(pubkey)
    # Build (n+1) x (n+1) matrix:
    # - Upper-left: n x n identity (tracks which elements are selected)
    # - Rightmost column: public key values, last row: -ciphertext
    A = Matrix(ZZ, n + 1, n + 1)

    for i in range(n):
        A[i, i] = 1            # identity rows
        A[i, n] = pubkey[i]    # public key values

    A[n, n] = -int(ciphertext)  # target sum row

    # LLL reduce
    R = A.LLL()

    # Search for a row where last element is 0 and all others are in {0, 1}
    for row in R:
        if row[-1] == 0 and all(b in (0, 1) for b in row[:-1]):
            return list(row[:-1])  # This is the binary plaintext

    # Alternatively, check for rows with last element 0 and values in {-1, 0, 1}
    # (LLL might negate the solution)
    for row in R:
        if row[-1] == 0 and all(b in (-1, 0, 1) for b in row[:-1]):
            bits = [(1 if b == -1 else b) for b in row[:-1]]
            if sum(pubkey[i] * bits[i] for i in range(n)) == ciphertext:
                return bits
    return None

# Example usage
pubkey = [<w0>, <w1>, ...]
ciphertext = <C>
plaintext_bits = knapsack_lll(pubkey, ciphertext)
if plaintext_bits:
    # Convert bits to bytes
    m = int(''.join(str(b) for b in plaintext_bits), 2)
    print(bytes.fromhex(hex(m)[2:]))
```

**When to suspect:**
- Challenge presents a "knapsack" or "subset sum" structure.
- Public key is a list of integers and ciphertext is their linear combination over {0,1}.
- Merkle-Hellman or related broken knapsack scheme.

**Key insight:** LLL finds the binary vector because it is much shorter than any random lattice vector. The last column being zero identifies the row encoding the solution.

---

1. **Choosing wrong bound `X`**: If `X` is too large, LLL won't find the root. If too small, root is outside the search space. Start with `X = 2^(bits_of_secret)`.

2. **Beta parameter in Coppersmith**: Determines moduli used. For `f(x) ≡ 0 (mod N)`, use `beta = 0.4` or `0.5`. For higher moduli, increase beta.

3. **Multivariate vs. univariate**: LLL works best on univariate polynomials. For multivariate, reduce to univariate via resultant (§1.3) if possible.

4. **Lattice dimension**: Larger lattices are harder to reduce. Aim for dimension < 100 for practical speed.

5. **GF(2^N) field generator mismatch**: If a cipher uses a specific reducing polynomial, ensure Sage's field uses the same one. Use `GF(2^N, modulus=<poly>)` to specify explicitly.

---

## References and Tools

- **Sage**: `LLL()`, `small_roots()`, `BKZ()`, `resultant()`, `GF(2^N)`, `PolynomialRing(GF(2))`.
- **fplll**: https://github.com/fplll/fplll — external lattice reduction library.
- **Coppersmith implementations**: Various papers and GitHub repos with ready-to-use implementations.

Load `offensive-tools/cryptography/sagemath/` for operational scripts and pattern reference.

