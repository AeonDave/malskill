# Diffie-Hellman weak parameter technique

## Purpose

Diagnose exploitable weaknesses in finite-field Diffie-Hellman deployments, captured handshakes, and custom protocols.

## Inputs

- Prime modulus `p`, generator `g`, public values `A = g^a mod p`, `B = g^b mod p`.
- Any reuse evidence for `A`, `B`, group parameters, or server static keys.
- Protocol transcript and negotiated ciphersuite if available.

## Weakness decision tree

1. Is `p` too small for the environment? Try discrete log with Sage or specialized tools.
2. Does `p-1` factor smoothly? Use Pohlig-Hellman.
3. Is `g` a generator of a small subgroup? Test subgroup confinement.
4. Is a static public value reused across sessions? Consider precomputation and passive decryption if the exponent is recovered.
5. Are peer public values validated? Try invalid or small-subgroup public keys only in authorized test environments.
6. Are common primes reused at scale? Check for Logjam-style precomputation risk.

## Parameter checks

```python
from sage.all import *

p = Integer(<prime>)
g = Integer(<generator>)
print(factor(p - 1))

# Generator/subgroup sanity
for q, _ in factor(p - 1):
    if pow(g, (p - 1)//q, p) == 1:
        print(f"g is confined away from factor {q}")
```

## Pohlig-Hellman path

**Preconditions:** `p-1` has small factors and the target public value is in the corresponding group.

```python
F = GF(p)
gF = F(g)
AF = F(A)
x = discrete_log(AF, gF)
assert pow(g, int(x), p) == A
```

If only part of the group is smooth, recover residues modulo smooth factors and combine with CRT. The remaining subgroup may still be too large.

## Small-subgroup confinement

**Risk:** a peer accepts attacker-supplied DH public values without validating group membership. The attacker can force the shared secret into a small set and recover bits of the private exponent through repeated sessions.

Validation checklist:

- Reject public values `0`, `1`, `p-1`, and values outside `[2, p-2]`.
- Validate subgroup membership when using safe-prime subgroups.
- Prefer standardized groups and ephemeral keys.

## Static DH and reuse

Indicators:

- Same server public value across many sessions.
- Long-lived key pair in configuration.
- Captured handshakes with identical `A` or `B`.

Impact:

- If the static exponent is recovered once, historical sessions using the same value may be decryptable when transcript data is available.

## Output validation

- Recomputed public value matches the transcript.
- Derived shared secret matches protocol key derivation output where test vectors exist.
- Decrypted sample traffic has valid protocol structure.

## Common pitfalls

- Treating a safe prime as sufficient while accepting invalid peer public keys.
- Ignoring group negotiation downgrade paths.
- Attempting generic discrete log before factoring `p-1`.
- Failing to distinguish finite-field DH from ECDH.
