# Domain & Infrastructure Research

Domain/IP OSINT reveals what services run at an address, who owns the infrastructure, historical changes, and related hosts—critical for attack-surface mapping and C2 hunting.

## Research Objectives

- **Subdomain discovery**: What subdomains exist under a target domain?
- **Service enumeration**: What ports/services are exposed (HTTP, SSH, databases)?
- **Historical tracking**: How has infrastructure changed over time?
- **Ownership mapping**: Who owns the IP blocks, hosting provider?
- **Related infrastructure**: Are other domains/IPs under the same owner?
- **C2 infrastructure**: For threat actors, build pivots from known C2 domains.

---

## Certificate Transparency (CT) Logs

### What They Are

CT logs are public append-only databases of all SSL/TLS certificates issued by trusted CAs. Every issued cert includes the domain name (Subject CN) and Subject Alternative Names (SANs).

### Tools

- **crt.sh** (crt.sh): Primary CT log search. Input domain → returns all certs issued for that domain + subdomains.
- **Censys Certificates** (search.censys.io/certificates): Similar; allows advanced filtering.
- **Rapid7 Open Data**: Regular snapshots of CT logs available for bulk analysis.

### Research Workflow

1. Input target domain (e.g., `example.com`).
2. Output: All subdomains with issued certs (e.g., `api.example.com`, `admin.example.com`, `dev.example.com`).
3. **Pivot**: For each subdomain, resolve to IP + check for hosted services (Shodan, Censys).
4. **Timing**: Certificate issuance date reveals when infrastructure was set up or rotated.
5. **Issuer/Serial reuse**: If organization uses same CA for multiple domains, can indicate related infrastructure.

---

## Passive DNS

Passive DNS aggregates historical DNS query logs. Query: domain name → returns all historical A/AAAA/CNAME/MX records + timestamps.

### Tools

- **SecurityTrails** (securitytrails.com): Comprehensive PDNS + host history. Input domain → returns IP history, nameserver changes, related domains.
- **DNSDB** (farsightsecurity.com/solutions/dnsdb/): Authoritative passive DNS; subscription required.
- **Rapid7 Sonar DNS data**: Free bulk DNS datasets (older snapshots, less real-time).
- **ZoneFiles Project**: Periodic zone file leaks (incomplete but valuable).

### Research Workflow

1. Input domain → PDNS.
2. Output: All IPs historically associated with that domain.
3. **For each IP**: Reverse DNS lookups → hostnames associated with that IP (can reveal other domains).
4. **Nameserver tracking**: Which nameservers has this domain used? Those nameservers may host other domains.
5. **Infrastructure transitions**: Multiple A-record changes suggest migration between hosting providers or load balancing.

---

## Host Enumeration (IP Lookups)

### Shodan & Censys

**Shodan** (shodan.io): Search engine for internet-connected devices. Query by IP/port/hostname/service/SSL certificate fingerprint.

- **Input**: IP address or hostname.
- **Output**: Ports, services, versions, banners, SSL certificate details, geolocation.
- **Filters**: Port-specific searches (`port:22`, `port:3306`), location (`country:US`), service fingerprints (`apache`, `nginx`).

**Censys** (search.censys.io): Similar to Shodan but with different data sources + advanced filtering.

- **Hosts tab**: Search IPs; returns open ports, services, certificates.
- **Certificates tab**: Certificate search; pivot on issuer, subject, serial number.
- **Services tab**: Service-specific searches.

### Complementary Tools

- **BinaryEdge** (binaryedge.io): Internet scanner; similar to Shodan but different dataset (fewer false positives in some regions).
- **FOFA** (fofa.so): Chinese cyberspace search engine; strong Asia-Pacific coverage.
- **ZoomEye** (zoomeye.org): Another Chinese search engine; different dataset.
- **Netlas** (netlas.io): Large-scale HTTP/DNS/certificate pivots.
- **LeakIX**: Search engine for exposed services + leaked credentials.
- **Censys (specific)**: Preferred for certificate analysis + historical records.

### Reverse IP Lookups

- **Reverse IP lookups**: Input IP → returns all domains ever hosted on that IP.
- **SecurityTrails**: Reverse IP tool shows domains historically on an IP.
- **MXToolbox** (mxtoolbox.com): Quick reverse IP + whois lookups.

---

## WHOIS & IP Ownership

### WHOIS Lookups

**Domain WHOIS** (registrant info):
- **whois.com** or **ICANN WHOIS lookup**: Returns registrant name, registrar, creation/expiry dates.
- **Privacy warnings**: Most domains now hide registrant via privacy/proxy services; look for reseller indicators.

**IP WHOIS** (ASN, netblock owner):
- **Hurricane Electric BGP Toolkit** (bgp.he.net): Input IP → returns ASN, netblock owner, hosting provider.
- **RIPE NCC RIPEstat** (stat.ripe.net): European IP + ASN data, geolocation, abuse contacts.
- **ARIN whois** (whois.arin.net): North American IP allocations.

### WHOIS History

- **WhoisXML API WHOIS History**: Historical WHOIS records for domain registration changes.
- **Domaintools** (domaintools.com): Domain history, registrant changes, parking history.

---

## ASN / BGP & Internet Measurement

### ASN Lookups

**Autonomous System Number (ASN)**: Each major IP block owner has an ASN. All IPs under one ASN are likely under same organizational control.

- **BGP Toolkit**: Input IP → ASN. Input ASN → all IP prefixes.
- **BGPView** (bgpview.io): ASN lookup, prefix explorer.
- **bgp.tools** (bgp.tools): Clean ASN/IX views, routing details.
- **RIPEstat**: IP/ASN history, routing, geolocation.

### Infrastructure Clustering

- **Find IP A under ASN X**.
- **Enumerate all prefixes under ASN X** → likely related infrastructure.
- **Check for infrastructure overlap**: If target company uses hosting provider Y, check what other domains also use provider Y (Shodan/Censys ASN filtering).

---

## Favicon & Page Fingerprinting

### Favicon Hash (mmh3)

- **Favicon**: Small image file served with web content.
- **mmh3 hash**: Standardized hash of favicon bits; identical favicons have same hash.
- **Use case**: Cluster infrastructure. If multiple IPs have identical favicon hash, likely same operator/organization.
- **Tools**: Shodan/Censys can filter by favicon hash.

### Page Fingerprinting

- **URLScan.io** (urlscan.io): On-demand webpage scan. Input URL → screenshot + resource map (scripts, images, domains loaded).
- **Visual similarity**: Multiple URLs with same page structure may be related infrastructure.

---

## SSL/TLS Certificate Analysis

### Certificate Reuse Pivots

- **Subject**: CN (Common Name) + SANs.
- **Issuer**: Certificate authority + issuer details.
- **Serial number**: Unique per certificate; sometimes reused patterns indicate related infrastructure.
- **Key reuse**: Same private key signing multiple certificates (rare but powerful pivot).

### Wildcard Certificates

- **`*.example.com`**: Single cert covers all subdomains. Suggests centralized infrastructure.
- **Pivot**: Find one subdomain → certificate likely covers others.

### Self-Signed Certificates

- **Fingerprint (SHA-1/SHA-256)**: Identical fingerprints across multiple hosts → same infrastructure.
- **Subject DN**: Names in the cert reveal infrastructure operators.

---

## DNS Enumeration

### Zone Transfers

- **DNS AXFR**: Attempt to request full zone transfer from authoritative nameserver (often denied, but worth trying).
- **Tools**: `dig axfr @ns.example.com example.com`, `nslookup`, `zonetransfer.me`.

### Subdomain Enumeration (Online)

- **Brute-force word lists**: Tools like **SubFinder**, **Amass** use wordlists + DNS to enumerate subdomains.
- **Online tools**: DnsRecon, fierce, sublist3r (all have OSINT-only modes).
- **Zone file leaks**: Occasionally zone files are publicly exposed (GitHub, pastebin).

### MX / SPF / TXT Records

- **MX records**: Mail server addresses (reveals email infrastructure).
- **SPF records**: Authorized mail senders (can reveal infrastructure provider names).
- **TXT records**: May contain DKIM keys, domain verification, third-party service indicators (e.g., Stripe, Slack).

---

## Hosting Provider & CDN Mapping

### Hosting Detection

- **IP geolocation**: Which data center? (MaxMind, IP2Location databases).
- **AS Organization**: Hosting provider name (from WHOIS).
- **Reverse DNS**: Often reveals hosting provider pattern (e.g., `*.example-hosting.com`).

### CDN Indicators

- **CNAME records**: May point to CDN (e.g., `*.cloudflare.net`, `*.akamai.net`).
- **TTLs**: Very short TTLs suggest dynamic infrastructure or load balancing.
- **Certificate issuer**: Rapid re-issuance suggests automated certificates (DDoS protection, WAF).

---

## Threat Actor Infrastructure Pivots

### C2 Infrastructure

- **Known C2 domain** → crt.sh (find subdomains, other infrastructure).
- **Known C2 IP** → Shodan/Censys (find other services on same IP).
- **Shared registrants** → WHOIS registrant name/email (find other domains under same registrant).
- **Nameserver reuse** → If threat actor uses custom NS for one domain, find other domains using same NS.
- **SSL certificate reuse** → Same certificate (issuer + serial) suggests same operator.

### Attribution via Infrastructure

- **Hosting provider choices**: Certain hosting providers favor certain threat actors (e.g., bulletproof hosts for ransomware).
- **Nameserver patterns**: Threat actors often reuse custom nameservers across multiple campaigns.
- **WHOIS contact info**: Sometimes registrant email/phone reveals other domains.

---

## Workflow: Domain to Infrastructure Map

1. **Start with domain** (e.g., `example.com`).
2. **Certificate Transparency** (crt.sh): Find all subdomains.
3. **Passive DNS** (SecurityTrails): Historical IPs for main domain + each subdomain.
4. **Resolve current**: `nslookup example.com` → get current IP.
5. **Shodan/Censys**: Search each IP → ports, services, versions.
6. **Reverse IP**: Find all domains hosted on each IP.
7. **ASN lookup**: Find IP → ASN; check if other domains under same ASN.
8. **WHOIS**: IP WHOIS → hosting provider + geolocation.
9. **Favicon hash**: Look for identical favicons across infrastructure.
10. **Archive**: Screenshots via archive.today, timestamps, WARC snapshots.
11. **Synthesis**: Network diagram (subdomains, IPs, services), provider map, historical changes.

---

## Anti-Patterns

- **Assuming single IP = single operator**: Shared hosting hosts 1000s of domains on one IP. Require additional pivots.
- **Ignoring CNAME aliases**: Reverse DNS may show CDN or provider, not the actual target.
- **Over-relying on reverse DNS**: Can be spoofed; validate with active checks (if in-scope).
- **Missing historical data**: Last week's IP matters; check PDNS history before concluding.
