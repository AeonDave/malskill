# PRNG and Oracle Technique Reference

Methodology for PRNG state recovery, oracle interaction attacks (padding oracle, timing leaks), and exploitation.

---

## Category 1: PRNG State Recovery

### 1.1 Biased Output Recognition

**What makes a PRNG exploitable?**
- **Weak seeding**: seed is predictable (timestamp, PID, hardcoded).
- **Biased output**: bytes/bits are not uniformly random.
- **Small state**: internal state space is small enough to brute-force or recover.
- **Leakage**: partial state exposed (e.g., truncated output).

**Recognition checklist:**

```python
import math
from collections import Counter

outputs = [get_output() for _ in range(10000)]

# 1. Check entropy
counts = Counter(outputs)
entropy = -sum((c/len(outputs)) * math.log2(c/len(outputs)) for c in counts.values())
expected_entropy = log2(2^output_bits)
print(f"Actual entropy: {entropy}")
print(f"Expected entropy: {expected_entropy}")
print(f"Ratio: {entropy / expected_entropy}")
# If ratio < 0.9, PRNG is biased

# 2. Check for clustering or patterns
# Plot outputs, look for visual structure
import matplotlib.pyplot as plt
plt.scatter(range(len(outputs)), outputs)
plt.show()

# 3. Check autocorrelation
# Does output[i] correlate with output[i+1] or output[i+k]?

# 4. Check if output space is small
# If all outputs are < 2^16, state is likely small
print(f"Max output: {max(outputs)}")
print(f"Bits needed: {max(outputs).bit_length()}")
```

---

### 1.2 LCG (Linear Congruential Generator) State Recovery

**Preconditions:**
- PRNG is LCG: `x_{i+1} = (a*x_i + c) mod m`.
- You have multiple consecutive outputs (or truncated outputs).

**Why it works:**
LCG is linear; given enough outputs, you can solve for `a`, `c`, `m` via linear algebra.

**Operational:**

```python
# Collect consecutive outputs
outputs = [y1, y2, y3, y4, y5, ...]

# If outputs are full state:
# x_{i+1} = (a*x_i + c) mod m
# x_{i+2} = (a*x_{i+1} + c) mod m
# x_{i+3} = (a*x_{i+2} + c) mod m

# Linear system:
# y1 = x0
# y2 = a*y1 + c (mod m)
# y3 = a*y2 + c (mod m)

# Solve:
# y3 - y2 = a*(y2 - y1) (mod m)
# a = (y3 - y2) / (y2 - y1) (mod m)  -- if inverse exists

def lcg_recover(outputs, m=None):
    # Assume m is known or try common values (2^31, 2^32, etc.)
    y1, y2, y3 = outputs[0], outputs[1], outputs[2]
    
    if m is None:
        # Guess m from difference patterns
        m = lcg_recover_modulus(outputs)
    
    # Solve for a
    denom = (y2 - y1) % m
    numer = (y3 - y2) % m
    
    try:
        a = (numer * pow(denom, -1, m)) % m
    except:
        return None  # No inverse; try different m
    
    # Solve for c
    c = (y2 - a*y1) % m
    
    return a, c, m

# Verify and continue prediction
a, c, m = lcg_recover(outputs, m=2**32)
x_next = (a * outputs[-1] + c) % m
print(f"Next output: {x_next}")
```

---

### 1.3 LFSR (Linear Feedback Shift Register) Recovery

**Preconditions:**
- PRNG is LFSR-based (used in some embedded systems and older ciphers).
- You have consecutive output bits.

**Why it works:**
LFSR is linear over GF(2). Given enough bits, solve linear system over GF(2).

**Operational:**

```python
# LFSR with feedback polynomial of degree n
# Output: sequence of bits

# Given: n+k bits of output
# Recover: feedback polynomial (n bits determine the rest)

def lfsr_recover(bits, n_expected):
    # Assume LFSR has n flip-flops
    # Last n bits depend linearly on first n bits
    
    # Build system over GF(2)
    from sage.all import *
    
    F2 = GF(2)
    A = matrix(F2, [[bits[i+j] for j in range(n_expected)] for i in range(len(bits) - n_expected)])
    b = vector(F2, bits[n_expected:])
    
    # Solve A*x = b
    try:
        feedback = A.solve_right(b)
        return feedback
    except:
        return None  # System has no solution; try different n

# Test feedback poly
feedback = lfsr_recover(output_bits, n=32)
if feedback:
    # Predict next bits
    state = vector(GF(2), output_bits[-32:])
    for _ in range(100):
        next_bit = (sum(f*s for f, s in zip(feedback, state))) % 2
        state = vector(GF(2), list(state[1:]) + [next_bit])
        print(next_bit, end='')
```

---

### 1.4 Seed Recovery via Brute Force or Timing

**Preconditions:**
- PRNG has small seed space (< 2^32 or < 2^40).
- You know seed generation function or can measure timing.

**Operational:**

```python
# Brute force seed space
import hashlib
import time

observed_output = [y1, y2, y3, ...]

for seed in range(2**32):
    rng = SeededPRNG(seed)
    predicted = [rng.next() for _ in range(len(observed_output))]
    
    if predicted == observed_output:
        print(f"Found seed: {seed}")
        break
```

---

### 1.5 Legendre Symbol PRNG (Quadratic Residue Bit Generator)

**What this looks like:**
A PRNG generates bits by computing whether its internal state `a` is a quadratic residue mod `p`:
- `bit = 1 if pow(a, (p-1)//2, p) == 1 else 0`
- `a += 1` (state increments by 1 each step)

The output is the Legendre symbol sequence of consecutive integers mod p.

**State leakage via DLP:**
If a protocol produces signatures of the form `sig = m^a mod p` (ElGamal-style), the internal state `a` is recoverable by DLP: `a = log(sig, m)` in `GF(p)`.

**Operational — DLP state recovery:**

```python
from sage.all import log, GF
import hashlib

P = <prime>  # Field prime
F = GF(P)

def recover_state_from_signature(sig, msg_bytes):
    """Given sig = m^a mod P where m = H(msg), recover a via DLP."""
    h = hashlib.sha512(msg_bytes).digest()
    m = int.from_bytes(h, "big") % P
    a = int(log(F(sig), F(m)))  # DLP in GF(P)
    return a

# From signature, recover 500 bits of internal PRNG state
# sig encodes 500 consecutive positions: a, a+1, ..., a+499
# Each position i gives bit = 1 if pow(i, (P-1)//2, P) == 1
def sig_to_bits(sig, msg_bytes, num_bits=500):
    a = recover_state_from_signature(sig, msg_bytes)
    bin_x = bin(a)[2:].zfill(num_bits)
    return list(map(int, bin_x))
```

**BSGS seed synchronization:**

Once you have a sequence of output bits, find which seed generated them using baby-step giant-step (BSGS): step through starting positions in large chunks, match a chunk of bits against a known dictionary.

```python
SIZE = 34           # Bits per dword for matching
STEP = 2**(SIZE//2) # Giant step

# Build dictionary from observed bits
dwords = {}
for i in range(0, len(prng_outs), SIZE):
    dword = int(''.join(str(b) for b in prng_outs[i:i+SIZE]), 2)
    dwords[dword] = i // SIZE  # Record which chunk index

class LegendreRNG:
    def __init__(self, p):
        self.p = p
        self.a = 1  # Internal state

    def getrandbits(self, l):
        bits = []
        for _ in range(l):
            while True:
                nxt = pow(self.a, (self.p - 1) // 2, self.p)
                bits.append(1 if nxt == 1 else 0)
                self.a = (self.a + 1) % self.p
                if self.a == 0:
                    self.a += 1
                break
        return int(''.join(map(str, bits)), 2)

# Enumerate starting seeds in giant steps
rng = LegendreRNG(P)
rng.a = 1  # Start at 1

while True:
    my_dword = rng.getrandbits(SIZE)
    if my_dword in dwords:
        found_seed = rng.a  # Current state after match
        found_index = dwords[my_dword]
        print(f"Seed found: {found_seed}, at chunk index {found_index}")
        break
    rng.a += STEP  # Giant step

# Sync remaining bits and generate key material
rng.a = found_seed
remaining_bits = (found_index + 1) * SIZE
rng.getrandbits(remaining_bits - SIZE)  # Fast-forward to sync point

# Now predict future outputs
otp = bin(rng.getrandbits(flag_len * 8))[2:]
```

**Complexity:** `O(N / STEP)` steps where `N` is the full state space and `STEP = sqrt(N)` → O(sqrt(N)).

**When to suspect:**
- PRNG emits single bits, not integers.
- Bit generation involves modular exponentiation or a primality-style test.
- Protocol sends ElGamal-like signatures that could encode internal PRNG state via DLP.
- `pow(a, (p-1)//2, p)` or equivalent Legendre symbol calculation appears in target source.

---

### 1.6 MT19937 Full State Recovery

**Pattern:** Python's `random` module uses MT19937. After observing 624 consecutive 32-bit outputs, you can reconstruct the full PRNG state and predict all future outputs.

**Why it works:**
MT19937 tempers a 624-word internal state via invertible transformations. Inverting these transforms (untempering) recovers the raw state. Setting the state directly into `random.Random` allows prediction.

```python
import random

def untemper(y):
    """Invert all four MT19937 tempering steps."""
    # Undo: y ^= y >> 18
    y ^= y >> 18
    # Undo: y ^= (y << 15) & 0xefc60000
    y ^= (y << 15) & 0xefc60000
    # Undo: y ^= (y << 7) & 0x9d2c5680  (need 7-bit iterations)
    b = 0x9d2c5680
    t = y
    for _ in range(4):
        t = y ^ ((t << 7) & b)
    y = t
    # Undo: y ^= y >> 11
    t = y
    for _ in range(3):
        t = y ^ (t >> 11)
    y = t
    return y & 0xffffffff

# Collect exactly 624 consecutive getrandbits(32) outputs
outputs = [get_next_uint32() for _ in range(624)]

# Reconstruct state
state = [untemper(y) for y in outputs]

# Inject into a new Random instance
r = random.Random()
r.setstate((3, tuple(state + [0]), None))

# Now predict future outputs
print(r.getrandbits(32))  # Will match the next output from the original RNG
```

**For `randrange(maxsize)` observations (Z3 approach):**

When you only observe partial outputs (e.g., `randrange(10**9)` values), each observation constrains 1-2 MT words. Use Z3 to recover the state:

```python
from z3 import *

solver = Solver()
mt_state = [BitVec(f"mt_{i}", 32) for i in range(624)]

# For each observation, add constraints:
# Python's randrange uses two 32-bit MT outputs per call when range >= 2^32
# For range < 2^32 uses one MT word, discards a few bits
for i, obs in enumerate(observations):
    # Relationship between obs and mt_state[i] depends on the range modulus
    word = mt_state[i]
    # Approximate: obs ≈ word >> (32 - bit_length(range_max))
    shift = 32 - (range_max - 1).bit_length()
    solver.add(URem(word >> shift, range_max) == obs)

if solver.check() == sat:
    m = solver.model()
    recovered = [int(str(m[mt_state[i]])) for i in range(624)]
```

**When to suspect:**
- Application uses Python's `random` module for session tokens, password resets, or secrets.
- You can observe a stream of `random.randint` or `random.random()` values.
- Token space analysis shows 624+ sequential values available.

---

### 1.7 MT19937 Float Recovery via GF(2) Matrix

**Pattern:** `random.random()` produces a 53-bit float. If only low bits are observed (e.g., `int(f * 256)` → 8 bits per call), the `not_random` library reconstructs the state from 3360+ observations.

**Why it works:**
Each float output is a linear function of internal MT state bits over GF(2). The precomputed magic matrix in `not_random` inverts this relationship.

```python
# Install: pip install not_random
# GitHub: https://github.com/fx5/not_random

from not_random import rebuild_random
import random

# Collect 3360+ 8-bit observations
# In the target application, we see md5(random.random()) but can measure
# probability distributions to recover bits
observations = []
for _ in range(3360):
    f = get_float_observation()       # e.g., int(random.random() * 256) from target
    observations.append(f)

# Reconstruct RNG state
rebuilt_rng = rebuild_random(observations)

# Predict subsequent outputs
next_val = rebuilt_rng.random()
print(f"Predicted next float: {next_val}")

# Common application: predict md5(random.random()) for password reset tokens
import hashlib
predicted_token = hashlib.md5(str(next_val).encode()).hexdigest()
print(f"Predicted token: {predicted_token}")
```

**When to suspect:**
- Application exposes floating-point values influenced by `random.random()`.
- Password reset tokens or session IDs are short MD5 digests of random floats.
- High-volume API endpoints return values that correlate statistically with a PRNG.

---

### 1.8 LCG Backward Stepping

**Pattern:** When you have the current LCG state but need to compute earlier states (e.g., to recover seed from a recent output), step backward using the modular inverse of the multiplier.

```python
def lcg_prev(state, a, c, m):
    """Compute the previous LCG state."""
    a_inv = pow(a, -1, m)         # Modular inverse of multiplier
    return (a_inv * (state - c)) % m

# Example: standard glibc LCG
a = 1103515245
c = 12345
m = 2**31

# Known current state
current = <observed_output>

# Step backward 10 states
for _ in range(10):
    current = lcg_prev(current, a, c, m)
    print(f"Earlier state: {current}")

# Java LCG (java.util.Random)
a_java = 25214903917
c_java = 11
m_java = 2**48
a_java_inv = pow(a_java, -1, m_java)

def java_prev(state):
    return (a_java_inv * (state - c_java)) % m_java

# Java's nextInt() exposes top 32 bits of 48-bit state
# Recover full state by brute-forcing lower 16 bits:
def recover_java_full_state(observed_int):
    upper = observed_int << 16
    for low in range(2**16):
        candidate = upper | low
        # Validate by checking next output matches
        next_state = (a_java * candidate + c_java) % m_java
        if (next_state >> 16) == next_observed_int:
            return candidate
    return None
```

**When to suspect:**
- LCG is identified (linear correlation between outputs).
- You need to recover seed or early states from a later-generation output.
- Java's `java.util.Random` is used with sequential `nextInt()` calls.

---

## Category 2: Oracle Attacks

### 2.1 RSA Padding Oracles (Bleichenbacher / Manger)

**Two attacks — pick by padding scheme:**
- **Bleichenbacher (1998)** → PKCS#1 v1.5 encryption padding. Oracle bit: does `m` begin with `0x00 0x02`? Cost ~10^6 queries per 1024-bit key. ROBOT (2017/2018) revived it against TLS.
- **Manger (2001)** → RSAES-OAEP (PKCS#1 v2.x). Oracle bit: is the OAEP-decoded MSB `0x00`? Cost ~1100 queries per 1024-bit key. Do not attack v1.5 with Manger.

**Preconditions (both):**
- You can submit ciphertexts to a decryption oracle.
- Oracle leaks validity via timing, error text, status code, TLS alert, or connection behavior.

**Why it works:**
Each oracle query on `(c * s^e) mod n` reveals one bit about the plaintext interval. Chosen multipliers halve the search space per round.

**Operational (high-level, Bleichenbacher):**

```python
import time
from pwntools import remote

def oracle_query(ct, conn):
    """Send ciphertext to oracle, return True if padding valid"""
    conn.send(ct)
    response = conn.recv()
    return "VALID" in response  # Adjust based on oracle behavior

def padding_oracle_attack(n, e, c, conn):
    # Phase 1: Find f1 such that (f1*c)^d has valid padding
    f = 2
    while not oracle_query(pow(f, e, n) * c % n, conn):
        f *= 2
    
    # Phase 2-3: Binary search to narrow plaintext range
    B = 2^(8 * (n.bit_length() // 8 - 1))  # One block below n
    f_min, f_max = f // 2, f
    
    plaintext_min, plaintext_max = 0, n
    
    for _ in range(100):  # Iterate until convergence
        f_test = (f_min + f_max) // 2
        ct_test = pow(f_test, e, n) * c % n
        
        if oracle_query(ct_test, conn):
            f_max = f_test
            plaintext_max = f_test * n // B
        else:
            f_min = f_test
            plaintext_min = f_test * n // B
    
    plaintext = (plaintext_min + plaintext_max) // 2
    return plaintext
```

**When to suspect:**
- Oracle is available (decryption service, web app with error messages).
- Timing varies between valid and invalid padding.
- Error messages distinguish padding errors.

**Tool**: Custom Python + pwntools for interaction.

---

### 2.2 Timing Oracle

**Preconditions:**
- Server implementation has timing differences based on computation path.
- Example: RSA decryption timing varies with ciphertext.
- Example: AES-CBC padding validation returns early on wrong first byte vs. correct.

**Why it works:**
Measure response times and infer which computation path the server took. Iteratively narrow down the secret.

**Operational:**

```python
import time

def measure_timing(ciphertext):
    """Send ciphertext, measure response time"""
    t0 = time.perf_counter()
    response = oracle(ciphertext)
    t1 = time.perf_counter()
    return t1 - t0, response

# Collect baseline timings
timings_fast = [measure_timing(invalid_ct) for _ in range(100)]
timings_slow = [measure_timing(valid_ct) for _ in range(100)]

# Compute threshold
threshold = (mean(timings_fast) + mean(timings_slow)) / 2

# Use timing to binary search
for bit_idx in range(key_bits):
    # Test key with bit_idx flipped
    key_test = flip_bit(key_guess, bit_idx)
    timing, _ = measure_timing(encrypt_with_key(key_test))
    
    if timing > threshold:
        key_guess[bit_idx] = 1
    else:
        key_guess[bit_idx] = 0
```

---

### 2.3 Error Message Oracle

**Preconditions:**
- Server returns different error messages or status codes for different failure modes.
- Failure modes reveal information (e.g., "invalid padding" vs. "decryption OK").

**Operational:**

```python
# Collect oracle responses and classify
responses = {}
for ct in test_cases:
    resp = oracle.query(ct)
    responses[ct] = resp

# Classify response types
for ct, resp in responses.items():
    if "invalid_signature" in resp:
        print(f"{ct}: Signature check failed")
    elif "decryption_ok" in resp:
        print(f"{ct}: Decryption succeeded")
    # ... etc

# Use classifications to build decision tree for plaintext recovery
```

---

## Category 3: Oracle and Service Interaction

### 3.1 Remote Oracle Harness (pwntools)

Build a harness to interact with remote service consistently.

```python
from pwn import *

# Connect to service
conn = remote('localhost', 12345)

# Send plaintext, receive ciphertext
def encrypt(plaintext):
    conn.sendline(f"ENCRYPT {plaintext.hex()}")
    return bytes.fromhex(conn.recvline().decode().strip())

# Send ciphertext, receive decryption result
def decrypt(ciphertext):
    conn.sendline(f"DECRYPT {ciphertext.hex()}")
    return conn.recvline().decode().strip()

# Send ciphertext, check padding validity
def oracle_check_padding(ciphertext):
    conn.sendline(f"ORACLE {ciphertext.hex()}")
    result = conn.recvline().decode().strip()
    return "VALID" in result
```

---

## Category 4: Protocol State Machine Interaction

Some protocols are not passive oracles — they actively send mathematical tasks that must be solved to advance to the next step. Each step builds on the previous one, and a protected secret may be released only after successfully completing all rounds.

### 4.1 Iterative Math Protocol (Kewiri Pattern)

**What this looks like:**
1. Server sends a math problem (e.g., "factor this N", "solve this DLP", "give me `k * P` for this EC point").
2. You compute the answer and send it back.
3. Server validates, advances to next step, sends a new problem.
4. After N rounds, server reveals a protected secret or capability.

**Preconditions:**
- You have network access to the server.
- Each round's problem type is predictable (factorization, DLP, EC arithmetic).
- Sage can solve each problem type programmatically.

**Operational skeleton:**

```python
from pwn import *
from sage.all import *
import re

conn = remote("host", port)

def solve_round(prompt_bytes):
    """Parse service prompt and dispatch to appropriate solver."""
    prompt = prompt_bytes.decode().strip()

    if "factor" in prompt.lower():
        # Factorization round
        n = int(re.search(r'\d+', prompt).group())
        factors = list(factor(n))
        # Format and return required factors
        return str(factors[0][0])  # Example: return largest prime factor

    elif "discrete_log" in prompt.lower() or "solve" in prompt.lower():
        # DLP round: g^x ≡ A (mod p)  or  in GF(p^k)
        # Extract g, A, p from service prompt
        # Example parsing (adapt to actual format):
        m = re.search(r'g=(\d+),\s*A=(\d+),\s*p=(\d+)', prompt)
        if m:
            g_val, A_val, p_val = int(m.group(1)), int(m.group(2)), int(m.group(3))
            F = GF(p_val)
            x = discrete_log(F(A_val), F(g_val))
            return str(x)

    elif "EC" in prompt or "point" in prompt.lower():
        # EC arithmetic round: given P, compute k*P
        # Extract curve params, k, P from service prompt
        p_val = <extract_p>
        a_val = <extract_a>
        b_val = <extract_b>
        k_val = <extract_k>
        Px, Py = <extract_Px>, <extract_Py>

        E = EllipticCurve(GF(p_val), [a_val, b_val])
        P = E(Px, Py)
        result = k_val * P
        return f"{int(result[0])},{int(result[1])}"

    else:
        raise ValueError(f"Unknown task type: {prompt}")


# Main loop
while True:
    line = conn.recvline()
    print(f"[RECV] {line}")

    # Detect termination condition
    if b"secret" in line.lower() or b"key" in line.lower() or b"well done" in line.lower():
        print(f"[DONE] Got final response: {line.decode()}")
        # Attempt to read any subsequent secret data
        try:
            extra = conn.recvall(timeout=3)
            print(f"[SECRET] {extra}")
        except EOFError:
            pass
        break

    if b"task" in line.lower() or b"solve" in line.lower() or any(kw in line.lower() for kw in [b"factor", b"log", b"point"]):
        answer = solve_round(line)
        print(f"[SEND] {answer}")
        conn.sendline(answer.encode())

conn.close()
```

### 4.2 State Accumulation Across Rounds

Some protocols accumulate values across rounds. The final round requires you to use a combination of values derived from all previous rounds.

```python
# State accumulation example
state = {}

while True:
    line = conn.recvline().decode().strip()

    # Save round outputs for use in later rounds
    if "your_factor" in line:
        state['p'] = extract_factor(line)
    elif "your_dlp" in line:
        state['x'] = extract_dlp_answer(line)
    elif "combine" in line:
        # Final round uses accumulated state
        final_answer = (state['p'] * state['x']) % <modulus>
        conn.sendline(str(final_answer).encode())
        break
```

### 4.3 Detecting Last Round

**Methods to detect when a protocol ends:**
- Server sends a different message format containing a key, secret, or hexadecimal blob.
- Server closes connection after last response.
- Response length is substantially longer than previous rounds.
- Task type changes to a "verification" step.

```python
# Defensive recv: handle both normal and final rounds
response = conn.recvline()
if b"=" in response and len(response) > 100:
    # Likely a hex-encoded secret
    secret = response.strip().decode()
    print(f"Final secret: {secret}")
    break
elif b"round" in response.lower():
    round_num = int(re.search(r'round\s*(\d+)', response.decode().lower()).group(1))
    print(f"Now in round {round_num}")
```

**When to suspect:**
- Problem description says "prove you can compute X" repeatedly.
- Server prints "stage 1 complete", "stage 2 complete", etc.
- Source code shows a `for i in range(rounds):` loop.

---

## Common Pitfalls

1. **Not measuring baseline timing**: Always collect reference timings (valid and invalid) before attempting timing-based attacks.

2. **Confusing PRNG output with internal state**: Many PRNGs truncate output. The output is not the full state.

3. **Assuming oracle is noiseless**: Real oracles have network latency, caching, and other noise. Collect many measurements.

4. **Off-by-one in state indexing**: When iterating states, confirm indexing matches between prediction and ground truth.

5. **Not handling connection errors in protocol loops**: Wrap recv/send in try/except when interacting with services that time out or close early.

---

## Decision Tree

```
START: You have ciphertext and oracle access.

Q1: Does oracle return timing differences?
  YES → Timing oracle attack (§2.2)
  NO → Continue

Q2: Does oracle return explicit error/status codes?
  YES → Error message oracle (§2.3)
  NO → Continue

Q3: Do you control plaintext (encryption oracle)?
  YES → Use encryption oracle to fingerprint ciphertext mode
  NO → Continue

Q4: PRNG-based attack
  Q4.1: Is PRNG output biased or small?
    YES → Entropy test and state recovery (§1.1–1.4)
    NO → PRNG likely strong; move to other attack vectors

Q5: Does the service send iterative math tasks?
  YES → Protocol state machine interaction (§4.1–4.3)
  NO → Static oracle; apply §1–3 techniques
```

