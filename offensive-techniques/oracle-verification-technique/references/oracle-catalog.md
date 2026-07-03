# Oracle Catalog

Per-class machine oracles. Each entry: **positive signal** (machine-decidable, from the target's real response), **recipe** (what to re-run N/N), **control** (a safe surface where the oracle must fail). A class with no deterministic oracle can never be `VERIFIED` — report it `candidate — no oracle` and verify by hand.

## Contents
- [Design rules for an oracle](#design-rules-for-an-oracle)
- [Injection / SQLi](#injection--sqli)
- [XSS (reflected / stored)](#xss-reflected--stored)
- [SSRF (in-band / out-of-band)](#ssrf-in-band--out-of-band)
- [XXE](#xxe)
- [SSTI](#ssti)
- [IDOR / BOLA](#idor--bola)
- [Auth / JWT bypass](#auth--jwt-bypass)
- [Open redirect](#open-redirect)
- [Path traversal](#path-traversal)
- [Mass assignment](#mass-assignment)
- [Host-header / trusted-header](#host-header--trusted-header)

## Design rules for an oracle

- **Decidable from the response, not the request.** The signal must come from what the target *does*, never from "the payload looks malicious."
- **Discriminating.** Use a value the app cannot produce by accident: a random nonce, an arithmetic result, a unique OOB token. Avoid signals that also appear on benign traffic.
- **Control-paired.** For every positive there must be a negative surface (patched route / benign value / control payload) where the same oracle fails. No control = no verdict.
- **Fresh state per run.** New session/token/nonce each of the N runs. A pass that needs a stale cached artifact is not proof.

## Injection / SQLi

- **Boolean/blind**: send a TRUE condition and a FALSE condition of the same length; positive = responses differ deterministically across N pairs (TRUE-page vs FALSE-page). Control: inject into a param proven inert, or use a tautology that changes nothing → responses must **not** diff.
- **Error-based**: signal = DB-specific error token appearing only for the malformed payload. Control: well-formed value → no error token.
- **UNION/read**: signal = a random marker string retrieved via the injection (e.g. `SELECT '<nonce>'`) echoed back. Control: benign value → nonce absent.
- Impact gate: reading a real secret (creds, other users' rows) upgrades from medium to high/critical.

## XSS (reflected / stored)

- Positive = execution, not reflection. Use a unique callback (DOM sink writing a nonce to a collector, or a headless browser that fires on the injected marker). Signal = the nonce arrives / JS executes.
- Reflected control: same nonce sent to a properly-encoded sink → must not execute.
- Stored: inject as user A, trigger render as user B; execution in B's context proves stored + cross-user.

## SSRF (in-band / out-of-band)

- **OOB**: unique per-run subdomain/token on a collector (DNS+HTTP). Positive = the exact token is seen at the collector. Control: a token never sent → never seen.
- **In-band**: fetch an internal resource whose body the app returns; signal = internal-only content (e.g. metadata endpoint field) in the response. Control: a public URL → no internal marker.
- Reachability only (bare callback) = **medium** until an impact oracle reads something sensitive.

## XXE

- Positive = external entity content in the response (e.g. a line of `/etc/passwd` matching `root:.*:0:0:`), or a unique OOB token via parameter entity. Control: same request without the entity → marker absent.

## SSTI

- Positive = server-side arithmetic on a unique pair, e.g. inject `{{ 7*<r1> }}` and read back `7*r1`; require a second random pair to rule out coincidence. Control: the literal in a non-template context → returned verbatim, unevaluated.

## IDOR / BOLA

- Positive = principal A retrieves principal B's object and the response contains B-owned data A never created (match on a B-only field/nonce planted as B). Control: A requests A's own object → allowed (baseline), and a random non-existent id → 404/deny, proving the access check is object-scoped, not blanket-open.
- Sequential IDOR: prove ≥2 distinct victim ids, not one.

## Auth / JWT bypass

- **`alg:none` / unsigned**: forge a token for a privileged claim, hit a protected endpoint; positive = protected data returned. Control: the same forged token with a wrong signature/claim → rejected (401/403), proving the endpoint does gate normally.
- **Login bypass**: injection/payload yields an authenticated session (valid post-auth cookie/token that fetches user-only data). Control: benign wrong creds → unauthenticated.

## Open redirect

- Positive = a 3xx `Location` (or JS/meta redirect) pointing to an attacker-controlled external origin from a controllable parameter. Control: a benign relative value → stays on-origin.

## Path traversal

- Positive = contents of a file outside web root matching a stable signature (`root:.*:0:0:` for `/etc/passwd`) via `../` sequences. Control: the canonical in-root path → normal file, no traversal marker.

## Mass assignment

- Positive = setting a non-form field (e.g. `role=admin`, `isAdmin=true`) persists and a follow-up read shows the elevated attribute for that account. Control: the same field on an endpoint that whitelists inputs → attribute unchanged.

## Host-header / trusted-header

- Positive = the app trusts an attacker-supplied `Host`/`X-Forwarded-*`/trusted header, evidenced by a poisoned artifact reflecting the injected value (password-reset link, cache key, or an auth bypass via a spoofed internal header). Control: the header absent/benign → no poisoned artifact.
