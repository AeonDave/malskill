---
name: crypto-technique
description: "Auth/lab: cryptanalysis methodology; RSA/ECC, PRNG, padding/oracle, symmetric issues, key/ciphertext/signature triage, proof workflow."
license: MIT
compatibility: "Linux/macOS/WSL recommended; Python 3.9+; SageMath for advanced techniques."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Crypto Technique

Goal: help the agent diagnose cryptographic weaknesses, select the right attack, and execute exploitation to recover secrets—keys, plaintexts, random state, or authentication bypasses.

## When this technique applies

- Encrypted data with weak or custom cipher implementation.
- Public cryptographic key material (RSA, ECC, DSA) with non-standard properties.
- Oracle-based systems: padding oracles, timing leaks, signature verification errors.
- Pseudo-random number generators with biased output or insufficient entropy.
- Symmetric cipher misuse: ECB mode, IV reuse, weak key derivation.
- Ransomware or malware encryption routines requiring algorithm, key hierarchy, and recovery-feasibility analysis.
- Mathematical shortcuts: incomplete prime checking, careless modulus construction, protocol design flaws.

## Boundary with other skills

- **vs. recon-technique**: recon maps the attack surface and discovers services. Once you have cipher/key material in hand, crypto-technique takes over.
- **vs. network-technique**: network-technique handles protocol analysis and PCAP forensics. Crypto-technique assumes you have extracted the cryptographic artifact (ciphertext, key, signature).
- **vs. offensive-tools/cryptography/**: tool skills (rsactftool, sagemath, cyberchef) describe command syntax and flags. Crypto-technique is the decision flow: "should I use SageMath or RsaCtfTool here?"
- **vs. programming skills**: when you need to script an oracle interaction or build a custom solver, load the relevant programming skill (python-patterns, python-testing) *after* crypto-technique tells you what to build.

## Initial triage

Before attempting attacks, reduce the problem to a concrete primitive and rank the most plausible weaknesses.

- **Starting state**: do you have source code, ciphertexts, public keys, signatures, oracle access, PRNG outputs, or protocol transcripts?
- **First questions**: what primitive is involved (RSA, ECC, DH, symmetric, hash/PRNG, constraint system), what exact parameters are known, and is there a structural anomaly or observable oracle?
- **Immediate actions**: extract parameters, test the highest-signal hypotheses first, and define what successful validation looks like before scripting or brute force.
- **Tool-family direction**: use `cyberchef` for fast transform sanity checks, `rsactftool` for common weak-RSA triage, `sagemath` for algebraic or lattice work, and Python/pwntools only after the attack shape is clear.
- **Escalation rule**: do not parallelize many unrelated attacks; pick the top 1-3 based on evidence and iterate from results.

## Agent operating model

Cryptanalysis is a **structured diagnosis → decision → execution** loop:

```
Loop:
  1. Parse the problem: read source code, dump key/ciphertext, connect to oracle.
  2. Extract parameters: key size, exponents, curve equation, moduli, nonce/IV properties.
  3. Diagnose weakness category: check parameter tables, structural anomalies, oracle behavior.
  4. Select primary attack: consult decision trees in technique references.
  5. Prepare exploit: build oracle harness, write solver script, or invoke tool.
  6. Execute: measure timing/errors, recover secret, validate correctness.
  7. Pivot: escalate to next stage (decrypt file, forge signature, assume compromised identity).

Exit when: plaintext recovered, key material compromised, or service bypassed.
```

Do not attempt multiple attacks in parallel without first ranking them by signal strength and likelihood.

---

## Phase 1 — Problem diagnosis

Parse and extract cryptographic artifacts. Understand the attack surface before selecting tools.

### 1.1 Source code review

If source is available (Python, OpenSSL, Go), look for:

- **Key generation**: custom random? Weak seed? Reused entropy?
- **Modulus construction**: distinct primes? Known factors? Small primes?
- **Exponents**: small `e` in RSA? Weak `d` values? Nonce reuse in DSA/ECDSA?
- **Cipher mode**: ECB, CBC with predictable IV, CTR with reused counter?
- **Padding**: custom or standard (PKCS#1 v1.5)? Missing validation?
- **Key derivation**: hardcoded? Low entropy input? Weak hash function?
- **Randomness**: `random.randint()` instead of `secrets.randbelow()`? Biased LFSR?

Typical red flags:
- `random.seed()` with predictable value (timestamp, PID).
- `random.randint()` for cryptographic operations.
- Hardcoded keys or weak key stretching.
- Custom cipher implementation (almost always broken).

### 1.2 Key material extraction

Dump and inspect all available cryptographic parameters.

**RSA:**
- Public exponent `e`, modulus `n`, ciphertext `c`.
- If private key available: extract `p`, `q`, `d`, `dp`, `dq`, `qinv`.
- Check: is `n` factorable? Is `e` small? Is `d` abnormally small?

**ECC:**
- Curve parameters: `p`, `a`, `b`, base point `G`, order `n`.
- Public key (point coordinates), private key scalar.
- Check: does `p±1` factor smoothly? Is the curve singular or anomalous?

**DSA/ECDSA:**
- Signature pairs `(r, s)`, nonce `k`, message hash.
- Check: do multiple signatures share the same `k`? Is `k` drawn from a small space?

**Symmetric:**
- Key size, IV/nonce value, plaintext/ciphertext blocks.
- Check: IV reuse? Predictable IV? Weak key derivation?

**PRNG:**
- Output samples, internal state (if leaked), seed.
- Check: is output biased? Can state be recovered from samples?

### 1.3 Oracle and timing characterization

If attacking an oracle service (padding oracle, timing leak, signature verification error):

- Measure baseline response times (no oracle activity).
- Test oracle behavior: valid vs. invalid inputs, edge cases.
- Probe timing differences systematically (e.g., 100s of trials per decision point).
- Confirm signal-to-noise ratio before committing to an oracle attack (SNR > 5 preferred).

Load `references/oracle-detection-checklist.md` before building an oracle exploit; it separates real cryptographic signal from parser, cache, WAF, auth, and network-noise artifacts.

Use `offensive-tools/network/*` to interact with services; use `python-patterns` or pwntools for harness scripting.

---

## Phase 2 — Attack selection

Classify the problem and match it to a primary attack. Most crypto breaks reduce to:

1. **Factoring `n` or solving DLP** → choose based on key structure.
2. **Exploiting weak randomness** → PRNG or nonce reuse.
3. **Oracle interaction** → padding, timing, or signature validation.
4. **Cipher mode abuse** → ECB pattern leakage, IV reuse, block manipulation.
5. **Mathematical shortcut** → modulus construction, curve singularity, protocol flaw.

### 2.0 Known-problem hint research gate

If the primitive and anomaly are known but the attack construction is still missing after local tests, load `knowledge/known-problem-hint-research`.

Use it to find one decisive external hint — a paper, implementation note, technical article, public writeup, or discussion that matches the current fingerprint. Do not use it for broad crypto learning or before problem diagnosis; return with a local test and validation condition.

### 2.1 RSA weak-key decision tree

See `references/rsa-technique.md`.

**Quick triage:**
- Small `e` (3 or 5)? → Try cube/fifth root first.
- `e` close to `φ(n)`? → Wiener's attack likely.
- Multiple public keys with same `n`? → Common modulus attack.
- Multiple ciphertexts with same message and different `e`? → Hastad broadcast.
- Can you time oracle responses? → Bleichenbacher's attack (PKCS#1 v1.5) or Manger's attack (OAEP / PKCS#1 v2.x).
- Does `p-1` or `q-1` factor smoothly? → Pollard p-1 or ECM.
- Consecutive-like primes (close or near-squares)? → Fermat factorization.

Tool families:
- `offensive-tools/cryptography/rsactftool/` — automated attack selection and execution.
- `offensive-tools/cryptography/sagemath/` — lattice-based attacks (Wiener, Boneh-Durfee), custom factorization.
- `offensive-tools/cryptography/sagemath/` — elliptic curve factorization (ECM), finite-field arithmetic, custom number-theory scripts.

### 2.2 ECC and DSA weak-key decision tree

See `references/ecc-technique.md`.

**Quick triage:**
- Curve order `n` is smooth? → Pohlig-Hellman reduction.
- Multiple signatures with same nonce `k`? → Recover private key directly.
- Nonce `k` drawn from small space? → Brute force or meet-in-the-middle.
- Curve is anomalous (order = p)? → Smart's attack via isogeny.
- Curve is singular? → Reduce to additive/multiplicative group.

Tool families:
- `offensive-tools/cryptography/sagemath/` — ECDLP solving, singular curve reduction.
- `offensive-tools/cracking/hashcat/` — brute-force nonce spaces if small enough.

### 2.3 Lattice-based attack decision tree

See `references/lattice-lwe-technique.md`.

Use lattice techniques when:
- You have partial information (e.g., high bits of `d` in RSA).
- You're recovering from biased/truncated PRNG output.
- Problem involves LWE, subset sum, or Knapsack.
- Mathematical constraint system suggests linear algebra solution.

Tool families:
- `offensive-tools/cryptography/sagemath/` — LLL lattice reduction, Coppersmith's method.
- `offensive-tools/cryptography/sagemath/` combined with `python-patterns` for custom constraint modeling.

### 2.4 PRNG and oracle decision tree

See `references/prng-oracle-technique.md`.

- **PRNG output biased?** → Recover internal state via LLL or meet-in-the-middle.
- **Padding oracle?** → Bleichenbacher's attack (PKCS#1 v1.5) or Manger's attack (OAEP).
- **Timing oracle?** → Cache timing, branch prediction, or response latency.
- **Signature verification oracle?** → Fault injection, signature forgeability, or existential forgery.

Tool families:
- `offensive-tools/cryptography/sagemath/` — lattice recovery for LCG/LFSR state.
- `offensive-tools/network/*` — oracle interaction harness (pwntools, boofuzz).
- Custom Python scripts using `python-patterns` for oracle methodology.

### 2.5 Symmetric cipher decision tree

See `references/symmetric-cipher-technique.md`.

- **ECB mode?** → Block pattern leakage, chosen-plaintext recovery.
- **CBC with predictable IV?** → Bit-flipping attacks, IV forgery.
- **Stream cipher reuse?** → XOR keystream recovery from two ciphertexts.
- **AES-GCM nonce reuse?** → Recover authentication key, forge arbitrary ciphertexts.

Tool families:
- `offensive-tools/cryptography/cyberchef/` — mode-specific decryption workflows, plaintext recovery.
- Custom Python (cryptography library) for cipher mode exploitation.

### 2.6 Diffie-Hellman weak parameter attacks

See `references/dh-technique.md`.

**Quick triage:**
- Small group prime `p` (< 1024 bits)? → Discrete log via Pohlig-Hellman or index calculus is feasible.
- `p-1` factors smoothly? → Pohlig-Hellman reduction; complexity collapses with small factors.
- Same `g^a mod p` reused across sessions with same `p`? → Logjam / pre-computation attack.
- Group order `q` is small (e.g., `p = 2q+1` not satisfied, small subgroup)? → Small subgroup confinement attack.
- `g` is not a generator of the full group? → Attacker can confine secrets to a small subgroup.
- Static DH without ephemeral keys? → Passive decryption of captured sessions if `a` is recovered.

Tool families:
- `offensive-tools/cryptography/sagemath/` — discrete log solving, Pohlig-Hellman, index calculus for small primes.

### 2.7 Constraint solving decision tree

Use constraint solvers when the problem reduces to a set of equations or logical conditions over unknown variables:

- **Multiple equations relating unknowns?** → Z3 SMT solver (handles linear/nonlinear integer constraints).
- **Polynomial system over finite field?** → SageMath's `solve_mod()` or Gröbner basis.
- **PRNG recovering seed from outputs?** → Z3 or LLL depending on linearity.
- **Custom cipher with known input/output pairs?** → Z3 bit-vector theory.

```python
from z3 import *

# Example: recover seed from LCG outputs
seed = BitVec('seed', 32)
s = Solver()
# LCG: state = (a * seed + c) % m
a, c, m = 1664525, 1013904223, 2**32
out1, out2 = 0x12345678, 0x9abcdef0   # known outputs
s.add((a * seed + c) % m == out1)
if s.check() == sat:
    print(s.model()[seed])
```

Tool families:
- `offensive-tools/cryptography/sagemath/` — algebraic solving, Gröbner basis, polynomial systems.
- `z3` — SMT constraint solving; `pip install z3-solver`.

### 2.8 Finite field and secret sharing decision tree

See `references/finite-field-technique.md`.

- **Problem provides `(x_i, y_i)` tuples with a stated prime?** → Shamir secret sharing → Lagrange interpolation over `GF(p)` or `GF(p^k)`.
- **Polynomial degree stated or inferable?** → Collect `degree+1` shares; recover with Sage's `lagrange_polynomial()`.
- **Values are extension field elements?** → Use `GF(p^k)` field; constant term of recovered polynomial is the secret.

Tool families:
- `offensive-tools/cryptography/sagemath/` — Lagrange interpolation, `GF(p)`, `GF(p^k)` field arithmetic.

### 2.9 Ransomware encryption analysis

See `references/ransomware-encryption-analysis.md`.

- **Need to identify file encryption algorithm/mode?** → Static crypto API and constant analysis, then dynamic API breakpoints.
- **Need decryption feasibility?** → Determine key hierarchy, randomness source, nonce/IV reuse, and whether keys exist in memory or file metadata.
- **Hybrid crypto suspected?** → Separate per-file symmetric keys from public-key wrapping and test implementation flaws before claiming recovery.

---

## Phase 3 — Execution

Once the attack is selected:

1. **Assemble the harness**: oracle interaction, key parsing, result validation.
2. **Run the attack**: invoke tool or script; monitor for signal.
3. **Validate results**: re-encrypt, verify signature, test decryption.
4. **Pivot**: use recovered secret for next stage (file decryption, service authentication, privilege escalation).

### 3.1 Tool invocation workflow

- **Weak RSA key?** → Use `offensive-tools/cryptography/rsactftool/` for automated factorization and decryption.
- **Mathematical modeling needed?** → Use `offensive-tools/cryptography/sagemath/` with custom scripts for Coppersmith, LLL, or ECDLP.
- **Constraint system (equations over unknowns)?** → Use `z3` SMT solver (`pip install z3-solver`) for bit-vector and integer constraint solving; fall back to SageMath for polynomial systems.
- **Oracle harness needed?** → Use pwntools (python-patterns) + `offensive-tools/cryptography/sagemath/` or custom brute-force.
- **Plaintext recovery from ciphertext?** → Use `offensive-tools/cryptography/cyberchef/` for offline workflows; load `offensive-tools/cryptography/cyberchef/` Node API for programmatic chaining.

### 3.2 Tool selection quick map

| Problem shape | First tool skill | Why |
|---|---|---|
| RSA public key/ciphertext bundle | `offensive-tools/cryptography/rsactftool/` | Automates common weak-RSA attacks and factorization checks |
| Lattice, finite field, ECC, DH, custom math | `offensive-tools/cryptography/sagemath/` | Algebraic modeling and exact arithmetic |
| Encoding, mode experimentation, byte-level transforms | `offensive-tools/cryptography/cyberchef/` | Fast reversible transform chains and visual sanity checks |
| Hash/password recovery | `cracking-technique` + `offensive-tools/cracking/hashcat/` or `john/` | Candidate generation and offline cracking strategy |
| Oracle interaction | `coding/python-patterns/` + pwntools/socket harness | Repeatable measurements and controls |

### 3.3 Common pitfalls

- Running all attacks in parallel → wastes resources. Rank by likelihood, run top 3 first.
- Trusting a single oracle query → confirming the same result 10–100 times reduces noise.
- Forgetting to validate recovered plaintext → always re-encrypt and compare ciphertexts.
- Using Sage for pure brute force → use hashcat or custom C for speed. Use Sage for algebraic structure.
- Ignoring endianness, padding, or serialization → cryptographic bugs live in the details.

---

## References

- `references/problem-diagnosis.md` — detailed problem reading checklist and parameter extraction.
- `references/rsa-technique.md` — RSA weakness diagnosis, attack selection matrix, quick-reference attack conditions.
- `references/ecc-technique.md` — ECC and DSA weakness diagnosis, nonce reuse patterns, curve singularity checks.
- `references/lattice-lwe-technique.md` — LLL lattice reduction, Coppersmith's method, LWE embedding, constraint modeling.
- `references/prng-oracle-technique.md` — PRNG state recovery, oracle timing/error-based methodology, Bleichenbacher/Manger padding oracles.
- `references/oracle-detection-checklist.md` — Oracle confirmation workflow: observable channels, timing gates, controls, and exploit-readiness criteria.
- `references/symmetric-cipher-technique.md` — ECB, CBC, CTR, and GCM mode weaknesses; plaintext recovery techniques.
- `references/finite-field-technique.md` — Shamir secret sharing recovery, Lagrange interpolation over GF(p) and GF(p^k), field extension arithmetic.
- `references/dh-technique.md` — Diffie-Hellman weak parameter attacks: small prime, Pohlig-Hellman, small subgroup confinement, logjam, static DH session recovery.
- `references/ransomware-encryption-analysis.md` — Malware/ransomware encryption triage: API identification, key hierarchy, file format analysis, memory extraction, and recovery-feasibility assessment.

---

## Recommended workflow sequence

1. **Read the problem**: `references/problem-diagnosis.md`.
2. **Classify the cryptosystem**: RSA, ECC, DH, PRNG, symmetric, constraint-based, or oracle-based.
3. **Consult the relevant technique reference** to narrow attack choices.
4. **Select primary attack** based on parameter constraints.
5. **Load the appropriate tool skill** from `offensive-tools/cryptography/` to execute.
6. **Pivot to next stage** (decryption, signature forgery, service bypass).

