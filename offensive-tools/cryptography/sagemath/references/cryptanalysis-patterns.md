# SageMath Reference — Cryptanalysis Patterns

Grounded in observed public solver implementations that explicitly import or execute Sage constructs.

## 1) File-by-file Sage technique map

### A) `solver.sage` (ROT/XOR algebra over $GF(2^{128})$)

Core Sage usage:
- `F.<w> = GF(2**N)` with $N=128$
- `PR.<z> = PolynomialRing(GF(2))`
- conversion helpers between integers and bit-polynomials
- factorization of constructed polynomial expressions to recover rotation-index candidates

Technique:
- Model rotate/XOR equations as polynomial identities over characteristic-2 algebra.
- Split unknowns into structured terms and recover candidates by divisibility/factor checks.

Operational role:
- Sage does the symbolic/algebraic recovery.
- `pwntools` drives round-based network interaction and submits recovered state.

### B) `solver.py` (finite-field + EC parameter recovery workflow)

Core Sage usage:
- `GF(p)` for prime-field arithmetic
- `factor(...)` for structured factorization responses
- `EllipticCurve(GF(p), [a,b])` and `E.order()`
- extension field `GF(p**3, 'x')` and `Ep3.order()`
- `log(A, G)` for ECDLP recovery on lifted points

Technique:
- Mixed protocol solving: classical factorization + elliptic-curve order computations + discrete logarithm.

Operational role:
- Sage computes each math answer required by the service protocol.
- Script serializes answers into the exact expected textual format.

### C) `solver.py` (multivariate truncated-state recovery with Coppersmith)

Core Sage usage:
- polynomial symbols via `polygens(F, 'x, e1, e2')`
- construction of two polynomial constraints from truncated outputs
- Sylvester-matrix determinant as elimination surrogate to remove one variable
- external `small_roots(...)` (loaded Sage implementation) for bounded multivariate roots

Technique:
- Convert truncated-leak equations into a small-root problem.
- Eliminate one variable, then solve for bounded error terms $(e_1, e_2)$.

Operational role:
- Sage builds/eliminates polynomial systems and solves bounded roots.
- Final plaintext/root extraction is done from recovered symbolic roots.

### D) `solver.py` (LLL lattice for partial-information recovery)

Core Sage usage:
- `identity_matrix`, `zero_vector`, `vector(QQ, ...)`, `stack/augment`
- `next_prime(n)` as a scaling/embedding helper
- `M.LLL()` to find a short vector encoding the hidden value

Technique:
- Build a constrained lattice embedding for partially known value recovery.
- Use LLL short vectors to reconstruct candidate message integer.

Operational role:
- Sage handles lattice construction and reduction.
- Python post-processes candidates and validates decoded output pattern.

### E) `solver.py` (Shamir reconstruction over finite field)

Core Sage usage:
- `F = GF(p)`
- `PR = PolynomialRing(F, 'x')`
- `PR.lagrange_polynomial(shares)`

Technique:
- Reconstruct secret polynomial from shares using Lagrange interpolation.
- Extract constant term as the recovered secret/key material.

Operational role:
- Non-Sage code performs ciphertext parsing/decryption attempts.
- Sage executes the exact interpolation/recovery step.

### F) `solver.py` (EC-LCG state recovery + lattice linearization)

Core Sage usage:
- `EllipticCurve`, `GF`, `PolynomialRing`, `Sequence`
- multivariate polynomial equations encoding EC and transition constraints
- coefficient-monomial matrix extraction, ring lift to `ZZ`
- block lattice construction with `identity_matrix`, `zero_matrix`
- `LLL()` to recover hidden offset variables

Technique:
- Algebraic modeling of consecutive EC-derived outputs.
- Lattice-assisted recovery of hidden additive components/state.

Operational role:
- Sage recovers internal state candidate points.
- Remaining protocol/signature interaction is handled by Python libs and I/O code.

## 2) Common Sage design patterns extracted

1. **Field-first modeling**: choose `GF(p)` or `GF(2^N)` before writing equations.
2. **Symbolic equation building**: create polynomial unknowns early, delay numeric substitution.
3. **Elimination before brute-force**: reduce variable count via resultant/sylvester-style transformations.
4. **Lattice escalation**: if equations include bounded noise/truncation, translate to an LLL-friendly basis.
5. **Protocol split**: keep Sage-only math in compact blocks; isolate transport/serialization separately.

## 3) Service-integration pattern

- Transport layer (`pwntools` or local process) collects input values.
- Sage layer computes canonical math outputs.
- Adapter layer serializes outputs to exact service format (`f,e` tuples, decimal scalars, hex points).
- Invariant checks (`assert`) gate each stage to fail fast on wrong branches.

## 4) Reliability checklist

- Confirm ring/field consistency before solving (`GF(p)` vs `ZZ` vs `QQ`).
- Bound checks for small-root assumptions (error ranges, truncation bits).
- Validate recovered candidates by replaying original equations.
- Keep conversion boundaries explicit (`int`, field element, bytes) to avoid silent coercion bugs.

## 5) False-positive filter when inventorying “Sage usage”

When mining large crypto corpora, some files mention the string `sage` but do not actually use Sage APIs. Count a file as Sage-powered only if at least one of the following appears:
- `from sage.all import ...`
- `.sage` execution context
- explicit Sage objects/functions (`GF`, `EllipticCurve`, `PolynomialRing`, `LLL`, `small_roots`, etc.)
