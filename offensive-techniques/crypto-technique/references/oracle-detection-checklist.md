# Oracle detection checklist

Use this when a service response may leak cryptographic validity through status, error text, timing, retry behavior, or side effects.

## Objective

Confirm that an oracle exists before committing to a padding, timing, signature, or format-validity attack. A real oracle gives a stable, attacker-controlled signal that separates at least two cryptographic states better than baseline noise.

## 1) Inventory observable channels

Record every response dimension for valid, invalid, and malformed inputs:

- HTTP status, redirect target, response length, body phrase, JSON error code.
- Connection behavior: close/reset/timeout, retry, throttling, rate-limit bucket.
- Timing: median, p95, jitter, cold-start vs warmed path.
- Side effect: account lock, session invalidation, audit event, cache entry, token rotation.
- Protocol-level signal: TLS alert, padding alert, MAC failure, ASN.1 parse error, signature error.

Do not trust a single visible error string. Many services normalize the body but still leak through timing or connection behavior.

## 2) Build controls before attack logic

For each candidate oracle, test at least three classes:

| Class | Purpose |
|---|---|
| Known-valid sample | Baseline success path |
| Known-invalid same length | Separates crypto failure from parser/routing failure |
| Random malformed input | Detects generic validation and WAF/error handling |

Keep request size, headers, transport, and session state constant. Change one cryptographic field at a time.

## 3) Timing signal gate

Timing oracles require statistical confidence, not vibes.

- Warm the service first; discard first-run cold start samples.
- Run repeated paired trials: A/B/A/B ordering reduces drift.
- Compare medians and p95, not one fastest/slowest request.
- Treat network jitter as adversarial. If delta is smaller than baseline jitter, do not attack timing yet.
- Prefer local/lab reproduction when possible; remote internet timing needs many more samples.

Minimum gate: the valid/invalid distributions should remain separable after retries, rate limits, and randomized order.

## 4) Oracle class decision

| Signal | Likely class | Next reference |
|---|---|---|
| Padding error differs from MAC/decrypt error | CBC padding oracle, PKCS#1 v1.5 oracle | `symmetric-cipher-technique.md`, `rsa-technique.md` |
| Same body, stable timing delta during compare | Timing oracle, early-exit compare | `prng-oracle-technique.md` |
| Signature parse errors differ from verification failures | Signature verification oracle | `ecc-technique.md`, `rsa-technique.md` |
| Distinct JWT/JWE/ASN.1 errors | Format-validity oracle | `problem-diagnosis.md` |
| Nonce/session reuse after invalid request | State oracle | `symmetric-cipher-technique.md` |

## 5) Exploit readiness gate

Proceed only when:

- Input field controlled by attacker is confirmed to reach crypto validation.
- Oracle signal survives replay from a clean session.
- False positives from routing, auth, cache, WAF, and rate limiting are eliminated.
- You can automate requests without changing session state in a way that destroys the oracle.
- Success condition is defined: plaintext byte, key bit, valid signature, token forgery, or decryptable file.

If any gate fails, return to problem diagnosis instead of brute-forcing against noise.

## 6) Common failure modes

- Treating parser errors as crypto oracle signal.
- Measuring over a shared session where previous failures change state.
- Ignoring compression, CDN, or WAF behavior that changes response length/timing.
- Running an oracle attack before proving input length, padding layout, and block boundary.
- Overfitting to one payload that triggered an unrelated application error.
