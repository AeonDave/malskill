# Attack-Path Hints & Severity Decision Matrix

Reference for: (a) scoring rubrics that convert raw findings into severity, (b) attack-path hint templates to attach to HIGH/CRIT findings so the operator knows where to pivot. Methodology link: `osint-technique/SKILL.md` §20+§21+§39+§40.

> **Scope note:** this file scores OSINT findings and describes *target-state hints* used to assess severity (e.g. "why is an exposed Redis CRITICAL"). Any examples that look like exploitation (PUT, `CONFIG SET`, kubelet exec, RCE PoCs) are **severity-assessment heuristics only** — actual exploitation belongs to [vuln-exploit-technique](../../vuln-exploit-technique/) and [web-exploit-technique](../../web-exploit-technique/). OSINT operators stop at evidence of exposure; they do not execute write-side or post-auth actions.

---

## 1. Endpoint Interest Score — 0–100

For every classified endpoint, sum signal points:

| Signal | Points | Condition |
|---|---|---|
| Unauth write | +40 | POST/PUT/DELETE/PATCH returns 2xx anonymously |
| Open GraphQL introspection | +35 | `__schema` query returns full type list anon |
| Verb tampering bypass | +30 | OPTIONS reveals undocumented method, accessible |
| Reflected CORS + credentials | +25 | `ACAO` reflects `Origin` AND `ACAC: true` |
| Sensitive keyword in path | +20 | matches: `admin`, `internal`, `debug`, `user`, `password`, `token`, `key`, `export`, `upload`, `backup`, `config`, `secret`, `private`, `delete`, `purge`, `wipe` |
| Schema leak in error | +20 | body has stack trace / ORM class / framework signature (`ActiveRecord::RecordNotFound`, `org.hibernate.exception.*`, `django.db.utils.IntegrityError`) |
| API key in URL | +15 | path/query has `api_key=`/`apikey=`/`token=`/`access_token=` |
| Wildcard CORS | +10 | `Access-Control-Allow-Origin: *` |
| Missing rate-limit headers | +10 | no `RateLimit-*` / `X-RateLimit-*`, no `Retry-After` after rapid req |

**Thresholds**

| Score | Severity |
|---|---|
| ≥ 90 | CRITICAL |
| 70–89 | HIGH |
| 50–69 | MEDIUM |
| 25–49 | LOW |
| < 25 | INFO |

Score ≥ 70 → attach `attack_path_hint` (§3 below).

---

## 2. Mobile App Ownership Confidence — 0–100

Score before deep APK analysis. Threshold ≥ 70 = accept.

| Signal | Points |
|---|---|
| Package reverse-DNS matches target domain (`com.acme.android` ⟂ `acme.com`) | +40 |
| Developer email `<anything>@<target-domain>` | +25 |
| Developer website = target domain (or confirmed sibling brand) | +20 |
| App name contains brand keyword from operator list | +10 |
| Reviews ≥ threshold (default 20) | +5 |

Below threshold → tag `mobile_review_pending`. Operator override: `--mobile-ownership-threshold 50`.

---

## 3. Attack-path hint templates

Attach to every HIGH/CRIT finding so operator immediately knows next move.

| Trigger | Attack-path hint template |
|---|---|
| Unauth POST/PUT/DELETE | *"Unauth {method} {path} — try IDOR + privilege escalation; check whether numeric IDs are sequential or guessable."* |
| Open GraphQL introspection | *"Open GraphQL introspection on {path} — enumerate mutations, look for `createUser`/`setRole`/`transferFunds`-shaped names; pivot to broken-auth or business-logic flaws."* |
| Reflected CORS + creds | *"Reflected CORS with creds on {path} — host CSRF page on attacker origin; victim browser leaks {sensitive-data}."* |
| Wildcard CORS + sensitive | *"Wildcard CORS on {path} returning user-tied data without creds — exfil via cross-origin fetch from any page victim visits."* |
| Verb tampering | *"Verb tampering: {hidden-method} allowed on documented-{visible-method}-only endpoint → likely missing-method-check authz; try {hidden-method} {path} with valid auth."* |
| API key in URL | *"API key in URL `?{param}=...` — token leaks to access logs, browser history, Referer, third-party CDNs. Check Wayback / Google cache."* |
| Schema leak in error | *"Schema leak — framework signature `{framework}` exposed; map to known {framework} vulns + craft targeted payloads."* |
| Sensitive keyword | *"Path contains '{keyword}' — review IDOR, mass-assignment, hidden admin functionality."* |
| Open Firebase RTDB | *"Open Firebase RTDB at `https://{project}.firebaseio.com/.json` — read all, then PUT `/<random>.json` to gauge ACL."* |
| Listable cloud bucket | *"Listable {provider} bucket `{bucket}` — recursive list + content-type analysis; backups, logs, customer data, AWS keys in JSON configs."* |
| .git exposed | *"Exposed `.git/config` on {host} — reconstruct repo with git-dumper/githacker; full history."* |
| .env exposed | *"Exposed `.env` on {host} — grep `_KEY`/`_SECRET`/`_TOKEN`/`_PASSWORD`; validate read-only via `secret-patterns-and-validators.md` §2."* |
| /actuator/env | *"Spring Boot `/actuator/env` exposed — dump env; `spring.datasource.password`, JWT secrets, cloud creds."* |
| /actuator/heapdump | *"Spring Boot `/actuator/heapdump` — download HPROF, `jhat` / VisualVM, search cleartext secrets in heap strings."* |
| Open Elasticsearch | *"Open ES on {host}:9200 — `/_cat/indices?v`, sample docs per index, test write `/test-idx/_doc` for ACL."* |
| Open Redis | *"Open Redis on {host}:6379 — `INFO`/`KEYS *`/sample reads; test write via `CONFIG SET`+`BGSAVE` → `authorized_keys`."* |
| Open MongoDB | *"Open MongoDB on {host}:27017 — `show dbs`/`show collections`/sample find; user collection for password hashes."* |
| Subdomain takeover | *"CNAME for {host} → unclaimed {provider} → register `{takeover-target}` to serve content from trusted domain; phishing/content injection."* |
| Open kubelet | *"Open kubelet on {host}:10250 — `GET /pods`; `POST /run/<ns>/<pod>/<container>` for in-container exec without K8s API auth."* |
| Open etcd | *"Open etcd on {host}:2379 — `etcdctl get / --prefix --keys-only`; secrets under `/registry/secrets/`."* |
| K8s API anonymous | *"K8s API {host}:6443 anonymous-auth — `kubectl --server=https://{host}:6443 --insecure-skip-tls-verify get pods --all-namespaces`."* |
| Citrix unpatched | *"Citrix NetScaler {ver} on {host} — CVE-{cve} (KEV); advise immediate patch."* |
| F5 BIG-IP TMUI | *"F5 BIG-IP TMUI on {host} — CVE-2022-1388 / CVE-2023-46747 KEV; immediate hotfix."* |
| vCenter accessible | *"vCenter at {host} without VPN — CVE-2021-21972 RCE if unpatched."* |
| Lambda URL unauth | *"AWS Lambda Function URL `{url}` anonymous — review IAM auth; if intended public, audit input validation aggressively."* |
| npm typosquat candidate | *"Unregistered `{candidate}` ~ target's `{official}` — typosquat takeover risk; advise defensive registration."* |
| DMARC missing/permissive | *"DMARC `p=none` on {domain} — spoof of `{anything}@{domain}` deliverable; recommend `p=quarantine`/`reject` after RUA observation."* |
| Live AI API key | *"Validated `sk-{provider}-...` with model access — quota exfil; rotate + audit provider console logs."* |
| Public Slack invite | *"Slack invite link search-engine-discoverable — anyone joins workspace without approval; trivial internal channel access."* |
| Open Docker registry | *"Public Docker registry at {host} — `GET /v2/_catalog`; pull + scan layers for embedded secrets."* |
| Telegram bot token live | *"Telegram bot token live — `getUpdates` reveals recipients (admin chats); `getMe` + channel membership = full message read."* |
| Sourcemap `sourcesContent[]` | *"Sourcemap on {host} embeds original sources — full frontend reconstructable; grep inline secrets + internal hostnames."* |

---

## 4. Severity Decision Matrix — worked examples

When in doubt, anchor on these.

### CRITICAL
- `.git/config` reachable on prod webapp — full source disclosure; secret history reconstructable
- `.env` reachable on prod — plaintext DB/cloud/API creds
- Open Firebase RTDB returning data — all app data readable, often writable
- Listable S3 bucket with PII — direct data exfil
- Spring `/actuator/env` exposed — DB creds, JWT secrets, cloud keys
- Spring `/actuator/heapdump` exposed — heap holds live secrets in strings
- Open ES (`/_cat/indices` returns) — full reads, often writes
- Open MongoDB (no auth) — full data + password-hash collection
- Open Redis (no AUTH) — `authorized_keys` write → SSH foothold
- Open Docker API (2375) — container/host takeover
- Public PMAK live + broad scope — full Postman account + team workspaces
- Public AWS root access key live — full account compromise
- `android:debuggable=true` on prod — full client compromise
- Open kubelet on 10250 — pod exec without K8s API auth
- Open etcd on 2379 — cluster state + secrets
- Citrix NetScaler KEV CVE — actively exploited; patch immediately
- Pulse Secure CVE-2024-21887 — KEV; chained command injection
- FortiGate CVE-2024-21762 — KEV; auth bypass + RCE
- PaloAlto GlobalProtect CVE-2024-3400 — KEV; pre-auth RCE
- vCenter CVE-2021-21972 — KEV; pre-auth RCE
- MS Exchange ProxyShell/Logon/NotShell unpatched — KEV chain; RCE + mailbox dump
- GitLab self-hosted CVE-2021-22205 — KEV; ExifTool RCE
- Heartbleed (CVE-2014-0160) — memory disclosure inc. session tokens + keys
- Live npm/PyPI/Docker Hub/GHCR token w/ publish scope — supply-chain compromise
- Live Anthropic/OpenAI key w/ broad scope — quota + PII in past responses
- Decommissioned legacy mail (NXDOMAIN) + breach corpus has historical employee URLs against it + SSO migration confirmed via autodiscover IPs — passwords almost certainly survived migration via reuse; SSO_EXPOSURE escalates regardless of dead legacy host

### HIGH
- Listable S3 bucket with logs only — internal hostnames + paths; pivot data
- Live AWS IAM-user key on GitHub — limited scope, often elevatable
- Live GitHub PAT in JS bundle — repo write access (scope-dependent)
- Live Slack token in pastebin — workspace data + history
- Sourcemap (`.js.map`) on prod — frontend source disclosure
- Open GraphQL introspection on prod — schema → mutations + business logic
- Subdomain takeover possible (Heroku / GH Pages) — trusted-domain phishing
- Reflected CORS + creds on `/api/billing` — CSRF-via-CORS billing data
- Verb tampering: DELETE on documented-GET-only — authz bypass, destructive
- `phpinfo.php` on prod — paths, env vars, modules → vuln-version pivot
- Tomcat `/manager/html` reachable — default creds, WAR upload = RCE
- Jenkins script console accessible — Groovy = RCE
- Missing HSTS on `/login` (escalated from MED) — login pages must enforce
- Sensitive deep-link handler (`myapp://reset-password`) — other apps trigger sensitive flows
- F5 BIG-IP TMUI accessible — TMUI = admin panel
- VMware ESXi exposed without VPN — multiple CVEs (ESXiArgs)
- AWS Lambda Function URL anonymous — direct invocation; IAM posture
- Public Cloud Run / Function unauth — same
- GitHub Actions secrets echoed in workflow logs — full secret disclosure
- GitHub Actions `pull_request_target` checkout of fork code — secrets accessible to attacker PRs
- Public Trello board w/ creds in cards — often plaintext API keys
- MX server open relay (test 250 OK to foreign RCPT TO) — spam + spoof
- Atlassian token w/ admin scope — workspace read, sometimes write
- Subdomain takeover candidate confirmed — trusted-domain phishing
- WAF/CDN trivially bypassable (origin via fingerprinting) — all WAF nulled
- Public Slack invite link discoverable — anyone joins; full DM/channel
- Vendor/supplier/e-procurement portal exposed + breach corpus shows vendor accounts compromised — vendor impersonation + procurement fraud (BEC); regulatory exposure
- Careers portal collects PII over plain HTTP — cleartext PII at scale; GDPR/CCPA/DPDP/LGPD exposure

### MEDIUM
- Missing HSTS on standard pages — hardening gap
- Missing CSP — XSS mitigation gone
- Internal IP / K8s service DNS in JS — internal topology disclosure
- Apache `/server-status` reachable — live request visibility
- `android:allowBackup=true` (no whitelist) — data exfil via `adb backup`
- `android:usesCleartextTraffic=true` — MITM on hostile networks
- Exported Android component without permission — IPC attack surface
- Slack webhook URL leaked — send-to-channel; social-eng
- Twilio Account SID leaked (no auth token) — half cred pair; account enum
- Wildcard CORS on data-returning API — lower than reflected+creds, still exfil
- Public Notion page w/ internal SOPs — operational intel; sometimes creds
- Public Confluence space w/ onboarding docs — seed creds + tech-stack reveal
- DMARC `p=none` on prod sending domain — spoof feasible
- SPF `~all` w/o strict DMARC — spoofs land in spam, but land
- TLS 1.0/1.1 on prod — compliance; PCI-DSS forbids 1.0
- RC4 / 3DES accepted — NOMORE / SWEET32
- Self-signed cert on prod — trust failure
- Public Postman workspace w/ internal API endpoints — API attack surface mapped
- CI/CD wordlist hits (Jenkinsfile, .gitlab-ci.yml public) — build-script intel
- Public-facing intranet (`intranet.<domain>` no VPN) — org structure, employee directory
- Staging/preprod/UAT/sandbox publicly resolvable — weaker auth, debug endpoints, test creds; sometimes prod data
- Public Docker registry (anonymous catalog) — image enum + secret hunt in layers

### LOW
- Missing `X-Frame-Options` — clickjacking
- `.DS_Store` exposed — directory listing of dev machine
- Stripe **test** key leaked — no money risk
- Firebase URL exposed (no open RTDB) — project-ID disclosure only
- Cert pinning missing in mobile app — MITM on hostile networks
- Outdated WordPress detected — pending CVE confirmation
- Cert expires < 30 days — operational; not exploitable
- Public Miro board w/ architecture diagrams — internal-host disclosure

### INFO
- Missing `Referrer-Policy` / `Permissions-Policy` — hardening, not exposure
- `.well-known/security.txt` discovered — useful contact only
- Domain in breach with 0 named accounts — contextual
- Private bucket exists (HEAD 403) — asset only
- `vpn.<domain>` resolves but vendor/version unknown (passive only) — attack-surface flag; escalate HIGH-CRIT after active fingerprint matches KEV
- DMARC RUA → third-party reporting vendor (kdmarc/dmarcian/Valimail/Agari/EasyDMARC) — tenant signal only; vendor compromise = DMARC bypass for all their customers
