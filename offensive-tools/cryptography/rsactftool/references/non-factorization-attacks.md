# RsaCtfTool Reference — Non-Factorization RSA Attacks

Use this reference when plaintext/key recovery is possible **without directly factoring** `n`.

## 1) Wiener attack

### Signal
- Private exponent `d` too small.
- Indicators: evidence of short private exponent, fragile key schedule.

### Why it works
Continued fractions on $e/n$ can recover small `d` in vulnerable ranges.

### Run
```bash
RsaCtfTool --publickey key.pub --attack wiener --private
```

## 2) Boneh-Durfee

### Signal
- `d` small but outside classic Wiener bound.
- Lattice-based small-root setting applies.

### Run
```bash
RsaCtfTool --publickey key.pub --attack boneh_durfee --private
```

## 3) Hastad broadcast (small e)

### Signal
- Same plaintext encrypted to multiple recipients with low exponent (often `e=3`) and different moduli.

### Why it works
CRT reconstructs $m^e$; if $m^e < \prod n_i$, take exact integer root.

### Run
```bash
RsaCtfTool --publickey "keys/*.pub" --attack hastads --private
```

## 4) Same modulus `n`, multiple exponents

### Signal
- Reused `n` across instances with co-prime exponents and related ciphertexts.

### Why it works
Bézout relation on exponents enables plaintext recovery.

### Run
```bash
RsaCtfTool --publickey "keys/*.pub" --attack same_n_huge_e --private
```

## 5) Partial key exposure (partial q / partial d)

### Signal
- Leakage: bits/chunks of `q` or `d` are exposed.
- Text references truncated/obfuscated key pieces.

### Why it works
Small-root/lattice recovery can reconstruct missing parts.

### Run
```bash
RsaCtfTool --publickey key.pub --attack partial_q --private
RsaCtfTool --publickey key.pub --attack partial_d --private
```

## 6) Small CRT exponent / CRT misuse

### Signal
- CRT parameters are weak/leaked/misconfigured.

### Run
```bash
RsaCtfTool --publickey key.pub --attack small_crt_exp --private
```

## 7) Generic lattice-assisted recovery

### Signal
- Polynomial constraints, leaked MSBs/LSBs, or arithmetic side-info.

### Notes
SageMath availability greatly improves lattice-heavy attack coverage.

## Workflow tip

Start with lightweight checks (`wiener`, `hastads`, `same_n...`) before expensive lattice paths.

## Failure triage

If attack fails:
1. Re-check assumptions (same plaintext? same modulus? leak truly consistent?).
2. Ensure all required public keys/ciphertexts are supplied.
3. Move to factorization reference when non-factorization assumptions are weak.
