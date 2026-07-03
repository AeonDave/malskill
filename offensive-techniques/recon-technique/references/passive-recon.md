# Passive Recon — Deep Dive

Passive recon uses only public or archived sources. Zero direct contact with target infrastructure.
Every technique here should leave no trace in target logs.

---

## Subdomain enumeration

### Certificate Transparency (CT) logs

Every TLS certificate issued is logged publicly. This reveals subdomains the organization has used historically.

```
# crt.sh — search by organization or domain
https://crt.sh/?q=%.target.com
https://crt.sh/?q=%.target.com&output=json

# Certspotter
https://sslmate.com/certspotter/api/v1/issuances?domain=target.com&include_subdomains=true&expand=dns_names

# Censys certificate search (web/API)
https://search.censys.io/certificates?q=target.com

# Google Transparency Report CT search
https://transparencyreport.google.com/https/certificates
```

Meta's Facebook CT monitor / API was discontinued in 2025 — do not depend on it.

Deduplicate and normalize names from CT results — SANs often include wildcard entries and internal hostnames.

### Passive DNS aggregators

Historical DNS resolution data — see what IPs a subdomain pointed to over time.

| Source | Coverage |
|--------|----------|
| SecurityTrails | Broad PDNS + history |
| DNSDB (Farsight) | Deepest historical coverage |
| RiskIQ PassiveTotal | PDNS + malware associations |
| VirusTotal PDNS | Free, limited history |

Pivot: if a subdomain historically resolved to a shared IP, check what other domains resolved to the same IP (reverse IP lookup → enumerate co-hosted assets).

### Search engine dorking

```
# Enumerate subdomains Google has indexed
site:*.target.com

# Find exposed files
site:target.com filetype:pdf OR filetype:docx OR filetype:xlsx
site:target.com filetype:env OR filetype:log OR filetype:sql

# Find login/admin pages
site:target.com inurl:login OR inurl:admin OR inurl:dashboard

# Find API docs
site:target.com inurl:swagger OR inurl:api-docs OR inurl:openapi

# Find configuration or backup files
site:target.com ext:bak OR ext:config OR ext:conf OR ext:backup

# Find credentials in public content
site:target.com "password" OR "api_key" OR "token" filetype:txt
```

### GitHub / GitLab / Bitbucket search

Source code leaks reveal internal subdomains, API endpoints, credentials, and infrastructure details.

```
# GitHub code search operators
org:target-org                          # repositories owned by org
"target.com" language:yaml              # YAML configs referencing domain
"internal.target.com"                   # internal subdomains
"api.target.com" "Authorization"        # auth patterns with domain
"target.com" "password" OR "secret"     # credential leaks
filename:.env "target.com"              # .env files
filename:docker-compose "target.com"    # docker configs
filename:*.conf "target.com"            # server configs
```

Tools: `trufflehog`, `gitleaks` for automated secret scanning on org repositories.

### Permutation candidate preparation (passive phase)

Before active brute-force begins, build a permutation seed list from all confirmed subdomains. This is passive work — no queries to the target.

```bash
# altdns — generate permutation candidates from confirmed subdomain list
# Output is a candidate list, not yet resolved. Feed into puredns/shuffledns in active phase.
altdns -i confirmed_passive.txt -o permutation_candidates.txt -w /path/to/words.txt

# Common permutation words that yield high hit rates:
# dev, staging, test, prod, api, v2, v1, internal, corp, admin, beta, old, legacy, backup
```

Permutation-derived names (`api-dev.target.com`, `staging-app.target.com`) are almost never indexed in CT logs or PDNS — they only surface through active brute-force. Prepare the candidate file during passive phase so it's ready when active probing begins.

### Archive and historical sources

```
# Wayback Machine — enumerate historical URLs for a domain
https://web.archive.org/cdx/search/cdx?url=*.target.com/*&output=text&fl=original&collapse=urlkey

# Common Crawl — indexed URLs
https://index.commoncrawl.org/

# URLScan.io — screenshots and link analysis for scanned pages
https://urlscan.io/search/#domain:target.com
```

Historic paths often remain live on current infrastructure. Pay attention to:
- `/api/v1/` endpoints that predate `/api/v2/`
- Admin paths like `/manage/`, `/backend/`, `/staff/`
- Upload directories and test endpoints

---

## IP and ASN mapping

### WHOIS and RDAP

```
# WHOIS lookup
whois target.com
whois 1.2.3.4

# RDAP (structured JSON alternative)
https://rdap.arin.net/registry/ip/1.2.3.4
https://rdap.arin.net/registry/domain/target.com
```

### ASN discovery

Find all IP ranges the organization owns.

```bash
# asnmap — domain/IP/org → all CIDR ranges (offensive-tools/recon/asnmap/)
asnmap -d target.com -silent
asnmap -org "Target Corporation" -silent
asnmap -i 1.2.3.4 -silent           # IP → ASN → full CIDR list

# BGP Toolkit (web — no install)
https://bgp.he.net/dns/target.com     # domain → ASN
https://bgp.he.net/AS12345#_prefixes  # ASN → prefixes

# Shodan ASN search (no direct target contact)
shodan search "org:\"Target Corp\""
shodan search "asn:AS12345"
```

### Cloud provider IP mapping

If target uses cloud providers, their IPs appear in cloud provider prefix lists:
- AWS IP ranges: `https://ip-ranges.amazonaws.com/ip-ranges.json`
- GCP: `https://www.gstatic.com/ipranges/cloud.json`
- Azure: Microsoft Download Center (Service Tags)
- Cloudflare: `https://www.cloudflare.com/ips/`

Cross-reference discovered IPs against these lists to identify cloud-hosted vs. on-prem assets.

---

## Technology fingerprinting (passive)

### Shodan and Censys

Query historical data without touching the target:

```
# Shodan — discover banners by domain/IP/org
shodan search "hostname:target.com"
shodan search "ssl.cert.subject.cn:target.com"
shodan search "org:\"Target Corporation\""

# Shodan — look for specific service versions
shodan search "product:\"Apache httpd\" hostname:target.com"
shodan search "vuln:CVE-2021-44228 org:\"Target Corp\""

# Censys (certificate-based host discovery)
https://search.censys.io/
```

Shodan banners include: service version, HTTP headers, TLS certificate, JARM fingerprint — all without a single packet to the target.

### Job postings

Job descriptions reveal tech stack. Indicators to extract:
- Cloud platform (AWS, GCP, Azure)
- Languages and frameworks (Java Spring, Python Django, Ruby Rails, Node.js)
- Databases (PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch)
- Infrastructure tools (Kubernetes, Terraform, Ansible, Jenkins)
- Security tools (Splunk, CrowdStrike, Okta, Ping Identity)

Each item narrows the likely attack surface (e.g., Elasticsearch → search for exposed instances; Okta → look for SSO bypass patterns).

### Wayback Machine — parameter and endpoint discovery

```
# All URLs ever indexed for a domain (via CDX API)
curl "http://web.archive.org/cdx/search/cdx?url=target.com/*&output=text&fl=original&collapse=urlkey&limit=5000"

# Filter for API endpoints
curl "http://web.archive.org/cdx/search/cdx?url=target.com/api/*&output=text&fl=original&collapse=urlkey"
```

Extract unique parameters from historical URLs — these often persist even when UI changes.

---

## Email and personnel pivot

Useful when recon includes credential stuffing scope or phishing simulation:

- `offensive-tools/osint/theharvester/` — email addresses from search engines
- `offensive-tools/osint/holehe/` — check if an email is registered on platforms
- LinkedIn: employee titles, technology vocabulary in profiles, org structure
- Hunter.io / Clearbit: email pattern discovery (`firstname.lastname@target.com`)

Email format discovery → credential stuffing list construction. Out of scope unless explicitly authorized.

---

## Passive recon quality checklist

- [ ] CT logs searched for wildcard and multi-level subdomains
- [ ] Passive DNS queried for historical A/CNAME records per subdomain
- [ ] Search engine dorks run for file types, admin paths, login pages
- [ ] GitHub org and keyword searches complete
- [ ] Wayback CDX dump collected and parsed for unique URL paths
- [ ] ASN and IP ranges confirmed via WHOIS + BGP data
- [ ] Shodan/Censys queried for org and known IP ranges
- [ ] Tech stack hypothesis documented per major asset
