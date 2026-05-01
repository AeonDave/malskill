---
name: recon-technique
description: "Technique-first reconnaissance methodology for mapping an attack surface before active testing. Covers passive collection (zero target contact), active enumeration (controlled probing), the iterative transition between phases, and how to produce a prioritized attack plan for vulnerability scanning. Use when you need to scope a target, identify high-value entry points, and decide where to invest deeper analysis."
license: MIT
compatibility: "Any OS; external network perimeter, web applications, domain/IP scope."
metadata:
  author: AeonDave
  version: "1.0"
  category: offensive-techniques
  language: multi
---

# Recon technique

Goal: map the attack surface with minimal noise, identify high-value entry points, and produce a structured attack plan that drives the next phase (vulnerability scanning, exploitation).

## When this technique applies

- External perimeter scoping before a pentest or red team engagement.
- Bug bounty scope expansion: discover assets before prioritizing targets.
- CTF host/service mapping before exploitation.
- Pre-exploitation scoping: "where do I spend time?" before vuln scanning.

## Boundary

- **vs. osint-technique**: OSINT covers identity/person/organization research from public online sources. Recon-technique is attack-surface mapping — domains, IPs, services, endpoints. They overlap at passive DNS and infrastructure pivoting; when recon needs deeper person/company context, load `osint-technique`.
- **vs. network-technique**: network-technique covers protocol analysis, PCAP, and in-engagement pivoting. Recon-technique is pre-exploitation surface mapping.
- **vs. vuln-scanners**: recon produces the target list and service inventory that vuln scanners consume. Do not skip recon and throw scanners at the whole scope.

## Agent operating model

Recon is **iterative**, not a single pass. Each discovery opens new threads.

```
Loop:
  1. Passive collection — zero target contact.
  2. Catalog assets and identify high-value threads.
  3. Active enumeration — controlled probing of selected targets.
  4. Pivot: new findings trigger new passive queries or deeper active probes.
  5. Repeat until diminishing returns.

Exit when: attack surface is mapped well enough to produce a ranked target list.
```

Do not move to vulnerability scanning before you have a clear service inventory and a prioritized entry point list.

---

## Phase 1 — Passive recon

Zero direct contact with target infrastructure. All data from public or archived sources.

**Goal**: build a broad asset map — domains, subdomains, IPs, tech stack — without generating any target-side logs.

### 1.1 Scope definition

- Define target: root domain(s), IP ranges, organization name, known product brands.
- Note explicit out-of-scope assets.
- Confirm rules of engagement and legal authorization before any action.

### 1.2 Domain and subdomain discovery

Use certificate transparency, passive DNS, and search engines — no direct DNS queries to target resolvers yet.

Sources to check:
- Certificate Transparency logs (crt.sh, certspotter, Facebook CT monitor)
- Passive DNS aggregators (SecurityTrails PDNS, DNSDB, Farsight)
- Search engine dorking: `site:target.com`, `site:*.target.com`
- Archive and index: Wayback Machine, Common Crawl, URLScan
- GitHub / GitLab code search: internal domain leaks, subdomains in configs

Tool families:
- `offensive-tools/recon/subfinder/` — passive subdomain aggregation from multiple sources
- `offensive-tools/osint/amass/` — DNS passive collection + OSINT integrations
- `offensive-tools/osint/theharvester/` — emails and subdomains from search engines and DNS sources

### 1.3 IP and ASN mapping

Map the organization's IP space without scanning it.

- WHOIS and RDAP for IP ranges (ARIN, RIPE, APNIC).
- ASN lookup → BGP prefixes → full IP space.
- Reverse DNS lookups on IPs found in certificate SANs.
- Cloud provider ASN correlation (AWS/GCP/Azure prefix lists — compare with organization WHOIS).

Tool families:
- `offensive-tools/recon/asnmap/` — domain/IP/org → full CIDR ranges from ASN data (passive)
- `offensive-tools/recon/shodan/` — historical host/service data indexed passively (no direct contact with target)

### 1.4 Technology and exposure fingerprinting

Identify tech stack, service versions, and historical exposure without touching the target.

- Shodan/Censys historical banners for discovered IP ranges.
- GitHub / GitLab: search for secrets, config leaks, internal domain references.
- Job postings: infer stack from listed technologies (AWS, Spring Boot, PostgreSQL…).
- Wayback Machine: discover dead endpoints, old parameter structures, removed admin paths.

Tool families:
- `offensive-tools/recon/shodan/` — historical exposure, open ports, banners, certificates
- `offensive-tools/recon/gau/` — known URLs from Wayback, Common Crawl, URLScan per domain

### 1.5 Passive phase output

Produce before moving to active:
- Subdomain list (confirmed + unresolved candidates)
- IP ranges and ASNs attributed to target
- Tech stack hypothesis per major asset
- Historical exposure signals (old endpoints, leaked configs, dead admin paths)

---

## Phase 2 — Active recon

Controlled direct contact with target infrastructure. Generates logs on target side — scope and pace within authorization limits.

**Goal**: resolve the passive asset map into a concrete service inventory — open ports, service versions, web endpoints, and ranked attack surface.

### 2.1 DNS resolution and validation

Resolve the passive subdomain list. Filter dead hosts and wildcard noise before deeper work.

Tool families:
- `offensive-tools/recon/dnsx/` — bulk DNS resolution, wildcard detection, filtering
- `offensive-tools/recon/massdns/` — high-throughput DNS resolution and brute-force

After initial resolution, expand with active brute-force: use permutation generators (`altdns`, `gotator`) to derive candidates from confirmed subdomains (`dev-app`, `app-staging`, `v2-api`), then brute-force resolve with validated resolvers (`puredns`, `shuffledns`). Permutation expansion finds assets that passive sources miss. See [references/active-recon.md](references/active-recon.md).

### 2.2 Port sweep

Fast breadth-first sweep across confirmed IP space. Identify open ports — do not probe services yet.

- Start with top-1000 or common-service ports for speed.
- Full-port sweep only on hosts confirmed as high value from passive phase.

Tool families:
- `offensive-tools/network/masscan/` — ultra-fast TCP/UDP sweep over large ranges
- `offensive-tools/network/rustscan/` — fast discovery with optional nmap handoff

### 2.3 Service and version enumeration

Deep scan on ports identified in sweep. Version detection, banner grab, default script set.

Tool families:
- `offensive-tools/network/nmap/` — version detection, NSE scripts, OS fingerprint

### 2.4 HTTP fingerprinting and visual triage

For every web-accessible host: status, title, tech stack, redirect chain, TLS metadata. Screenshot for visual ranking of large scopes.

Tool families:
- `offensive-tools/recon/httpx/` — HTTP probing at scale: status, title, tech, TLS
- `offensive-tools/recon/eyewitness/` — screenshot all HTTP services for visual triage

Detect WAFs and security controls during this phase — before content discovery or parameter fuzzing. `httpx -tech-detect` surfaces common WAFs inline; dedicated WAF fingerprinting identifies vendor and product for targeted bypass strategy. Adjust tooling (lower rate, evasion headers, tamper scripts) before probing WAF-protected hosts.

Tool families:
- `offensive-tools/recon/wafw00f/` — WAF vendor fingerprinting; run per high-value host before injection testing

### 2.5 Web content discovery

Discover hidden endpoints, admin panels, APIs, and exposed files on confirmed web hosts. Target the highest-value hosts first.

Tool families:
- `offensive-tools/recon/feroxbuster/` — recursive content and endpoint brute-force
- `offensive-tools/recon/gobuster/` — directory and file enumeration

### 2.6 URL and parameter harvesting

Collect known URLs and parameters from crawl, JS analysis, and public archives for confirmed live hosts.

Tool families:
- `offensive-tools/recon/katana/` — JS-aware web crawler; headless mode for SPA/React/Angular apps
- `offensive-tools/recon/hakrawler/` — fast link extraction from static HTML
- `offensive-tools/recon/gau/` — passive URL harvest per live host (Wayback, URLScan, Common Crawl)

### 2.7 Cloud asset discovery

Modern targets host storage, APIs, and internal tooling in cloud providers outside their own WHOIS/ASN footprint. Shadow IT, dev environments, and data exports frequently appear here.

**Passive (no direct contact):**
- Search CT logs for cloud-specific subdomain patterns: `target.s3.amazonaws.com`, `target.blob.core.windows.net`, `target.storage.googleapis.com`.
- Query `GrayhatWarfare` for publicly indexed buckets matching the organization name or product names.
- Extract cloud provider indicators from TXT records (SPF/SES tokens → AWS SES, Google Workspace, etc.).

**Active:**
- Derive bucket name candidates from organization name, product names, and confirmed subdomains.
- Test discovered bucket candidates for public read/write access.
- Confirm cloud provider per IP range (cross-reference AWS/GCP/Azure prefix lists — see passive-recon.md).
- Use permutation wordlists from known subdomains (`altdns`, `gotator`) to generate bucket name candidates before testing.

Tool families:
- `s3scanner` — enumerate and test S3 bucket permissions (no dedicated skill — `pip install s3scanner`, then `s3scanner scan --buckets candidates.txt`)
- `cloud_enum` — multi-cloud enumeration across S3, Azure Blobs, GCP Storage (no dedicated skill — `python cloud_enum.py -k orgname`)

See [references/cloud-recon.md](references/cloud-recon.md) for detailed patterns and naming strategies.

---

## Transition model

### Passive → Active

Move when:
- Subdomain list is stable (two to three passes return no new unique results).
- At least one high-value target cluster is identified.
- IP space attribution is bounded.

Stay in passive when:
- New subdomains still appear rapidly (scope not bounded).
- Active authorization is not yet confirmed.

### Active recon → Vulnerability scanning

Move when:
- Service inventory per host is stable (port + version + web tech known).
- At least 3-5 prioritized entry points are identified with specific rationale.
- Content discovery on key web hosts is complete.

---

## Attack plan output

Recon ends when the agent produces this structured output:

### Asset inventory

| Asset | Type | IP | Ports | Tech | Priority |
|-------|------|----|-------|------|----------|
| app.target.com | Web app | 1.2.3.4 | 443 | Nginx, React, Node | High |
| api.target.com | REST API | 1.2.3.5 | 443 | Express, PostgreSQL | High |
| admin.target.com | Admin panel | 1.2.3.6 | 443, 8443 | Apache, PHP | Critical |

### Entry point ranking

Rank by:
- **Exposure surface**: public-facing, unauthenticated, legacy tech
- **Data value**: admin access, credential endpoints, file upload, API keys
- **Historical signals**: leaked configs, known CVEs for detected versions, dead paths still live

### Next-phase recommendations

Per high-priority target, specify:
- Suggested vuln scanner or technique (e.g., nuclei with matched templates, sqlmap on form endpoints)
- Detected service version → relevant CVE search scope
- Manual investigation areas (e.g., admin panel requires auth bypass testing, file upload requires extension bypass)

---

## Quality gates

- Passive phase complete before active probing starts.
- DNS resolution validated — no stale or dead hosts in active target list.
- Port sweep rate and scope confirmed within authorization limits.
- HTTP fingerprinting done on all live web hosts before content discovery.
- Attack plan specifies exact targets with rationale, not vague categories.

## Anti-patterns

- Starting vuln scanners before completing service inventory.
- Running content discovery on the entire IP range (pick targets from fingerprinting first).
- Treating Shodan results as ground truth without active confirmation.
- Expanding scope during active phase without re-checking authorization.
- Reporting every subdomain found instead of ranking by attack surface value.
- Confusing recon with OSINT — person/identity research is a different phase.

## Resources

- [references/passive-recon.md](references/passive-recon.md) — passive source catalog, Google dork patterns, GitHub search operators, Wayback/archive strategy, subdomain enumeration and permutation candidate preparation.
- [references/active-recon.md](references/active-recon.md) — port sweep profiles, DNS brute-force and permutation commands, WAF detection, service enumeration patterns, HTTP fingerprinting workflow, content discovery strategy, URL/parameter harvesting.
- [references/cloud-recon.md](references/cloud-recon.md) — cloud asset discovery for AWS/Azure/GCP: bucket enumeration, cloud subdomain patterns, metadata SSRF, multi-cloud tooling.
