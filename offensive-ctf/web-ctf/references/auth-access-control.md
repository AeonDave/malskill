# Auth and Access Control

Use this reference for authentication flaws, access-control bypasses, token abuse, and identity-flow attacks.

## Table of Contents
- [Fast triage](#fast-triage)
- [Sessions and cookies](#sessions-and-cookies)
- [Access-control failures](#access-control-failures)
- [JWT and JWE](#jwt-and-jwe)
- [OAuth, OIDC, and SAML](#oauth-oidc-and-saml)
- [Infrastructure and identity-admin pivots](#infrastructure-and-identity-admin-pivots)
- [Exotic auth edge cases](#exotic-auth-edge-cases)
- [Weak-signature / MAC / token oracles](#weak-signature--mac--token-oracles)
- [Method / verb / fingerprint bypass](#method--verb--fingerprint-bypass)
- [Open redirect, subdomain takeover, info-disclosure quick pivots](#open-redirect-subdomain-takeover-info-disclosure-quick-pivots)

## Fast triage

Check auth in this order:
1. session source: cookie, bearer token, magic link, API key, signed URL, OAuth callback
2. trust boundary: browser-only gate, backend gate, proxy gate, IdP gate, admin API
3. identity material: usernames, emails, user IDs, tenant IDs, roles, KIDs, redirect URIs
4. state mutations: login, password reset, invite, token refresh, role change, account linking
5. replay surface: old tokens, stale cookies, unsigned or partially checked signatures

## Sessions and cookies

High-yield checks:
- role or admin flags stored directly in cookies
- public endpoints that seed privileged cookies
- host-header dependent session routing
- hidden admin or internal routes reachable once a cookie is replayed
- balance or privilege fields trusted from a client-stored token

Useful probes:

```bash
curl -i -c jar.txt http://target/admin/login
curl -b jar.txt http://target/admin
curl -H "Cookie: role=admin" http://target/
```

Common web CTF failures:
- static admin session values
- cookie integrity based on weak or truncated checks
- custom MACs that are forgeable or only partially validated
- access decisions made in frontend JavaScript only

## Access-control failures

Focus on mismatches between identity check and object/action execution.

Patterns:
- unauthenticated WIP or debug endpoints
- IDOR/BOLA on numeric IDs, UUIDs, slugs, exports, or job-result paths
- route mismatches in Express / proxy / middleware normalization
- method-based bypasses like `TRACE`, verb overrides, or alternate content types
- browser-gated admin actions that succeed through direct API calls
- AI/chatbot or workflow endpoints with policy enforced only in UI copy

Quick matrix:
- Subject × Object × Action
- anonymous vs low-priv vs target-user vs admin
- REST vs GraphQL vs WebSocket vs background job finalizer

## JWT and JWE

Test token handling before touching claims.

JWT checklist:
- `alg: none`
- RS256 -> HS256 confusion
- weak HMAC secret brute-force
- decode-without-verify logic
- embedded `jwk` header
- `jku` fetch to attacker JWKS
- `kid` path traversal or SQL injection
- replay of stale privilege-bearing claims

JWE checklist:
- public key exposed via JWKS or app endpoint
- server trusts any token it can decrypt
- no secondary signature or server-side claim binding

Minimal tooling:

```bash
flask-unsign -decode -cookie "eyJ..."
hashcat -m 16500 jwt.txt wordlist.txt
```

## OAuth, OIDC, and SAML

Fast route:
1. capture full authorize request
2. inspect `redirect_uri`, `state`, `nonce`, `aud`, `azp`, and callback validation
3. test open-redirect and path-normalization bypasses on callback domain
4. check if account-linking can be CSRFed or rebound
5. for SAML, preserve `RelayState` and inspect signature coverage and digest validation

High-yield patterns:
- redirect URI confusion
- missing or weak `state`
- unsigned or weakly validated ID tokens
- account-linking CSRF
- SAML response replay or digest smuggling
- email subaddressing or normalization mismatches during identity linking
- authorization-code dirty-dancing: prefix/`HasPrefix` path validation accepts `…/callback/../../page`, landing the victim `code` on a **same-origin** page; leak it with a client-side primitive (see `browser-attacks.md`), then replay
- token endpoint not binding `redirect_uri` (omitted check, or an ORM `WHERE` with more args than placeholders): a code minted for one `redirect_uri` exchanges under another → replay a stolen code through the confidential client's own callback to get a victim session

## Infrastructure and identity-admin pivots

If you land project-admin or CI/CD access, auth often collapses through adjacent systems.

Targets:
- Git history for deleted secrets
- CI/CD variables and deployment secrets
- identity-provider admin APIs
- Guacamole and similar connection brokers
- login-page poisoning for credential harvest
- build systems such as TeamCity for code exec under privileged agents

Operator rule:
- once an admin API token exists, switch from login bypass mindset to identity takeover mindset

## Exotic auth edge cases

Rare but real CTF patterns worth remembering:
- `std::unordered_set` bucket-collision auth bypass
- Unicode homograph username collisions after normalization
- SRP with `A = 0` or `A = N`
- AQL / NoSQL merge-based privilege escalation
- affine-cipher or PRNG-based OTP recovery
- base64 decode leniency plus parser override bugs
- truthy hash checks where the comparison is missing entirely

**Guacamole parameter extraction**: connection parameters (`hostname`, `password`, `username`) are round-tripped through the client in some deployments — inspect the WebSocket for cleartext credentials.

**TeamCity REST API RCE**: authenticated write access to a build config → configure a build step that runs an arbitrary script under the agent user — same primitive as Jenkins job creation.

**Login-page poisoning**: if you get file write on the web root, replace the login template to log submitted credentials to a file/webhook.

**SAML SSO automation edge**: automated federation tools that accept an `IdP metadata URL` from user input let you swap in an attacker IdP if the callback signature check is not bound to the *originally-configured* certificate.

**Identity-provider MFA bypass** via `not_configured_action: skip` (some IdPs default to skipping MFA when the user has none enrolled). Enumerate users whose MFA is not yet configured, then log in with just the password.

## Weak-signature / MAC / token oracles

**Custom linear MAC forgery**: XOR-based custom signing (`sig = k1 ^ H(msg) ^ k2` or per-block XOR with secret blocks) is linear — recover the fixed secret from *any* known (msg, sig) pair, then forge for arbitrary messages. Any custom "sign(k, m)" that boils down to XOR / addition mod 2^n is forgeable.

**Base64 decode leniency + parameter override**: `base64.b64decode()` (Python) silently ignores non-base64 chars. Append `&price=0` after a signed token in the URL — the base64 decoder strips it before verifying the signature, but the URL parameter parser reads it (last-value-wins) after verification. Sig check passes; server sees `price=0`.

**Truncated / prefix-only hash compare**: `if hash.startswith(user_input)` treats a valid 1-char prefix as valid. Send `'0'` — many hex hashes start with `0` at ~1/16 probability. Iterate.

**Affine-cipher OTP**: `otp = (a * counter + b) mod 26` (or similar constants) has only 312 possible `(a, b)` pairs when the space is 26; brute-force all pairs against 2–3 observed (counter, otp) samples in milliseconds.

**TOTP with `srand(time())` seed**: server generates "random" secrets seeded from wall-clock time — sync your local clock to the server's `Date:` header, replay `srand`+`rand` with the same libc, predict every code for the current window.

## Method / verb / fingerprint bypass

**Verb / method bypass**: endpoints that return 403 on `GET`/`POST` sometimes accept `TRACE`, `PUT`, `PATCH`, `DELETE`, or method-override headers (`X-HTTP-Method-Override: GET`). Always sweep `curl -X` with the full verb set on any 403 you care about, plus content-type flips (`application/json` vs `text/plain`).

**JA4 / JA4H TLS fingerprinting**: servers that gate on client identity check the TLS ClientHello fingerprint (cipher/extension order) *and* HTTP header ordering — spoofing `User-Agent` alone fails. When JA4 mismatch is the block, either run the actual browser (headless with a matching build) or use `curl-impersonate` / `noble-tls` to reproduce the exact ClientHello.

## Open redirect, subdomain takeover, info-disclosure quick pivots

**Open-redirect bypass characters** to cycle against `?redirect=`, `?next=`, `?url=`, `?returnTo=` parameters: `@`, `%00`, `%09`, `//attacker`, `///attacker`, `\attacker`, `http:attacker`, `//\attacker`, `//attacker%23target`, CRLF (`%0d%0a`), unicode homoglyph domains. Chain with OAuth `redirect_uri` for token theft (see also `dirty-dancing` above).

**Subdomain takeover**: dangling `CNAME` to a de-registered SaaS resource (GitHub Pages, S3, Heroku, Azure, Fastly) — claim the resource on that service, own the subdomain. Enumeration: `subfinder | httpx | dnsx` → grep for `NoSuchBucket`, `404 Not Found` from *the SaaS provider*, `there isn't a GitHub Pages site here`.

**Apache `mod_status` info-disclosure**: `/server-status` (often accessible from localhost or when misconfigured) lists active URLs with client IPs and session IDs live — use for admin-endpoint discovery and short-lived session hijack.

**Apache CVE-2012-0053 HttpOnly cookie leak**: send an oversized `Cookie:` header (≥48000 bytes on old Apache 2.2.x) to trigger a 400 whose error page reflects the offending cookie — leaks `HttpOnly` cookies to any XSS that can read the response body.

## See also

- `sql-injection.md` — SQL-specific auth bypass and data extraction
- `web-vulnerabilities-and-cves.md` — framework and product-specific auth-impacting CVEs
