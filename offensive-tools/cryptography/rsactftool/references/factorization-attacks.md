# RsaCtfTool Reference — Factorization Attacks

Use this reference when the core weakness is in how `n = p*q` was generated.

## 1) Fermat

### Signal
- `p` and `q` are close (`|p-q|` small).
- Indicator: prime structure appears designed (near-squares / consecutive-like primes).

### Why it works
Fermat searches for $n = a^2 - b^2 = (a-b)(a+b)$ efficiently when factors are near each other.

### Typical run
```bash
RsaCtfTool --publickey key.pub --attack fermat --private
```

## 2) Pollard Rho

### Signal
- Generic moderate-size factors; no stronger clue available.

### Why it works
Pseudo-random cycle detection can reveal non-trivial divisors faster than naive trial division.

### Typical run
```bash
RsaCtfTool --publickey key.pub --attack pollard_rho --private
```

## 3) Pollard p-1 / Williams p+1

### Signal
- `p-1` or `p+1` likely smooth (small factors).
- Indicator: non-standard prime generation pattern.

### Typical run
```bash
RsaCtfTool --publickey key.pub --attack pollard_p_1 --private
RsaCtfTool --publickey key.pub --attack williams_pp1 --private
```

## 4) ECM (Elliptic Curve Method)

### Signal
- Medium-size factor with smooth subgroup order.
- Other fast methods fail but `n` not too hard.

### Typical run
```bash
RsaCtfTool --publickey key.pub --ecmdigits 25 --private
```

## 5) Quadratic sieve / SQUFOF / Dixon

### Signal
- General integer factorization stage when simpler methods fail.

### Typical run
Use automatic mode and let RsaCtfTool escalate:
```bash
RsaCtfTool --publickey key.pub --private
```

## 6) ROCA / known vulnerable keygen

### Signal
- Known key-generation fingerprint/vulnerability class.

### Typical run
```bash
RsaCtfTool --isroca --publickey key.pub
```

## 7) Common-factor / batch GCD

### Signal
- Reused factors across multiple RSA keys.
- Reused prime across keys.

### Typical run
```bash
RsaCtfTool --publickey "keys/*.pub" --attack common_factors --private
```

## 8) Factordb integration

### Signal
- Public key is already known or partially factored.

### Typical run
```bash
RsaCtfTool --publickey key.pub --attack factordb --private
```

## Decision shortcut

- Close primes hint → `fermat`
- Many keys / reuse suspicion → `common_factors`
- Smoothness hint → `pollard_p_1` / `williams_pp1` / `ecm`
- No clue → auto run (`--private`) then inspect logs

## Validation

After a hit, always verify:
1. Derived `d` decrypts to structured plaintext.
2. Re-encryption matches original ciphertext behavior.
3. If oracle verification is required, submit candidate and verify response.
