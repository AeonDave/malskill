# Auth and Access Control

Use this reference for authentication flaws, access-control bypasses, token abuse, and identity-flow attacks in web CTFs.

## Table of Contents
- [Fast triage](#fast-triage)
- [Sessions and cookies](#sessions-and-cookies)
- [Access-control failures](#access-control-failures)
- [JWT and JWE](#jwt-and-jwe)
- [OAuth, OIDC, and SAML](#oauth-oidc-and-saml)
- [Infrastructure and identity-admin pivots](#infrastructure-and-identity-admin-pivots)
- [Exotic auth edge cases](#exotic-auth-edge-cases)

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

## See also

- `sql-injection.md` — SQL-specific auth bypass and data extraction
- `field-notes.md` — compact quick-reference payloads and pivots
- `web-vulnerabilities-and-cves.md` — framework and product-specific auth-impacting CVEs
