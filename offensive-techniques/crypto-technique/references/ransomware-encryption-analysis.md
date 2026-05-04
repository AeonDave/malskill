# Ransomware encryption analysis

## Purpose

Determine how a ransomware sample encrypts data, whether key recovery is feasible, and what evidence supports or rules out decryption without paying an attacker.

## Triage workflow

1. Preserve sample, encrypted files, ransom notes, logs, and memory if available.
2. Identify crypto APIs, linked libraries, and embedded constants.
3. Locate file traversal and encryption routines.
4. Determine key hierarchy: per-file, per-host, campaign public key, hybrid scheme.
5. Inspect randomness source and key wrapping.
6. Test implementation weaknesses on copied evidence.
7. Produce decryption feasibility assessment with confidence.

## Key hierarchy patterns

| Pattern | Signals | Recovery angle |
|---|---|---|
| Symmetric-only static key | Same key or IV across files | Extract key from binary/config/memory |
| Per-file symmetric key + public-key wrap | RSA/ECC public key embedded; encrypted key blob per file | Recover private key only if implementation/keygen is weak |
| Per-host symmetric key | Host identifier used in KDF | Search memory, registry, notes, config, network beacons |
| Stream cipher with nonce reuse | Same keystream prefix across files | Known-plaintext or XOR recovery |
| Broken KDF | Low iteration count, predictable salt/seed | Offline cracking or seed recovery |

## Static analysis checklist

- Imports: `CryptAcquireContext`, `BCrypt*`, `CryptGenRandom`, OpenSSL EVP, libsodium, Crypto++.
- Constants: AES S-boxes, ChaCha sigma, RSA DER blobs, curve OIDs.
- File markers: custom extension, footer/header key blobs, magic bytes.
- Threading: worker pools encrypting file chunks.
- Exclusions: paths, extensions, processes, locale checks.
- Network: key exchange before encryption, fallback offline public key.

## Dynamic analysis checklist

In an isolated VM:

1. Snapshot before execution.
2. Feed known test files with known plaintext prefixes.
3. Monitor file write order and metadata changes.
4. Break on crypto API calls to capture keys, IVs, nonces, and plaintext buffers.
5. Dump process memory before exit and after encryption begins.
6. Compare multiple encrypted outputs for nonce/IV reuse.

## Encrypted file analysis

For each encrypted file sample:

- Original size vs encrypted size.
- Header/footer structure.
- Entropy before/after.
- Repeated blocks or repeated keystream indicators.
- Per-file metadata: filename, extension, host ID, timestamp.
- Wrapped key or nonce location and length.

## Feasibility assessment

| Result | Meaning |
|---|---|
| Feasible | Key/seed/nonce weakness demonstrated and decryptor can be built |
| Partially feasible | Only some files/classes recoverable due to known plaintext or memory capture |
| Not feasible from current evidence | Strong crypto appears correctly used and private key is absent |
| Inconclusive | Missing memory, sample, original plaintext, or key-exchange evidence |

## Evidence requirements

- Exact algorithm and mode identification.
- Key/IV/nonce source and lifecycle.
- Reproduction on copied sample files.
- Decryptor validation on at least two files when claiming recovery.
- Clear explanation of limits and required additional evidence.

## Common pitfalls

- Assuming public-key encryption covers whole files; most families use hybrid crypto.
- Missing per-file key blobs stored at EOF.
- Treating high entropy as proof of strong encryption.
- Running sample without collecting memory during key generation.
- Publishing a decryptor claim without validating file integrity after decryption.
