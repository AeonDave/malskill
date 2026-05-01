# RsaCtfTool Reference — Scenario-Specific and Non-Standard Attack Typologies

These methods target non-standard RSA key patterns and custom modulus construction rather than textbook production failures.

## 1) Novelty / gimmick primes

### Signal
- Prime generation includes memes, fixed prefixes/suffixes, repeated decimal motifs, deterministic templates.

### Approach
- Extract constraints from RSA key specifications and source material.
- Use RsaCtfTool scenario-aware attack modes first, then custom scripts if needed.

## 2) Prime reuse patterns from prior events

### Signal
- Input intentionally imitates known weak constructions from earlier events.

### Approach
- Test scenario-specific attacks in RsaCtfTool.
- Cross-check with public writeups for similar constructions.

## 3) Non-RSA disguised math (`b^x` forms, non-standard algebra)

### Signal
- Input claims RSA but includes equations not matching standard RSA flows.

### Approach
- Use dump/analysis mode to confirm whether modulus/exponent semantics are actually RSA.
- If not, pivot to SageMath symbolic/number-theory scripts.

## 4) External solver bridges (Z3 / WolframAlpha style hints)

### Signal
- Constraints resemble SAT/SMT or symbolic systems rather than pure factorization.

### Approach
- Use RsaCtfTool where compatible; otherwise solve constraints externally then feed recovered values back.

## 5) Oracle-backed RSA verification

### Signal
- Remote service returns transformed decryptions, parity bits, validity flags, etc.

### Approach
- Use `pwntools` for tube/protocol interaction.
- Use RsaCtfTool for key-side hypotheses and candidate validation.
- Keep a reproducible loop: collect samples -> hypothesize -> test -> submit.

## Integration pattern with SageMath

When non-standard algebraic structures appear (e.g., polynomial constraints, lattice setup, finite-field lifting):
1. Prototype with Sage (`GF`, polynomial rings, `LLL`, roots).
2. Recover missing RSA values.
3. Return to RsaCtfTool for final key recovery/decryption checks.

## Minimum artifact checklist

Store with your solve script:
- exact public parameters (`n`, `e`, key files)
- ciphertext samples (raw and decoded form)
- assumptions for selected attack type
- verification output proving recovered plaintext is correct
