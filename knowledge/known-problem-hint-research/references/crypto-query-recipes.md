# Crypto Hint Research Recipes

Use these only after local analysis has classified the cryptographic primitive and collected concrete evidence. Each query should include one specific anomaly plus one source-type term.

## Query construction pattern

Build each query from:

```text
{primitive} {specific anomaly} {attack family or suspected theorem} {source type}
```

Source-type terms: `paper`, `eprint`, `implementation`, `writeup`, `blog`, `discussion`, `github`, `sage`, `proof`, `bounds`.

Prefer 3 to 5 narrow queries. If all fail, refine the fingerprint rather than widening to the whole category.

## Source filters

Useful focused searches:

```text
site:eprint.iacr.org {attack phrase} {parameter clue}
site:arxiv.org {primitive} {attack phrase}
site:crypto.stackexchange.com {parameter relation} {primitive}
site:github.com {attack name} sage implementation
site:github.io {attack name} writeup {primitive}
```

For Jina Search, encode the query and optionally use supported site parameters when useful:

```text
https://s.jina.ai/{url-encoded-query}
https://s.jina.ai/{url-encoded-query}?site=eprint.iacr.org&site=crypto.stackexchange.com
```

## RSA fingerprints

Turn local evidence into attack-shaped searches:

| Local clue | Query seed |
|---|---|
| small exponent, no padding, small message | `RSA small e no padding integer root implementation` |
| same modulus, different exponents | `RSA common modulus attack writeup implementation` |
| same message to multiple moduli | `Hastad broadcast attack bounds eprint` |
| partial bits of p, q, or d | `RSA partial key exposure Coppersmith Sage implementation` |
| close primes or near square n | `RSA close primes Fermat factorization discussion` |
| unusually small private exponent | `Wiener Boneh Durfee RSA small d bounds` |
| non-coprime moduli across keys | `batch gcd RSA shared prime implementation` |

## ECC, DSA, and finite-field fingerprints

| Local clue | Query seed |
|---|---|
| repeated ECDSA/DSA nonce | `ECDSA nonce reuse private key recovery implementation` |
| biased or partial nonce bits | `hidden number problem ECDSA partial nonce lattice` |
| anomalous curve order equals field prime | `Smart attack anomalous elliptic curve Sage` |
| singular curve discriminant zero | `singular elliptic curve discrete log reduction writeup` |
| smooth group order | `Pohlig Hellman elliptic curve smooth order implementation` |
| invalid curve or twist behavior | `invalid curve attack ECC implementation discussion` |

## Lattice and Coppersmith fingerprints

| Local clue | Query seed |
|---|---|
| small unknown root modulo n | `Coppersmith small roots Sage bounds univariate` |
| two related messages or affine relation | `Franklin Reiter related message attack implementation` |
| stereotyped plaintext with unknown suffix | `RSA stereotyped message Coppersmith implementation` |
| approximate common divisor | `approximate common divisor problem lattice implementation` |
| knapsack/subset sum shape | `low density knapsack LLL attack writeup` |

## PRNG fingerprints

| Local clue | Query seed |
|---|---|
| MT19937 outputs | `MT19937 untemper state recovery implementation` |
| truncated LCG outputs | `truncated LCG state recovery lattice implementation` |
| unknown LCG modulus | `recover LCG modulus from outputs discussion` |
| xorshift outputs | `xorshift state recovery symbolic implementation` |
| time/PID seed suspicion | `predictable seed crypto random attack writeup` |

## Symmetric and oracle fingerprints

| Local clue | Query seed |
|---|---|
| CBC valid/invalid padding signal | `CBC padding oracle attack implementation timing noise` |
| PKCS#1 v1.5 validity oracle | `Bleichenbacher Manger RSA padding oracle implementation` |
| GCM nonce reuse | `AES GCM nonce reuse authentication key recovery implementation` |
| CTR nonce reuse | `CTR nonce reuse many time pad recovery writeup` |
| ECB chosen plaintext | `ECB byte at a time attack implementation` |

## Stop rules

Stop searching when one of these happens:

- a source gives the exact missing construction and a local test can be run
- two independent sources agree on the same attack condition
- every high-signal hit fails the local applicability check
- the search drifts into broad category learning

The output should be a hint packet plus next local test, not a survey.
