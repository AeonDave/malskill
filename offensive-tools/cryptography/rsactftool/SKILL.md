---
name: rsactftool
description: "Auth/lab ref: RSA testing automation tool for weak public keys. For targeting RSA key recovery or plaintext recovery from public data (n, e, ciphertext, partial leaks)."
license: MIT
compatibility: "Python 3.9+; Linux/macOS/WSL recommended."
metadata:
  author: AeonDave
  version: "1.0"
---

# RsaCtfTool

Multi-attack RSA solver for weak RSA scenarios. Best used as a **triage engine**: feed known key material, run constrained attacks first, escalate only when signal supports it.

## Core workflow

1. Normalize input (`.pem`, OpenSSH pubkey, or raw `n/e`).
2. Inspect key parameters and weakness indicators.
3. Select attack families by signal (not brute-force all blindly).
4. Recover private key and/or decrypt ciphertext.
5. Verify output format and cryptographic consistency.

## Quick commands

```bash
# Recover private key (auto attack selection)
RsaCtfTool --publickey key.pub --private

# Force a specific attack
RsaCtfTool --publickey key.pub --attack wiener --private

# Decrypt a ciphertext file once key is recoverable
RsaCtfTool --publickey key.pub --decryptfile ciphertext.bin

# Build pubkey from n/e (for problem specifications that give integers only)
RsaCtfTool --createpub -n <n> -e <e>

# Dump key parameters for triage
RsaCtfTool --dumpkey --ext --key key.pub
```

## Attack selection heuristics

- Start with **non-factorization** attacks when evidence indicates weak `d`, broadcast, shared `n`, or partial leakage.
- Prioritize **factorization** when `n` structure suggests close primes, smoothness, reused factors, or vulnerable keygen.
- Use **scenario-specific** methods when custom prime construction or non-standard modulus generation is suspected.

## Practical attack loop

```bash
# 1) Parse and inspect
RsaCtfTool --dumpkey --ext --key key.pub

# 2) Run fast specific checks first
RsaCtfTool --publickey key.pub --attack wiener --private
RsaCtfTool --publickey key.pub --attack hastads --private
RsaCtfTool --publickey key.pub --attack common_factors --private

# 3) Escalate to broader runs
RsaCtfTool --publickey key.pub --private

# 4) If key recovered, decrypt material
RsaCtfTool --publickey key.pub --decryptfile ct.bin
```

## Output validation checklist

- Decrypted bytes decode cleanly (UTF-8/ASCII) or have expected binary structure.
- PKCS#1 padding assumptions are consistent with implementation.
- If multiple candidate plaintexts appear, test all against oracle verification or remote service.
- Never trust a single lucky decode without re-encryption consistency checks.

## Boundaries

- Tool scope is RSA semiprime attacks on weak public keys (standard asymmetric key scenarios).
- Hash cracking (MD5/SHA/bcrypt) is intentionally out of scope here (covered by `hashcat` skills).

## Resources

- `references/factorization-attacks.md` — RSA attacks based on factoring `n` (Fermat, Pollard variants, ECM, QS, etc.).
- `references/non-factorization-attacks.md` — RSA attacks without directly factoring `n` (Wiener, Hastad, Boneh-Durfee, partial leaks, lattice).
- `references/challenge-specific-attacks.md` — scenario-specific attacks for non-standard RSA key patterns and triage patterns.
