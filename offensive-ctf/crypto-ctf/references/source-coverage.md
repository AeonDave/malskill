# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-crypto`
- Target skill: `crypto-ctf`
- Preserved files: 17

## Imported files and topic cues

### `source-skill.md`

- CTF Cryptography
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- Identify cipher type
- RSA quick check
- Quick factorization tools
- XOR analysis
- Hash identification
- SageMath (for lattice/ECC)
- Classic Ciphers
- Modern Cipher Attacks
- RSA Attacks
- Elliptic Curve Attacks
- Lattice / LWE Attacks
- ZKP & Constraint Solving
- Modern Cipher Attacks (Additional)
- Introspective CRC via GF(2) Linear Algebra
- CBC Padding Oracle Attack
- Bleichenbacher RSA Padding Oracle (ROBOT)
- Birthday Attack / Meet-in-the-Middle
- CRC32 Collision-Based Signature Forgery
- Blum-Goldwasser Bit-Extension Oracle

### `advanced-math.md`

- CTF Crypto - Advanced Mathematical Attacks
- Table of Contents
- Elliptic Curve Isogenies
- Height estimation via random walks to leaves
- Find path between two nodes via LCA
- Pohlig-Hellman Attack (Weak ECC)
- Factor curve order
- Solve DLP in each small subgroup
- Combine with CRT
- Baby-Step Giant-Step for General DLP
- Example: ElGamal with smooth p-1
- p-1 = 2 * 3^4 * 5 * 13 * 397 * 34703 *... (all small factors)
- Pohlig-Hellman: solve DLP in each prime-power subgroup, combine with CRT
- LLL Algorithm for Approximate GCD
- Collect 3 hints from server
- h_i = f * p_i + n_i (noise is small)
- Construct lattice where short vector reveals primes
- Short vector contains p1, p2, p3
- Recover f = (h1 - n1) / p1
- Merkle-Hellman Knapsack Cryptosystem via LLL
- Sage
- Identity matrix in upper-left (tracks which elements are selected)
- Target sum in bottom-right
- LLL reduction finds short vector where last element is 0

### `classic-ciphers.md`

- CTF Crypto - Classic Ciphers
- Table of Contents
- Vigenere Cipher
- Kgeneric caseki Examination for Key Length
- Atbash Cipher
- Polybius Square Cipher
- Example: "5211251521531412" -> pairs (5,2)(1,1)(2,5)(1,5)(2,1)(5,3)(1,4)(1,2)
- Substitution Cipher with Rotating Wheel
- XOR Variants
- Multi-Byte XOR Key Recovery via Frequency Analysis
- Cascade XOR (First-Byte Brute Force)
- c[i] = p[i] ^ c[i-1] (or similar cascade)
- Brute force first byte, rest follows deterministically
- XOR with Rotation: Power-of-2 Bit Isolation
- Weak XOR Verification Brute Force
- Deterministic OTP with Load-Balanced Backends
- OTP Key Reuse / Many-Time Pad XOR
- If one plaintext is known (or guessable, e.g., padded 'A' chars)
- Book Cipher
- Variable-Length Homophonic Substitution
- Iteratively replace most-frequent fixed groups with single symbols
- Grid Permutation Cipher Keyspace Reduction
- 5x5 grid substitution cipher — brute force row+column permutations
- Image-Based Caesar Shift Ciphers

### `ecc-attacks.md`

- CTF Crypto - Elliptic Curve Attacks
- Table of Contents
- Small Subgroup Attacks
- SageMath ECC basics
- Invalid Curve Attacks
- Singular Curves
- Smart's Attack (Anomalous Curves)
- Sage's discrete_log handles anomalous curves automatically
- ECC Fault Injection
- For each key bit position:
- If fault at bit i changes output -> key bit i affects computation
- Binary distinguisher: faulty_output == correct_output -> bit is 0
- Clock Group DLP via Pohlig-Hellman
- Given points on the curve, p divides (x^2 + y^2 - 1)
- May need to remove small factors
- 1. Recover p from points: gcd(x^2 + y^2 - 1) across known points
- 2. Factor p+1 into small primes
- 3. Pohlig-Hellman: solve DLP in each small subgroup, CRT combine
- 4. Compute shared secret, derive AES key (e.g., via MD5)
- Ed25519 Torsion Side Channel
- Query sign(uid=3, 2^t) for t = 0..255
- S_t = (MASTER_KEY * 2^t mod l) * P3
- Check: does doubling S_t match S_{t+1}?
- Reconstruct: MASTER_KEY ≈ l * (0.bit0 bit1 bit2...)_binary

### `exotic-crypto-2.md`

- CTF Crypto - Exotic Algebraic Structures (Part 2)
- Table of Contents
- BB-84 Quantum Key Distribution MITM Attack
- Strategy: Always use bgeneric case Z, always send value 1 to Bob
- Alice side: measure in random bases, record results
- Bob side: always receives 1 in bgeneric case Z
- Bob's key = all 1s (known to attacker)
- Alice's key = attacker's measured qbit values
- Heuristic: throttle Bob's correct-guess count to match Alice's
- Both parties verify by comparing subset of bits — attacker controls both sides
- After bgeneric case reconciliation:
- key_with_alice = [measured values where bases matched]
- key_with_bob = [all 1s]
- ElGamal Trivial DLP When B = p-1
- Check for trivial case
- Paillier LSB Oracle via Homomorphic Doubling
- Alternative: homomorphic subtraction to isolate each bit
- Differential Privacy Laplace Noise Cancellation
- Homomorphic Encryption Oracle Bit-Extraction
- Increment plaintext by 1 repeatedly via homomorphic add-1
- Detect when bit N overflows: ciphertext "wraps" at value 2^N
- Subtract recovered low bits to make value even
- Repeatedly divide by 2 and observe the resulting high bits
- ElGamal over Matrices via Jordan Normal Form

### `exotic-crypto.md`

- CTF Crypto - Exotic Algebraic Structures
- Table of Contents
- Braid Group DH — Alexander Polynomial Multiplicativity
- Key exchange:
- alice_pub = scramble(connect(pub_info, alice_priv), 1000)
- bob_pub = scramble(connect(pub_info, bob_priv), 1000)
- shared = sha256(str(normalize(calculate(connect(alice_priv, bob_pub)))))
- Eve computes shared secret from public values only:
- Recover Alice's private polynomial
- Shared secret = calc(alice_priv) * calc(bob_pub) = calc(bob_priv) * calc(alice_pub)
- Decrypt XOR stream cipher
- Winding numbers range from w_min to w_max (e.g., -1 to 5)
- Multiply all entries by t^w_max to get polynomial matrix
- Original: M[i][j] = t^(-w[i][j])
- Scaled:   M'[i][j] = t^(k - w[i][j])  (all non-negative powers)
- Recover true determinant: det(M) = det(M') / t^(k*n)
- Then: (1-t)^(n-1) divides det_true (topological property)
- Monotone Function Inversion with Partial Output
- Match SageMath's RealField(N) precision exactly:
- RealField(256) = 256-bit MPFR mantissa
- For decimal: mpmath.mp.dps = N sets decimal places
- Hierarchical search: determine unknown digits sequentially
- Step 1: Fix digits that are constant across all valid flags
- (compute forward for min/max valid flag, compare)

### `historical.md`

- CTF Crypto - Historical Ciphers
- Table of Contents
- Lorenz SZ40/42 (Tunny) Cipher
- Step 1: Get keystream from known plaintext
- Step 2: Compute delta keystream (THE key insight)
- delta_k = delta_chi XOR delta_psi
- Since psi only moves ~25% of the time, delta_k BIASES toward delta_chi
- Step 3: Recover delta_chi via majority vote at each wheel position
- Assume wheels start at position 1
- Step 4: Integrate delta_chi to get chi (2 candidates per wheel, start 0 or 1)
- Circular consistency: chi[0] ^ chi[-1] should equal delta_chi[P-1]
- Step 5: Subtract chi from keystream to get psi contribution
- Identify when psi steps: delta_psi = delta_k XOR delta_chi
- When ALL 5 bits of delta_psi are 0 → μ37 was off (psi didn't step)
- (Statistically very rare for all 5 cams to not change when stepping)
- Step 6: From stepping pattern, determine μ61 (period 61)
- μ61[pos] = 1 when we see psi resume stepping after being stopped
- Step 7: Cross-reference to get μ37 (period 37)
- μ37 position advances only when μ61=1
- Step 8: Determine psi wheels from delta_psi values when stepping occurs
- Look for repeating patterns with periods 43, 47, 51, 53, 59
- Step 9: Brute force remaining ambiguity
- Total candidates: 2^5 (chi) × 2^5 (psi) × 61×37 (μ positions) = 2,313,472
- Trivially brutable - decrypt and check if known plaintext matches

### `lattice-and-lwe.md`

- CTF Crypto - Lattice and LWE Attacks
- Table of Contents
- Quick Triage: Is This a Lattice Problem?
- Core Tools: LLL, BKZ, Babai, CVP, SVP
- LLL
- BKZ
- Babai nearest plane
- After building and reducing the lattice bgeneric case:
- CVP vs SVP
- Hidden Number Problem (HNP): Partial Nonce / Biased Nonce
- Minimal ECDSA partial-nonce workflow
- LCG and Truncated Output as a Lattice Problem
- Minimal truncated-LCG workflow
- LWE via Embedding and CVP
- Embedding-style lattice
- For ternary or sparse secrets
- Ring-LWE / Module-LWE Recognition Notes
- Flattening Ring-LWE to plain LWE
- After flattening, treat as plain LWE: b_vec = A_mat * s_vec + e_vec (mod q)
- Orthogonal Lattices: HSSP / AHSSP Style Recovery
- Subset Sum / Knapsack via Lattice Reduction
- Common Failure Modes
- Quick Checklist Before You Commit to Lattices

### `modern-ciphers-2.md`

- CTF Crypto - Modern Cipher Attacks (Continued)
- Table of Contents
- Blum-Goldwasser Bit-Extension Oracle
- Iterative plaintext recovery via bit-extension
- Hash Length Extension Attack
- Using HashPump (install: apt install hashpump)
- Outputs: new_signature and new_data (with padding bytes)
- Python: hashpumpy
- Compression Oracle / CRIME-Style Attack
- Baseline: empty input
- Recover secret byte-by-byte
- Hash Function Time Reversal via Cycle Detection
- Reverse from T_known to T_goal
- state is now the value at t_goal
- OFB Mode with Invertible RNG Backward Decryption
- Last block is zero-padded → ciphertext XOR 0 = keystream = RNG state
- Decrypt backwards
- Weak Key Derivation via Public Key Hash XOR
- Public key is available
- Seed from challenge (hardcoded/predictable)
- Derive AES key the same way the encryptor did
- Decrypt
- HMAC-CRC Linearity Attack
- CRC is linear: CRC(a XOR b) = CRC(a) XOR CRC(b)

### `modern-ciphers-3.md`

- CTF Crypto - Modern Cipher Attacks (Part 3)
- Table of Contents
- Custom Hash State Reversal via Known Intermediates
- Brute-force printable 4-byte blocks matching each hash
- CRC32 Brute-Force for Small Payloads
- Extract CRC from ZIP without decrypting
- Brute-force 5-byte printable content
- Noisy RSA LSB Oracle with Post-Hoc Error Correction
- Sponge Hash Collision via Meet-in-the-Middle on Partial State
- Forward: compute AES(random_10_bytes || 0x00*6), key on last 6 bytes
- Backward: compute AES_dec(target XOR random_c), check last 6 bytes
- CBC IV Forgery + Block Truncation for Authentication Bypass
- Forge IV to flip MD5 from registered user to "admin"
- Strip last 2 blocks (junk + PKCS padding block)
- Padding Oracle to CBC Bitflip Command Injection
- Step 1: Padding oracle recovers plaintext
- Step 2: CBC bitflip — modify block N-1 to change decrypted block N
- SPN Cipher Partial Key Recovery via S-box Intersection
- AES-CFB IV Recovery from Timestamp-Seeded PRNG
- File mtime IS the random seed used at encryption time
- Three-Round XOR Protocol Key Cancellation
- c1 = msg ^ clientKey
- c2 = msg ^ clientKey ^ serverKey
- c3 = msg ^ serverKey

### `modern-ciphers.md`

- CTF Crypto - Modern Cipher Attacks
- Table of Contents
- AES-CFB-8 Static IV State Forging
- ECB Pattern Leakage on Images
- Padding Oracle Attack
- CBC-MAC vs OFB-MAC Vulnerability
- Non-Permutation S-box Collision Attack
- LCG Partial Output Recovery
- output = state % N, state = (A * prev + C) % M
- Weak Hash Functions / GF(2) Gaussian Elimination
- Affine Cipher over Composite Modulus
- AES-GCM with Derived Keys
- Common key derivation chain:
- 1. Recover secret bytes (s_bytes) from crypto challenge
- 2. Unwrap session nonce: nonce = wrapped_nonce XOR SHA256(s_bytes)[:nonce_len]
- 3. Derive AES key: key = SHA256(s_bytes + session_nonce)
- 4. Decrypt AES-GCM
- AES-GCM Nonce Reuse / Forbidden Attack
- Given: two (ciphertext, tag, nonce) pairs with same nonce
- Step 1: Recover plaintext via CTR keystream reuse
- Step 2: Recover GHASH auth key H
- Construct tag difference polynomial in GF(2^128)
- T1 XOR T2 = P(H) where P is polynomial from ciphertext difference
- Factor P(H) = 0 to find H candidates

### `prng-attacks.md`

- CTF Crypto - PRNG Attacks
- Table of Contents
- Mersenne Twister Seed Recovery from Subset Sum
- After recovering seed, all future (and past) outputs are predictable
- MT19937 State Recovery via Constraint Propagation
- Model: each state word starts as a set of 2^32 candidates
- Partial observation: narrow candidates for observed indices
- Propagate: for each constrained cell, narrow related cells
- After ~20 partial observations across different positions:
- Most cells converge to single candidates → full state determined
- Rule 86 Cellular Automaton PRNG Reversal via Z3
- Forward-compute 128 rounds symbolically
- Constrain final state to known output
- Java LCG Seed Meet-in-the-Middle via Partial Modulo
- Phase 1: enumerate 2^18 low-18-bit candidates whose nextInt(62) parities match known chars
- Phase 2: extend each candidate to 48 bits, matching next outputs
- LCG Backward Stepping via Multiplicative Inverse
- LFSR Bit-Fold Recovery from ASCII Parity
- Collect parity constraints: each observed ASCII byte gives top_bit == 0
- Each bit of each byte is a linear combination of state bits
- Stack rows, solve in GF(2)
- Z3 Solve-Time Timing Oracle on PRNG
- randcrack-Fed DSA k Prediction
- Time-Seeded PRNG Offset via Format-String Global Write

### `prng.md`

- CTF Crypto - PRNG & Key Recovery
- Table of Contents
- Mersenne Twister (MT19937) State Recovery
- Given 624 consecutive outputs, recover state
- Create symbolic MT state
- For each observed 63-bit output
- MT State Recovery from random.random() Floats via GF(2) Matrix
- Load precomputed GF(2) magic matrix (from github.com/fx5/not_random)
- Collect 3360+ random.random() floats from the target
- Recover state and predict future outputs
- Verify predictions match remaining observations
- Forge password reset token (same hash the server computes)
- Time-Based Seed Attacks
- Set timezone to match target
- Look for File Modification Date/Time
- C srand/rand Synchronization via Python ctypes
- Load the SAME libc used by the target binary
- Seed at the same second as the binary starts
- Generate the same sequence as the binary's rand() calls
- Binary XORs each 4-byte block with rand() output
- include <stdlib.h>
- Layered Encryption Recovery
- LCG Parameter Recovery Attack
- Given sequence: [s0, s1, s2, s3,...]

### `rsa-attacks-2.md`

- CTF Crypto - RSA Attacks (Part 2: Specialized Techniques)
- Table of Contents
- RSA p=q Validation Bypass
- Server encrypts flag with our key, test decryption fails → leaks ciphertext c
- Decrypt with correct totient:
- RSA Cube Root CRT when gcd(e, phi) > 1
- For each prime, find all 3 cube roots of c mod p
- Try all 3^13 = 1,594,323 combinations
- Factoring n from Multiple of phi(n)
- RSA Signature Forgery via Multiplicative Homomorphism
- Factor target message and sign each factor separately
- Weak RSA Key Generation via Base Representation
- n = A*B^2 + C*B + D where A=kp*kq, D=tp*tq
- Brute-force kp, kq such that kp*kq == A
- RSA with gcd(e, phi(n)) > 1
- For small g, try integer root first
- Batch GCD for Shared Prime Factoring
- Usage: given list of public keys from smartcards
- RSA Partial Key Recovery from dp dq qinv
- dp, dq, qinv extracted from partial PEM; e is known (usually 65537)
- Similarly recover q from dq; verify qinv * q % p == 1
- RSA-CRT Fault Attack / Bit-Flip Recovery
- RSA Homomorphic Decryption Oracle Bypass
- Server refuses to decrypt enc_flag directly

### `rsa-attacks.md`

- CTF Crypto - RSA Attacks
- Table of Contents
- Small Public Exponent (Cube Root)
- Usage
- Common Modulus Attack
- Wiener's Attack (Small Private Exponent)
- Pollard's p-1 Factorization
- Hastad's Broadcast Attack
- Usage (e=3, three encryptions)
- Hastad Broadcast Attack with Linear Padding - Coppersmith
- Standard Hastad requires identical plaintext
- With linear padding: each ciphertext encrypts a_i*m + b_i
- Use CRT + Coppersmith's small_roots on the resulting polynomial
- Combine via CRT
- Coppersmith's method finds small root
- Franklin-Reiter Related Message Attack on RSA e=3
- SageMath
- Coppersmith Attack on Linearly-Related RSA Primes
- RSA with Consecutive Primes (Fermat Factorization)
- Multi-Prime RSA
- Factor N (easier when many primes)
- Compute phi using all factors
- RSA with Restricted-Digit Primes
- At each step k, we know p mod 10^k -> compute q mod 10^k = n * p^{-1} mod 10^k

### `stream-ciphers.md`

- CTF Crypto - Stream Cipher Attacks
- Table of Contents
- LFSR Stream Cipher Attacks
- Berlekamp-Massey Algorithm
- Known keystream bits (from known plaintext XOR ciphertext)
- Berlekamp-Massey in SageMath
- Recover initial state from first L bits
- Generate future keystream
- Correlation Attack
- Correlation attack on a single biased LFSR
- Known-Plaintext on LFSR Keystream
- Given 2L keystream bits, solve for L-bit state + L feedback taps
- Keystream relation: k[i+L] = c[0]*k[i] + c[1]*k[i+1] +... + c[L-1]*k[i+L-1] (mod 2)
- Galois vs Fibonacci LFSR
- Common LFSR Lengths and Polynomials
- Galois LFSR Tap Recovery via Autocorrelation
- PNG header is always: 89 50 4e 47 0d 0a 1a 0a 00 00 00 0d 49 48 44 52
- XOR first 16 encrypted bytes with this header to get 128 keystream bits
- Seed = first keystream block (LFSR state before first step)
- RC4 Second-Byte Bias Distinguisher
- Expected: random = N/256, RC4 = N/128 (2x more zeros)
- XOR Consecutive Byte Correlation Attack
- Observation: xorct[i] = ct[i] ^ ct[i+1]
- For two ciphertext/plaintext pairs:

### `zkp-and-advanced.md`

- CTF Crypto - ZKP, Solvers & Advanced Techniques
- Table of Contents
- ZKP Attacks
- Graph 3-Coloring
- Z3 SMT Solver Guide
- Boolean variables (for bit-level problems)
- Integer/bitvector variables
- Model flag as array of 4-byte chunks (how BPF sees it)
- Constraint: printable ASCII
- Extract constraints from BPF dump (seccomp-tools dump./binary)
- Example BPF constraint reconstruction
- Garbled Circuits: Free XOR Delta Recovery
- Encrypted rows: E_i = AES(key_a_i XOR key_b_i, G_out_f(a,b))
- XOR of three rows where AES inputs differ by delta causes cancellation
- Reveals delta directly, then compute: W_1 = W_0 XOR delta
- Bigram/Trigram Substitution -> Constraint Solving
- Shamir Secret Sharing with Deterministic Coefficients
- In GF(p), find roots of h(s) via gcd with x^p - x
- h(s) = s + g(s)*x_0 +... + g^9(s)*x_0^9 - y_0
- Compute x^p mod h(x) via binary exponentiation with polynomial reduction
- gcd(x^p - x, h(x)) = product of (x - root_i) for all roots
- Race Condition in Crypto-Protected Endpoints
- Launch 80 processes with unique signature modifications
- Garbled Circuits: AES Key Recovery via Metadata Leakage

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
