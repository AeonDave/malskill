---
name: vuln-search-technique
description: "Active vulnerability discovery methodology for AI agents. Covers the full find loop: service version fingerprinting, CVE correlation and prioritization, automated scanner orchestration (nuclei/nikto/openvas), nmap NSE script probing, targeted tool scanning (testssl/wpscan/sqlmap probe), fuzzing integration, and manual logic review. Use when you have a scoped target inventory from recon and need to systematically identify exploitable vulnerabilities before attempting initial access."
license: MIT
compatibility: "Linux/Windows/macOS; web apps, network services, APIs, infrastructure targets."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Vuln-search technique

Goal: convert a recon-produced asset inventory into a **confirmed, prioritized, exploitable vulnerability list** ready for `vuln-exploit-technique` or `web-exploit-technique`.

## When this technique applies

- Recon is complete: asset inventory, open ports, service versions, web tech known.
- Need systematic vulnerability discovery before attempting exploitation.
- Scope requires coverage (audit, pentest) — not opportunistic attack.
- Target includes web applications, APIs, or services requiring deeper manual analysis.

## Boundary

- **Input from `recon-technique`**: asset list, port/service/version inventory, web fingerprint.
- **Output to `vuln-exploit-technique`**: confirmed infrastructure/service vulnerabilities with CVE, severity, exploitation path.
- **Output to `web-exploit-technique`**: confirmed web app vulnerabilities (SQLi, SSRF, auth bypass, etc.) with class, surface, and exploitation route.
- **Not covered**: exploitation — this skill stops at confirmed finding + exploitation route.
- **Fuzzing**: deep campaigns follow `fuzzing-technique`; integrated here as a bounded probe phase.

## Agent operating model

```
Loop per target:
  1. Fingerprint service version precisely.
  2. Correlate version against CVE databases — prioritize by exploitability.
  3. Run automated scanners (nuclei, nikto, nmap NSE).
  4. Run targeted tool probes per detected tech/service.
  5. Fuzz high-value input surfaces for unknown vulns.
  6. Review logic and config manually for issues scanners miss.
  7. Triage and rank findings — eliminate false positives.

Exit when: confirmed finding list covers all high-priority targets
           OR scope time/effort budget exhausted.
```

---

## Phase 1 — Version fingerprinting

Precise version identification enables accurate CVE matching. Vague version ranges produce noise.

```bash
# nmap — service version + banner
nmap -sV --version-intensity 9 -p <ports> <target>

# nmap — OS fingerprint (combine with version)
nmap -sV -O -p <ports> <target>

# Banner grab specific port
nc -nv <target> <port>
curl -sI https://target.com            # HTTP headers
curl -sI --http1.1 https://target.com  # force HTTP/1.1 for different response
```

Extract:
- Software name + version (Apache 2.4.49, nginx 1.18.0, OpenSSH 7.4)
- Framework versions (PHP 7.4.3, Spring Boot 2.5.1, Django 3.1)
- OS and kernel (Linux 4.15, Windows Server 2016)
- SSL/TLS versions and cipher suites

---

## Phase 2 — CVE correlation and prioritization

Cross-reference detected versions against vulnerability databases. Prioritize by exploitability, not CVSS alone.

### Lookup sources (priority order)

| Source | What it gives |
|--------|--------------|
| CISA KEV Catalog | Actively exploited in the wild — highest priority |
| NVD / CVE.org | Full CVE details, CVSS score, affected versions |
| exploit-db / searchsploit | Public exploits available for this CVE |
| GitHub PoC search | Unregistered PoCs, fresh exploits |
| Vulners / VulDB | Aggregated exploit intelligence |

### Prioritization model

```
Score = exploitability × impact × availability

Tier 1 — Act immediately:
  - CISA KEV listed
  - Public exploit available (exploit-db / GitHub PoC)
  - CVSS ≥ 9.0 (Critical) + network attack vector + no auth required

Tier 2 — High priority:
  - CVSS 7.0-8.9 + known exploit path
  - Authentication bypass, RCE, SQLi, SSRF

Tier 3 — Medium priority:
  - CVSS 4.0-6.9 + requires some conditions
  - XSS, info disclosure, config weakness

Tier 4 — Document only:
  - No public exploit, CVSS < 4.0, requires complex conditions
```

See `references/cve-correlation.md` for database search patterns and version matching.

Use SSVC-style prioritization when a CVSS number does not capture urgency. Combine exploitation status, technical impact, automatability, exposure, and mission prevalence into action labels (`Track`, `Track*`, `Attend`, `Act`); see `references/risk-prioritization.md`.

---

## Phase 3 — Automated scanner orchestration

Run scanners in layers — broad first, targeted second. Never only one scanner.

### nuclei — template-based vulnerability scanning

Primary scanner. 12,000+ community templates covering CVEs, misconfigs, exposures, tech-specific checks.

```bash
# Scan with all default templates
nuclei -u https://target.com

# Target-specific template categories
nuclei -u https://target.com -t cves/             # CVE checks
nuclei -u https://target.com -t exposures/        # exposed files, configs
nuclei -u https://target.com -t misconfigurations/ # server misconfigs
nuclei -u https://target.com -t technologies/     # tech fingerprint
nuclei -u https://target.com -t vulnerabilities/  # known vuln patterns

# Scan list of URLs
nuclei -list urls.txt -t cves/ -o nuclei_cves.txt

# Filter by severity
nuclei -u https://target.com -severity critical,high -o high_crit.txt

# Match specific CVE
nuclei -u https://target.com -id CVE-2021-44228

# Rate control (avoid aggressive default on sensitive scopes)
nuclei -u https://target.com -rate-limit 50 -concurrency 10
```

See `offensive-tools/vuln-scanners/nuclei/` for template selection and custom template writing.

### nikto — web server audit

Complements nuclei at the server config layer (headers, methods, legacy paths, default content).

```bash
# Standard web scan
nikto -h https://target.com

# With authentication
nikto -h https://target.com -id user:pass

# Specific port
nikto -h target.com -p 8080

# Output to file
nikto -h https://target.com -output nikto_out.txt -Format txt
```

See `offensive-tools/vuln-scanners/nikto/`.

### openvas — broad authenticated or infrastructure scanning

Use OpenVAS/GVM when the scope requires broad infrastructure coverage, authenticated checks, or vulnerability-management style reporting. Keep it rate-controlled and scoped; use targeted tools for validation.

```bash
# Run from the OpenVAS/GVM UI or automation wrapper.
# Configure: target list, port list, scan config, credentials if authorized.
# Export results, then manually validate high-risk findings before handoff.
```

See `offensive-tools/vuln-scanners/openvas/`.

### nmap NSE scripts — service-level probing

Run targeted NSE scripts per service type after version detection.

```bash
# HTTP specific
nmap --script http-vuln-* -p 80,443 target.com
nmap --script http-auth-finder,http-methods,http-headers -p 80,443 target.com

# SMB
nmap --script smb-vuln-ms17-010,smb-vuln-cve-2017-7494 -p 445 target.com
nmap --script smb-enum-shares,smb-os-discovery -p 445 target.com

# SSH
nmap --script ssh-auth-methods,ssh-vuln-cve2018-10933 -p 22 target.com

# SSL/TLS
nmap --script ssl-enum-ciphers,ssl-heartbleed,ssl-poodle -p 443 target.com

# FTP
nmap --script ftp-anon,ftp-bounce,ftp-vuln-cve2010-4221 -p 21 target.com

# All vuln scripts (noisy)
nmap --script vuln -p <open_ports> target.com
```

---

## Phase 4 — Targeted tool probing

Per detected technology, run the purpose-built scanner.

### SSL/TLS — testssl

```bash
testssl --severity HIGH --parallel https://target.com
testssl --full https://target.com          # all checks
testssl --openssl-timeout 20 target.com:443
```

See `offensive-tools/vuln-scanners/testssl/`.

### WordPress — wpscan

```bash
wpscan --url https://target.com --enumerate vp,vt,u  # plugins, themes, users
wpscan --url https://target.com --api-token <token>   # CVE database lookup
```

See `offensive-tools/vuln-scanners/wpscan/`.

### SQL injection probe — sqlmap (detection only)

```bash
# Probe only — no exploitation yet
sqlmap -u "https://target.com/page?id=1" --level=2 --risk=1 --batch --dbs
sqlmap -u "https://target.com/page?id=1" --forms --crawl=2 --batch
```

See `offensive-tools/vuln-scanners/sqlmap/` for detection patterns. Full exploitation in `vuln-exploit-technique`.

### Additional targeted probes

| Tech detected | Tool | Skill |
|---------------|------|-------|
| SSRF indicators | `ssrfmap` | `offensive-tools/vuln-scanners/ssrfmap/` |
| SSTI indicators | `sstimap` | `offensive-tools/vuln-scanners/sstimap/` |
| CORS misconfiguration | `corsy` | `offensive-tools/web/corsy/` |
| XSS surfaces | `dalfox` | `offensive-tools/vuln-scanners/dalfox/` |
| NoSQL injection | `nosqlmap` | `offensive-tools/vuln-scanners/nosqlmap/` |
| HTTP smuggling | `smuggler` | `offensive-tools/web/smuggler/` |

---

## Phase 5 — Web application analysis

For web-accessible targets identified in fingerprinting, apply a structured analysis before declaring no findings. Automated scanners miss logic flaws, broken auth, and injection in complex inputs.

### 5.1 Application mapping

Before probing, understand the attack surface:

- Enumerate all endpoints via crawl (katana, hakrawler) + gau historical data.
- Map authentication boundary: which endpoints require auth? Which allow anonymous access?
- Identify state-changing operations: POST/PUT/DELETE endpoints, form submissions, file uploads.
- Locate API entry points: `/api/`, `/graphql`, `/rest/`, Swagger/OpenAPI docs at `/swagger`, `/api-docs`.
- Note data flows: where does user input go? What parameters reach the backend?

### 5.2 Authentication and session analysis

```
Checklist:
- [ ] Login brute-force protection? (rate limiting, lockout)
- [ ] Password reset flow: token entropy, expiry, reuse
- [ ] Session token entropy and predictability
- [ ] Session invalidation on logout
- [ ] JWT: algorithm confusion (alg:none, RS256→HS256), weak secret, expired token accepted
- [ ] OAuth: state parameter missing, redirect_uri bypass, token leakage in referrer
- [ ] MFA: OTP replay, backup code brute-force, bypass via response manipulation
- [ ] Auth response manipulation: change "success":false to true, remove error field
```

### 5.3 Authorization and access control analysis

```
Checklist:
- [ ] IDOR: replace numeric/UUID IDs with other users' values in every endpoint
- [ ] Horizontal privilege: user A accessing user B's resources
- [ ] Vertical privilege: regular user accessing admin/staff endpoints
- [ ] Function-level auth: unauthenticated access to authenticated endpoints
- [ ] Mass assignment: add extra fields to POST/PUT (isAdmin, role, price)
- [ ] HTTP method override: X-HTTP-Method-Override, _method parameter
- [ ] GraphQL introspection enabled → full schema exposure; BOLA on object IDs
```

### 5.4 Injection surface identification

Map inputs that reach dangerous sinks:

| Input type | Where to probe | Injection class |
|------------|---------------|-----------------|
| URL parameters | `?id=`, `?query=`, `?url=` | SQLi, SSRF, path traversal |
| POST body fields | form data, JSON, XML | SQLi, SSTI, XXE, cmd injection |
| HTTP headers | `User-Agent`, `X-Forwarded-For`, `Referer`, `Host` | SQLi, SSRF, header injection |
| File upload | filename, content, MIME type | RCE, XSS, path traversal |
| Cookie values | session, user IDs | SQLi, SSRF, deserialization |
| JSON/XML bodies | nested keys, type coercion | NoSQLi, XXE, SSTI |

For each input surface: probe with class-specific detection payload before confirming. Do not exploit without confirming.

### 5.5 Config and exposure checks

```
Checklist:
- [ ] CORS: Access-Control-Allow-Origin: * or reflects Origin with credentials
- [ ] Security headers missing: CSP, X-Frame-Options, HSTS, X-Content-Type-Options
- [ ] Admin/debug endpoints reachable: /admin, /debug, /actuator/env, /phpinfo.php
- [ ] Directory listing enabled
- [ ] Sensitive files exposed: .env, .git/HEAD, .DS_Store, backup.zip
- [ ] API versioning: does /api/v1/ have weaker controls than /api/v2/?
- [ ] Error messages reveal stack trace, DB type, internal paths
- [ ] HTTP methods: TRACE/OPTIONS enabled, PUT allowed
```

See `references/web-vuln-analysis.md` for per-class detection workflows (SQLi/SSRF/SSTI/XSS/auth).

---

## Phase 6 — Fuzzing integration

When automated scanners return no findings on custom or complex input handlers, apply targeted fuzzing.

- Use `fuzzing-technique` for the full fuzzing loop.
- Apply here as a bounded probe: 1-2 entry points, short campaign, clear oracle.
- Priority surfaces for fuzzing: file upload endpoints, deserialization inputs, custom parsers, API parameters with complex types.

---

## Phase 7 — Manual logic review

Scanners miss: auth logic flaws, IDOR, business rule bypasses, race conditions, insecure direct object references.

Manual checks per target type:

**Web application:**
- Test auth flows: can you access resource B while authenticated only for A?
- IDOR: replace numeric/UUID IDs with other users' values
- Mass assignment: add extra fields to POST/PUT and check if they're accepted
- Rate limiting: does login/reset/OTP endpoint enforce limits?
- HTTP method override: does `X-HTTP-Method-Override: DELETE` work?

**API:**
- GraphQL introspection enabled? → full schema exposure
- Broken function-level auth: can regular user hit admin-only endpoints?
- JWT: `alg:none` accepted? Secret brute-forceable? Expired token accepted?
- See `offensive-tools/web/jwt-tool/` for JWT attack surface

**Infrastructure:**
- Default credentials on admin panels (router, camera, NAS, Jenkins, Grafana)
- Debug/actuator endpoints exposed (Spring `/actuator/env`, Rails `/rails/info`)
- Internal services reachable due to firewall misconfiguration

---

## Triage and severity model

After scanning, consolidate findings:

1. **Deduplicate**: same vulnerability class on same endpoint = one finding
2. **Verify**: run the scanner-reported finding manually to confirm it's not a false positive
3. **Rate by exploitation chain**:
   - Directly exploitable without auth → Critical/High regardless of CVSS
   - Exploitable post-auth → rate by privilege level required
   - Requires chaining → rate combined impact
4. **Document evidence**: request/response pair, screenshot, exact CVE or class

Use `references/false-positive-elimination.md` before handing findings to exploitation; it defines positive/negative controls, confounder checks, and confidence levels.

## Quality gates

- No exploitation attempt before confirming vulnerability is real (not scanner FP).
- Version match verified against actual banner, not assumed from nmap guess.
- At least two different scan methods cover each high-priority target.
- All Tier 1 and Tier 2 findings have verified evidence before handoff.
- Scanner findings reach C3 confidence (reproducible with positive and negative controls) before exploitation handoff.

## Anti-patterns

- Running every scanner on every host without version-guided prioritization.
- Accepting scanner output as ground truth without manual verification.
- Skipping manual logic review on web apps (scanners miss auth/IDOR/business logic).
- Jumping to exploitation before confirming finding is real and in scope.
- Reporting CVSS score as exploitation likelihood — they are not the same.

## Resources

- [references/cve-correlation.md](references/cve-correlation.md) — CVE lookup patterns, CISA KEV usage, version-to-CVE matching, exploitability scoring.
- [references/risk-prioritization.md](references/risk-prioritization.md) — SSVC-style prioritization, EPSS/KEV context, exploitation status, mission relevance, and offensive handoff criteria.
- [references/scanner-workflow.md](references/scanner-workflow.md) — nuclei template selection, nikto interpretation, nmap NSE script catalog, targeted scanner chaining.
- [references/web-vuln-analysis.md](references/web-vuln-analysis.md) — per-class web vulnerability detection: SQLi, XSS, SSRF, SSTI, XXE, auth flaws, IDOR, file upload, deserialization.
- [references/false-positive-elimination.md](references/false-positive-elimination.md) — manual reproduction, control matrix, confounder checks, confidence levels, and evidence package before exploit handoff.
