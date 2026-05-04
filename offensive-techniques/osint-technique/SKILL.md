---
name: osint-technique
description: "Open-source intelligence (OSINT) methodology bridging systematic research workflow with online tool discovery and API leverage. Covers target definition, source prioritization, online research across people/identity, infrastructure, breach data, geospatial/media analysis, and threat actor tracking. Use when conducting reconnaissance against a target person/organization/domain/infrastructure, investigating breach impacts, tracing cryptocurrency flows, geolocating events, or mapping an attack surface using only public online sources. Methodology-first: what to research first, which online sources answer that question, and how to synthesize findings rather than tool recipes."
license: MIT
compatibility: "Online research; any OS with browser. No live network scanning — passive sources only."
metadata:
  author: AeonDave
  version: "1.1"
  category: offensive-techniques
---

# OSINT Technique

Open-source intelligence (OSINT) is the systematic collection, analysis, and synthesis of information from publicly available online sources. Unlike traditional recon tools (Nmap, Shodan downloads), OSINT emphasizes **research methodology** and **online tool leverage** (APIs, web interfaces, databases) to build comprehensive intelligence on a target—person, organization, domain, infrastructure, or event.

## Core OSINT Loop

OSINT campaigns follow a iterative research lifecycle:

1. **Define Scope**: Target type (person, company, domain, IP, event), research objectives (profile, risk assessment, attribution, incident response), constraints (OpSec, legal/compliance, timeline).
2. **Prioritize Sources**: Which online sources are most likely to yield evidence? (e.g., certificate transparency for domain history; LinkedIn/breaches for employee intel; blockchain explorers for crypto flows).
3. **Collect & Correlate**: Systematic querying across online tools and APIs; cross-reference findings to validate and pivot.
4. **Synthesis & Reporting**: Map relationships (person ↔ domain ↔ infrastructure ↔ breach), document confidence levels, distinguish correlation from control.
5. **Iterate**: Each discovery may spawn new research threads (e.g., find email → breach database lookups → person research → infrastructure pivots).

---

## Agent Operating Model

When this technique is active:

1. **Interpret the research objective**: Is the user investigating a person, organization, infrastructure, event, or threat actor? What are they trying to learn?
2. **Map to OSINT domains**: Person/identity → social media, breaches, email search, people-search APIs. Company → registries, employee records, leaked documents, compliance filings. Infrastructure → Certificate Transparency, DNS history, host enumeration APIs (Shodan, Censys). Breach → leak databases, dark web monitoring. Threat actor → infrastructure pivots, artifact profiling, attribution discipline.
3. **Select online tools & APIs**: Not all tools apply to every domain. Shodan searches infrastructure; Hunter.io finds emails; crt.sh tracks certificate history; breach databases index leaked credentials. Prefer APIs and web interfaces over downloadable tools (offensive-tools/osint/ handles tool manuals).
4. **Execute research systematically**: Follow the OSINT Lifecycle. Document each step: tool used, query, timestamp, findings. Archive evidence (screenshots, URLs, timestamps, SHA-256 hashes).
5. **Validate & synthesize**: Cross-check findings with independent sources. Separate weak signals (timing coincidence) from strong signals (account name + email + domain registration). Map relationships visually if possible.
6. **Report with confidence levels**: Mark low/medium/high confidence for each assertion. Distinguish *correlation* (two things co-occur) from *control* (one caused the other).

---

## Required Deliverables

An OSINT campaign targeting a specific scope should produce:

1. **Scoped Research Plan**: Target type, objectives, timeline, OpSec constraints, relevant online domains.
2. **Collected Evidence**: Artifact log (timestamp, source, URL, query, result, hash if file). JSONL or structured format for reproducibility.
3. **Correlation Map**: Relationships discovered (person ↔ email ↔ domain, company ↔ employees ↔ infrastructure, wallet ↔ exchanges). Can be graph, spreadsheet, or narrative.
4. **Synthesis Report**: Findings structured by domain (who, what, where, when, why). Confidence levels per assertion. Key pivots highlighted. Unknown gaps noted.
5. **Operational Notes**: Tools/APIs used, search parameters, any rate-limiting or access restrictions encountered. Reproducibility data (tool versions, dates).

---

## Case-Based OSINT Selection

Different target types benefit from different online tool families and research priorities:

### A. Person or Identity Investigation
**Trigger**: Name, email, username, phone, document ID, face image.
**Online sources first**: Social media (X/Twitter, LinkedIn, Instagram, GitHub), people-search APIs, email-verification services, username enumeration, breach databases, image reversal (faces/document scans).
**Key tools**: Sherlock/Maigret (username search), Hunter.io/Epieos (email pivot), Holehe (email → platforms), PimEyes/FaceCheck (face search), breach databases (Have I Been Pwned, Dehashed, IntelX), OSINT Framework (resource directory).
**Output**: Profile timeline, email-domain associations, breach exposure, social connections.

### B. Organization / Company Research
**Trigger**: Company name, domain, country, sector.
**Online sources first**: Business registries (OpenCorporates, SEC EDGAR, regional databases), employee records (LinkedIn, job boards), leaked documents (OCCRP Aleph, breaches), procurement records (EU TED, country-specific), domain registration (WHOIS, Domaintools).
**Key tools**: OpenCorporates (company filings), WHOIS/WHOIS history, LinkedIn (workforce), breach databases, Google dorking (site-specific searches), tech-stack detection (BuiltWith), domain history (SecurityTrails PDNS).
**Output**: Org structure, key personnel, financial health, infrastructure footprint, risk indicators.

### C. Infrastructure / Domain / IP Research
**Trigger**: Domain name, IP address, CIDR block, ASN, hosting provider.
**Online sources first**: Certificate Transparency logs (domain/subdomain history), passive DNS (historical A/AAAA/CNAME records), host enumeration (IP associations, services), BGP/ASN data (ownership, peering), SSL/TLS fingerprints (host clustering).
**Key tools**: crt.sh (Certificate Transparency), SecurityTrails (PDNS + host history), Shodan/Censys (host enumeration), WHOIS APIs, passive DNS aggregators (DNSDB, Farsight), BGP Toolkit, URLScan (page snapshots + fingerprints).
**CLI tool families**: `offensive-tools/recon/subfinder/` (subdomain enumeration), `offensive-tools/recon/dnsx/` (DNS resolution + filtering), `offensive-tools/recon/shodan/` (Shodan API queries), `offensive-tools/recon/httpx/` (HTTP probing at scale).
**Output**: Subdomain list, service/version inventory, owner history, related infrastructure, tech stack.

### D. Breach & Credential Research
**Trigger**: Email, domain, username, phone (checking for exposure).
**Online sources first**: Breach aggregators, dark web search, credential stuffing detection, infostealer dumps, OSINT database indices.
**Key tools**: Have I Been Pwned (breach search), Dehashed (credential search), LeakCheck (breach aggregator), IntelX (dark web index), Epieos (email metadata), breach monitoring services.
**Output**: Breach timeline, exposed credentials, infostealer overlap, attack surface severity.

### E. Geospatial & Media Analysis
**Trigger**: Image, video, location description, event timeline.
**Online sources first**: Reverse image search (Google Lens, TinEye, Yandex), geolocation databases (Mapillary, KartaView, Google Earth), satellite imagery (Sentinel Hub, NASA Worldview), shadow/sun calculators (geolocation via shadows), social media check-ins (Snap Map, Swarm history).
**Key tools**: Google Lens, TinEye, Yandex Images, SunCalc (shadow analysis), Mapillary (street-level imagery), Sentinel Hub (historical satellite), Overpass Turbo (OSM queries), FlightRadar24 (aircraft tracking).
**Output**: Location confirmation, timeline, related events/witnesses, geolocation precision.

### F. Threat Actor / Malware Investigation
**Trigger**: Command & control domain, malware hash, exploit code, actor alias.
**Online sources first**: Passive DNS history (C2 domain pivots), certificate reuse (infrastructure clustering), artifact databases (Malpedia, MalwareBazaar), social/procurement pivots (job posts, academic publications, procurement records), code repositories (GitHub, pastebin).
**Key tools**: crt.sh + passive DNS (C2 history), SecurityTrails (PDNS pivots), Malpedia (malware classification), VirusTotal (hash associations), GitHub search (code/credentials), academic databases, job boards (hiring requirements suggest capability).
**Output**: Infrastructure map, capability profile, likely affiliation, TTPs (MITRE ATT&CK), confidence assertions.

### G. Phishing / Brand-Abuse Infrastructure
**Trigger**: Brand, domain, certificate, URL, phishing kit, suspicious login portal.
**Online sources first**: Certificate Transparency, passive DNS, URLScan, WHOIS/RDAP, hosting intelligence, page screenshots.
**Key questions**: Is this a lookalike? Is content live? Does it reuse infrastructure, certificates, kits, or payment artifacts? What confidence supports any linkage?
**Output**: Candidate domain list, enrichment table, archived pages, risk priority, and attribution confidence.

### H. Ransomware Payment Tracking
**Trigger**: Wallet address, ransom note, payment screenshot, blockchain transaction, negotiation portal.
**Online sources first**: Chain explorers, public labels, exchange/mixer/bridge tags, threat-intel wallet reports, transaction graphing tools.
**Key questions**: Did payment occur? Where did funds move next? Are there service touchpoints or clusters? Where does traceability stop?
**Output**: Transaction graph, cluster rationale, cash-out hypotheses, confidence and limitations.

---

## Quality Gates

Before concluding an OSINT investigation:

1. **Pivot Rule-of-Three**: Require at least three independent weak signals, or one strong + one weak, before asserting a link.
2. **Durable vs. Ephemeral Pivots**: Prefer registrar account reuse, code-signing certs, PDB paths (durable) over IP addresses (ephemeral, often shared hosting).
3. **Source Independence**: Cross-check with alternative tools/sources. Avoid single-source attribution.
4. **Confidence Labeling**: Mark each finding low/medium/high; document reasoning.
5. **Archive Everything**: Timestamp, URL, screenshot/WARC archive, SHA-256 hash of downloads. Enable reproducibility.
6. **Legal/OpSec Check**: Ensure queries comply with terms of service and local law. Use separate identities (sock puppets) where appropriate. Do not access honeypots or unauthorized systems.

---

## Anti-Patterns

Avoid:

- **Tool Substitution for Methodology**: Running Shodan on every domain without asking "what am I looking for?" Research objective drives tool choice, not the reverse.
- **Single-Source Attribution**: One coincidence (same email on two sites) is not proof of control; gather independent evidence.
- **Overwhelming Data Hoarding**: Collect with intent. Document *why* each artifact matters to your research objective. Too much noise drowns the signal.
- **Ignoring OpSec**: Revealing your investigation via identifiable searches, account re-use, or rate-limited API calls. Use personas, rotate identities, stagger queries.
- **Stale Tool Assumptions**: OSINT tools evolve (APIs change, free tiers vanish, authentication gates new features). Verify tool status before relying on it for critical pivots.
- **Confusing Correlation with Control**: Two events at the same time do not prove causation. Weigh timing against independent evidence.

---

## Integration with tool skills

This technique focuses on *methodology + online research*. Specific tool usage lives in:

**OSINT tools** (`offensive-tools/osint/`):
- `amass/` — active DNS enumeration + passive collection
- `ghunt/` — Google account reverse-engineering
- `holehe/` — email-to-platform enumeration
- `maigret/` — username aggregation across platforms
- `phoneinfoga/` — phone number intelligence
- `sherlock/` — username search
- `spiderfoot/` — automated multi-source OSINT collection
- `theharvester/` — email + subdomain harvesting

**Recon tools** (`offensive-tools/recon/`):
- `subfinder/` — passive subdomain enumeration
- `dnsx/` — DNS resolution and filtering at scale
- `gau/` — historical URL discovery from Wayback, Common Crawl, and URLScan sources
- `shodan/` — Shodan CLI and API queries
- `httpx/` — HTTP probing, title/tech detection

Reference tool `SKILL.md` files for flags and workflows; use this technique for research strategy and source selection.

---

## References

- [person-and-identity-research.md](references/person-and-identity-research.md) — Email pivots, social media profiling, people-search APIs, facial search, username enumeration.
- [company-and-organization-research.md](references/company-and-organization-research.md) — Registries, employee records, financial filings, leaked documents, compliance checks.
- [domain-and-infrastructure-research.md](references/domain-and-infrastructure-research.md) — Certificate Transparency, passive DNS, host enumeration, BGP/ASN, service discovery.
- [breach-and-leak-research.md](references/breach-and-leak-research.md) — Breach aggregators, credential search, infostealer databases, dark web indices.
- [image-and-geospatial-osint.md](references/image-and-geospatial-osint.md) — Reverse image search, geolocation techniques, EXIF analysis, satellite imagery, chronolocation.
- [social-media-profiling.md](references/social-media-profiling.md) — Platform-specific techniques (X, LinkedIn, Instagram, Telegram, Mastodon, Bluesky), check-in data, content archives.
- [threat-actor-research.md](references/threat-actor-research.md) — Infrastructure pivoting, artifact profiling, attribution discipline, MITRE ATT&CK mapping.
- [ct-phishing-and-attribution.md](references/ct-phishing-and-attribution.md) — CT monitoring for lookalikes, phishing infrastructure enrichment, and cautious attribution methodology.
- [ransomware-payment-tracking.md](references/ransomware-payment-tracking.md) — Cryptocurrency flow tracking, service/mixer/bridge identification, cluster confidence, and traceability limits.
- [operational-security-and-evidence.md](references/operational-security-and-evidence.md) — Sock puppets, browser isolation, evidence archival, chain of custody, reproducibility logging.
- [online-tools-and-apis-navigator.md](references/online-tools-and-apis-navigator.md) — Directory of online OSINT tools/APIs by domain (no downloads). Updated regularly via Tavily research.
