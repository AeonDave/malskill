# Threat Actor Research

Threat actor OSINT maps infrastructure, capability profiles, and attribution for APTs, ransomware groups, and cybercriminals—purely via public sources.

## Research Objectives

- **Infrastructure mapping**: C2 domains, servers, registrants, resellers.
- **Capability profiling**: Exploits used, malware family, tactics (MITRE ATT&CK).
- **Attribution**: Which actor/country likely responsible?
- **Campaign tracking**: Timeline of attacks, victims, evolution.
- **Threat intelligence**: IOCs, malware signatures, detection methods.

---

## Infrastructure Pivoting

### C2 Domain → Related Infrastructure

1. **Known C2 domain** (e.g., `c2.evil.com`).
2. **Certificate Transparency** (crt.sh): Find all subdomains, SANs.
3. **Passive DNS** (SecurityTrails): Historical IPs for domain.
4. **Reverse IP**: Find all domains hosted on each IP.
5. **Whois/Registrant**: If registrant email/phone leaked, find other domains under same registrant.
6. **Nameserver reuse**: Threat actors often use custom nameservers; find other domains using same NS.
7. **ASN lookup**: IP → ASN; find other IPs in same ASN (suggests hosting provider preference).

### Infrastructure Clustering

- **Favicon hash**: Identical favicons across multiple sites → likely same operator.
- **SSL certificate reuse**: Same cert (issuer + serial) across domains → same operator.
- **Shared registrants**: WHOIS contact info (name, email, phone) reveals other domains.
- **Hosting provider patterns**: Threat actors favor certain bulletproof hosting providers.

---

## Malware & Artifact Analysis

### Static Analysis

- **Hashes**: SHA-256, MD5 of executable.
- **VirusTotal** (virustotal.com): Submit hash/file; see detections, metadata, YARA hits.
- **Malpedia** (malpedia.caad.fkie.fraunhofer.de): Malware family classification, references, YARA rules.
- **Strings**: Executable strings (APIs, URLs, config paths) reveal behavior.
- **PE metadata**: Import tables, PDB paths (compiler artifacts), resources, embedded data.
- **Rich header**: Compile timestamp, toolchain info.

### Sandbox Execution

- **ANY.RUN** (any.run): Sandboxed malware execution; behavioral analysis.
- **Hybrid Analysis** (hybrid-analysis.com): Similar; powered by Falcon Sandbox.
- **CAPE** (capesandbox.com): Open-source sandbox.
- **Tria.ge** (tria.ge): Quick sandbox; integrates with other platforms.
- **Output**: Network IOCs (C2, DNS requests), file drops, mutexes, registry changes.

### Clustering & Similarity

- **SSDEEP, TLSH**: Fuzzy hash algorithms; find similar samples.
- **YARA**: Pattern matching; search for samples with specific code/strings.
- **Intezer** (analyze.intezer.com): Code-reuse analysis; find related samples.

---

## Attribution Discipline

### Separate Capability from Intent

- **Capability**: What can this actor do? (Exploit development, RAT usage, lateral movement).
- **Intent**: Why are they doing this? (Financial, espionage, political).
- **Sponsorship**: Which country/organization backs them?
- **Danger**: Confusing these leads to false attribution.

### Rule-of-Three

- Require at least **three independent weak signals** OR **one strong + one weak** signal before asserting linkage.
- **Weak signal**: Shared hosting provider, use of common tool (Cobalt Strike).
- **Strong signal**: Unique code-signing cert, custom malware family, registrar account reuse.

### Durable Pivots (Prefer These)

- **Code-signing certificates**: Expensive; reuse suggests same organization.
- **Registrar accounts**: More stable than individual domains; pattern of domains under same registrant.
- **PDB paths**: Embedded compiler paths (e.g., `C:\Users\Admin\Projects\malware.pdb`) are hard to fake.
- **Malware family**: Custom packers, encryption routines specific to one actor.

### Ephemeral Pivots (Weak)

- **IP addresses**: Shared hosting; many domains on one IP.
- **Timestamps**: Can be spoofed; timezone hints are probabilistic.
- **Tool usage**: Cobalt Strike is used by many groups; not unique.

---

## Actor-Centric Workflow

### Phase 1: Scoping

- Define the actor (e.g., APT28, Wizard Spider, Fancy Bear).
- Collect seed reports from CERTs, vendors, threat intel feeds.

### Phase 2: Indicator Harvesting

- Parse IOCs (domains, IPs, hashes, JA3/JA4 fingerprints, user-agents) from advisories.
- Validate against passive DNS, CT logs, sandbox submissions.

### Phase 3: Infrastructure Mapping

- Build pivots from CT logs (SANs, issuer patterns).
- Shared hosting, nameserver reuse, registrar account clustering.
- Enrich with ASN/WHOIS history, geolocation, hosting provider.

### Phase 4: Artifact Profiling

- Extract PE/ELF metadata (PDB paths, compile timestamps, Rich headers).
- Cluster via fuzzy hashes (SSDEEP, TLSH); identify packers/loaders.
- Search YARA, sandboxes for near-matches.

### Phase 5: Social & Procurement Pivots

- Developer handles, code snippets, academic theses → capability hints.
- Job posts, procurement records → organizational mandate.
- Coding style, variable names → fingerprinting.

### Phase 6: Attribution & Reporting

- Weigh each linkage (weak/medium/strong).
- Document alternatives (what other actors might explain these IOCs?).
- Map TTPs to MITRE ATT&CK.
- Cite sources with exact sections/pages.
- **Confidence levels**: Low/medium/high.

---

## Tools & Data Sources

### Threat Intelligence Feeds

- **Vendor advisories**: CISA, NSA, CSA joint advisories; CERT-EU, NCSC-UK, JPCERT/CC, CERT-UA.
- **MISP Project** & **OpenCTI**: Structured threat intelligence; community feeds.
- **VirusTotal**: File/URL/IP/domain reputation; community contributions.

### Malware Databases

- **MalwareBazaar** (bazaar.abuse.ch): Hash-based sample sharing.
- **URLHaus** (urlhaus.abuse.ch): Malicious URLs.
- **PhishTank** (phishtank.com): Phishing URLs.

### IOC Intelligence

- **ThreatFox** (threatfox.abuse.ch): Malware C2 IOCs.
- **AlienVault OTX**: Community threat intelligence.

### TLS Fingerprints

- **JA3** (salesforce/ja3): TLS client fingerprints; identifies malware families.
- **JA4** (FingerprinTLS/ja4): Improved fingerprinting.
- **Shodan/Censys**: Search by JA3 hash → find related servers.

---

## Workflow: Attribute an APT Campaign

1. **Incident seed**: Known attack, domain, malware sample.
2. **Indicator extraction**: Hashes, domains, IPs, tool signatures.
3. **VirusTotal/Sandbox**: Upload sample; note detections, behavior.
4. **CT logs + PDNS**: Expand infrastructure map.
5. **Reverse IP**: Find related domains.
6. **Registrant research**: WHOIS registrant email/phone → other domains.
7. **Code analysis**: Unique strings, PDB paths, compile timestamps → actor fingerprints.
8. **MISP/CTI feeds**: Compare against known APT campaigns.
9. **TTPs**: Map to MITRE ATT&CK; compare with known actor playbooks.
10. **Social/procurement**: GitHub handles, job posts, academic papers → capability hints.
11. **Attribution assertion**: Require rule-of-three; document confidence + alternatives.
12. **Report**: IOC list, infrastructure map, TTPs, confidence, citations.

---

## Anti-Patterns

- **Over-confident attribution**: Shared tools/infrastructure can be copied; require multiple independent signals.
- **Ignoring false flags**: Threat actors intentionally plant false evidence.
- **Assuming unique = rare**: PDB paths can be standard project layouts; compile timestamps are often machine-local.
- **Timestomping assumption**: Metadata can be changed; validate with behavioral analysis.
- **Single report = truth**: Vendor reports vary; corroborate with alternative sources.
