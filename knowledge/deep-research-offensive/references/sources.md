# Security Intelligence Sources

Curated reference for offensive security research. Load this file when needing to identify where to search for CVE data, exploit code, threat intelligence, or OSINT.

## Table of Contents

- [Vulnerability Databases](#vulnerability-databases)
- [Exploit Repositories](#exploit-repositories)
- [Threat Intelligence Feeds](#threat-intelligence-feeds)
- [OSINT and Reconnaissance](#osint-and-reconnaissance)
- [Vendor Advisory Feeds](#vendor-advisory-feeds)
- [MCP Search Patterns](#mcp-search-patterns)

---

## Vulnerability Databases

| Source | URL | Best for | Notes |
|---|---|---|---|
| NVD (NIST) | nvd.nist.gov | CVSS scores, affected versions, references | Enrichment backlog since Feb 2024; pre-2018 CVEs marked Deferred (Apr 2025) — cross-check cve.org |
| CVE Program | cve.org | CVE descriptions, CNA attribution | Canonical; often more current than NVD for new CVEs |
| CISA KEV | cisa.gov/known-exploited-vulnerabilities-catalog | Actively exploited CVEs | Filter by date; download CSV for bulk |
| OSV.dev | osv.dev | Open source library vulns | JSON API available; good for deps |
| Vulncheck | vulncheck.com/nvd-mirror | NVD mirror + exploit intel | Better exploit track than raw NVD |

## Exploit Repositories

| Source | URL | Best for | Caveats |
|---|---|---|---|
| Exploit-DB | exploit-db.com | Verified PoC, shellcodes, papers | Highly credible; searchable by CVE |
| Sploitus | sploitus.com | Aggregator across exploit sources | Good for new CVEs not yet in ExploitDB |
| PacketStorm | packetstormsecurity.com | Exploits, tools, advisories | Broad; quality varies |
| GitHub Search | github.com/search | PoC repos, patch diffs | Search: `CVE-YYYY-NNNNN exploit` |
| poc-in-github | poc-in-github.motikan2010.net | GitHub PoC index by CVE ID | API: `/api/v1/?cve_id=CVE-YYYY-NNNNN` |
| Nuclei Templates | github.com/projectdiscovery/nuclei-templates | Detection templates | Check `cves/` folder |
| Metasploit Modules | github.com/rapid7/metasploit-framework | Weaponized modules | Filter `modules/exploits/` |

## Threat Intelligence Feeds

| Source | URL | Best for |
|---|---|---|
| CISA Advisories | cisa.gov/news-events/cybersecurity-advisories | US critical infra threats |
| US-CERT | cisa.gov/uscert/ncas/alerts | Alert-level threat intel |
| Recorded Future Blog | recordedfuture.com/research | APT and ransomware TTPs |
| Mandiant | mandiant.com/resources/insights | Advanced threat reporting |
| Krebs on Security | krebsonsecurity.com | Breaking vuln/exploit news |
| Bleeping Computer | bleepingcomputer.com | Rapid disclosure, ransomware tracking |
| The Hacker News | thehackernews.com | Aggregated security news |

## OSINT and Reconnaissance

| Tool/Source | MCP Tool | Use |
|---|---|---|
| Shodan | shodan.io (scrape via Playwright) | Exposed services, banner grabbing |
| Censys | search.censys.io | Alternative to Shodan; better cert data |
| FOFA | fofa.info | Chinese asset discovery, ICS/SCADA focus |
| GreyNoise | viz.greynoise.io | Internet noise vs targeted scanning |
| VirusTotal | virustotal.com | File/URL/IP reputation, relations |
| URLScan | urlscan.io | JS-rendered page recon |
| WHOIS / ASN | bgp.he.net | ASN, netblock, org ownership |
| Hunter.io | hunter.io | Email recon for orgs |
| Wayback Machine | web.archive.org | Historical content, removed pages |

## Vendor Advisory Feeds

Search pattern: `[vendor] security advisory [year]`

| Vendor | Advisory URL |
|---|---|
| Microsoft | msrc.microsoft.com/update-guide |
| Apple | support.apple.com/en-us/100100 |
| Cisco | sec.cloudapps.cisco.com/security/center/publicationListing.x |
| VMware | support.broadcom.com/web/ecx/security-advisories |
| Fortinet | fortiguard.com/psirt |
| Palo Alto | security.paloaltonetworks.com |
| Red Hat | access.redhat.com/security/updates/advisory |
| Debian | www.debian.org/security/ |
| Ubuntu | ubuntu.com/security/notices |
| F5 | support.f5.com/csp/article/K00000 |
