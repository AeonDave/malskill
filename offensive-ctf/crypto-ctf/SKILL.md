---
name: crypto-ctf
description: "Lab/CTF: crypto challenges; ciphertexts, keys, signatures, oracles, transcripts, PRNG, RSA/ECC/lattice/math protocol code."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Crypto CTF

Goal: solve cryptography challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- ciphertexts, keys, signatures, oracles, transcripts, proofs, PRNG outputs, or mathematical protocol code
- RSA, ECC, DH, DSA/ECDSA, lattice/LWE, PRNG, symmetric-mode, stream-cipher, ZKP, secret-sharing, or exotic algebraic weaknesses

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load references only for deep technique details.
4. Choose the smallest tool chain that can produce a validation signal.
5. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `crypto-technique`
- `cracking-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `rsactftool`
- `sagemath`
- `cyberchef`
- `hashcat`
- `john`
- `coding/python-patterns`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Category-specific quick pivots

- Extract parameters before choosing attacks: modulus, exponent, curve order, nonce, IV, oracle response, random source, and serialization.
- Rank attacks by structural evidence: factorability, smoothness, nonce reuse, small roots, linear recurrence, or mode misuse.
- Validate recovered material by re-encryption, signature verification, oracle replay, or known plaintext.

## Targeted hint research gate

If local triage has already classified the primitive, ranked attacks, and still hit a specific wall, load `knowledge/known-problem-hint-research`.

Use it only as a post-triage spike to find a paper, blog, article, public analysis, source discussion, or implementation note that maps to the exact problem fingerprint. Do not use it as broad search or before the local pivot ledger has evidence.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve coverage by keeping every operational topic reachable from the Resources routing below.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

### Modern Cipher Attacks
- [references/modern-cipher-modes-and-forgery.md](references/modern-cipher-modes-and-forgery.md) — AES/CFB/CBC/CTR/GCM/OFB mode failures, padding and decode oracles, bit-flip/cut-and-paste forgeries, cookie/session tampering, and practical ciphertext manipulation workflows.
- [references/modern-hash-mac-and-collision-attacks.md](references/modern-hash-mac-and-collision-attacks.md) — Hash/MAC weaknesses: length extension, CRC misuse, chosen-prefix and multi-collision workflows, linear-MAC breaks, and aggregate-hash forgery patterns.
- [references/modern-oracles-protocols-and-custom-crypto.md](references/modern-oracles-protocols-and-custom-crypto.md) — Protocol and design failures: Bleichenbacher/Rabin/Blum-Goldwasser oracles, SRP and KDF flaws, reduced-round/custom constructions, and algebraic attack pivots.

### RSA Attacks
- [references/rsa-attacks.md](references/rsa-attacks.md) — Small exponent recovery, common modulus attacks, Wiener's attack, Pollard p-1 factorization, Hastad broadcast, Fermat factorization, multi-prime RSA, restricted-digit primes, Coppersmith attacks, Manger's padding oracle, specialized RSA (p=q bypass, gcd(e,phi)>1, phi-multiple factoring, CRT faults, homomorphic bypass, batch GCD, partial key recovery), signature forgery (homomorphic, Bleichenbacher, low-exponent), ROCA attack (CVE-2017-15361), timing attacks, dependent-prime RSA, three-key GCD.

### Exotic Cryptography
- [references/exotic-crypto.md](references/exotic-crypto.md) — Braid group DH (Alexander polynomial multiplicativity), monotone function inversion, tropical semiring residuation, Paillier homomorphic encryption, Hamming codes, ElGamal variants, format-preserving encryption Feistel, icosahedral symmetry group cipher, Goldwasser-Micali ciphertext replication, BB-84 quantum key distribution MITM.

### PRNG & Key Recovery
- [references/prng.md](references/prng.md) — Mersenne Twister state recovery (untemper, symbolic solving), MT from random.random() floats via GF(2) matrix (not_random library), time-based seed attacks, C srand/rand via ctypes, layered encryption recovery, LCG parameter recovery, ChaCha20 key recovery, GF(2) matrix PRNG seed recovery, middle-square PRNG brute-force, deterministic RNG from flag bytes (hill climbing), byte-by-byte oracle, RSA key reuse, logistic map/chaotic PRNG seed recovery, V8 XorShift128+ state recovery (Math.random prediction), and CTF-era advanced techniques (MT constraint propagation, Z3 timing oracle, cellular automaton LFSR, Java LCG MITM), EC-LCG state recovery from truncated EC coordinates.

### Elliptic Curve Attacks
- [references/ecc-attacks.md](references/ecc-attacks.md) — Small subgroup attacks, invalid curve attacks, Smart's attack, ECDSA nonce reuse, curve order factorization, twist attacks, anomalous curves, special-form curve weaknesses, BLS aggregate signature rogue-key attacks, proof-of-possession bypass.

### Advanced Mathematics
- [references/advanced-math.md](references/advanced-math.md) — Isogenies and CSIDH, Pohlig-Hellman algorithm, LLL lattice reduction, Coppersmith small-roots method, Clock group DLP, Babai nearest-plane algorithm, CVP/SVP solvers, GF(2) linear algebra, generalized birthday attacks, sparse polynomial systems.

### Lattice & LWE
- [references/lattice-and-lwe.md](references/lattice-and-lwe.md) — Lattice problems (SVP, CVP, HNP), LWE attacks (Gaussian elimination, BKZ reduction), hidden number problem, ECDSA partial-nonce recovery via lattice, LWE parameter tweaking, NTRU attacks.

### Classic Ciphers
- [references/classic-ciphers.md](references/classic-ciphers.md) — Vigenere cipher frequency analysis, Atbash simple substitution, Polybius square attacks, substitution cipher key recovery, XOR-based cipher analysis, pattern matching and constraint solving.

### Stream Ciphers
- [references/stream-ciphers.md](references/stream-ciphers.md) — LFSR feedback polynomial recovery, RC4 state recovery and keystream prediction, XOR-based stream cipher weaknesses, mode misuse (reusing nonces/IVs), correlated keystream analysis.

### Historical Ciphers
- [references/historical.md](references/historical.md) — Lorenz SZ40/42 rotor machine analysis, book cipher key recovery, pre-modern cryptanalysis techniques, mechanical cipher exploitation.

### ZKP & Advanced Techniques
- [references/zkp-and-advanced.md](references/zkp-and-advanced.md) — Zero-knowledge proof attacks, interactive proof verification bypass, Z3 SMT solver application, garbled circuits (generator/evaluator attacks), Shamir secret sharing, race conditions in crypto protocols, Fiat-Shamir heuristic vulnerabilities.
