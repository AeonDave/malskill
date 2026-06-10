# Threat Intel Sources & Vulnerability Prioritization

Load when you need threat-intel feeds, bulk CVE prioritization, or disclosed-report mining.

---

## 1. Primary feeds

| Source | URL | Use |
|---|---|---|
| CISA / NSA joint advisories | https://www.cisa.gov/news-events/cybersecurity-advisories | State-actor + critical infra TI |
| CERT-EU, NCSC-UK, JPCERT/CC, CERT-UA | various | Regional TI |
| MISP feeds | https://www.misp-project.org/ | Pivot-ready IOC sharing |
| OpenCTI | https://www.opencti.io/ | CTI knowledge graph |
| Malpedia | https://malpedia.caad.fkie.fraunhofer.de/ | Family YARA + refs |
| ThreatFox | https://threatfox.abuse.ch/ | C2 IOCs |
| URLHaus | https://urlhaus.abuse.ch/ | Live malware URLs |
| SSLBL | https://sslbl.abuse.ch/ | Malicious TLS certs / JA3 |
| MalwareBazaar | https://bazaar.abuse.ch/ | Hash-based samples |
| PhishTank, OpenPhish | https://www.phishtank.com/, https://openphish.com/ | Phishing URLs |

## 2. Sandboxes & sample triage

- Static: `pefile`, `FLOSS`, `capa`.
- Similarity: SSDEEP, TLSH (cluster variants).
- Sandboxes: ANY.RUN, Hybrid Analysis, CAPE, Tria.ge.
- Intelligence: Intezer (code reuse), VirusTotal.
- TLS fingerprints: JA3 (legacy), JA4 (current).

**VirusTotal caution:** uploads become public + searchable. Never upload sensitive client artifacts. Use VT Enterprise private retrohunt or local YARA instead.

---

## 3. Vulnerability prioritization sources

| Source | URL | Signal |
|---|---|---|
| NVD | https://services.nvd.nist.gov/rest/json/cves/2.0 | CVE catalog + CVSS v2/v3 |
| EPSS | https://api.first.org/data/v1/epss / CSV: https://epss.cyentia.com/epss_scores-current.csv.gz | 0.0-1.0 prob exploit in 30 days, daily update |
| CISA KEV | https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json | Proven exploited + federal due dates |
| Vulncheck KEV | https://vulncheck.com/kev | Expanded KEV (more than CISA) |
| ExploitDB | https://www.exploit-db.com/, offline `searchsploit` | Public PoC code |
| Metasploit | `msfconsole -q -x "search cve:CVE-...; exit"` | Automation availability |
| Trickest CVE→PoC | https://github.com/trickest/cve | Auto-mapped CVE → public repos |
| InTheWild.io | https://inthewild.io/ | Community ITW tracker |
| OpenCVE | https://www.opencve.io/ | Timeline + watchlist + alerts |
| GitHub Security Advisories | https://github.com/advisories | Ecosystem-scoped |
| OSV.dev | https://osv.dev/ | Open-source DB, JSON API |
| Tenable Research | https://www.tenable.com/research | Vendor enrichment |
| Qualys ThreatPROTECT | https://threatprotect.qualys.com/ | Vendor enrichment |

### 3.1 Per-CVE lookup
```bash
CVE="CVE-2024-3400"
# EPSS
curl -sk "https://api.first.org/data/v1/epss?cve=$CVE" | jq '.data[0]'
# KEV
curl -sk https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json | \
  jq --arg c "$CVE" '.vulnerabilities[] | select(.cveID == $c)'
# ExploitDB
searchsploit cve $CVE
# Metasploit
msfconsole -q -x "search cve:$CVE; exit"
```

### 3.2 Bulk prioritization (from nuclei output)
```bash
jq -r '.info.classification.["cve-id"][]?' nuclei.json | sort -u > cves.txt

KEV_JSON=$(curl -sk https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json)

while IFS= read -r CVE; do
  EPSS=$(curl -sk "https://api.first.org/data/v1/epss?cve=$CVE" | jq -r '.data[0].epss // "N/A"')
  KEV=$(echo "$KEV_JSON" | jq -r --arg c "$CVE" '.vulnerabilities[] | select(.cveID == $c) | "KEV"' | head -1)
  printf "%s | EPSS:%s | %s\n" "$CVE" "$EPSS" "${KEV:-}"
done < cves.txt | sort -t: -k2 -nr
```

### 3.3 Prioritization heuristic
1. **KEV-flagged** → patch first regardless of score.
2. **EPSS ≥ 0.5** → high near-term exploit probability.
3. **CVSS ≥ 9.0 + public PoC (Trickest/ExploitDB/Metasploit)** → operator-ready exploit, escalate.
4. **EPSS 0.1–0.5 + targetable from internet** → MEDIUM-HIGH.
5. **Internal-only + no PoC + CVSS < 7** → noise; defer.

Cache CSV daily for offline ops:
```bash
curl -sk -o /tmp/epss-$(date +%F).csv.gz https://epss.cyentia.com/epss_scores-current.csv.gz
gunzip -f /tmp/epss-$(date +%F).csv.gz
```

---

## 4. HackerOne disclosed reports — `scripts/h1_reference.py`

Pull community-validated findings as reference. No API key, public GraphQL.

### 4.1 Modes
```bash
# Top voted — validated techniques baseline
python3 scripts/h1_reference.py --top-voted --limit 25

# Top bounty — business-impact framing
python3 scripts/h1_reference.py --top-bounty --limit 10

# Keyword search across pages (50 results/page hard cap)
python3 scripts/h1_reference.py --top-voted --query "SSRF" --pages 10
python3 scripts/h1_reference.py --top-voted --query "auth bypass|OAuth|OIDC" --pages 5
python3 scripts/h1_reference.py --top-voted --query "open redirect" --pages 5

# Severity filter (client-side)
python3 scripts/h1_reference.py --top-bounty --severity critical high --pages 3

# Program-specific
python3 scripts/h1_reference.py --program gitlab --pages 5
python3 scripts/h1_reference.py --lookup-program gitlab    # handle → team ID

# JSON for piping
python3 scripts/h1_reference.py --top-voted --query "XSS" --pages 5 --json | jq '.[].report.url'
```

### 4.2 When to run
- Session start: `--top-voted` for high-signal baseline.
- After tech-stack identified: `--query "<tech>" --pages 10`.
- Before probing a class: `--query "SSRF|XXE|SSTI" --pages 5`.
- Report writing: `--query "<vuln>" --top-bounty` for severity/bounty comparables.

### 4.3 H1 GraphQL quirks (handled by the script)
- Hard 50 results/page regardless of `first:` value — use `--pages` for breadth.
- `disclosed_at` field crashes when combined with substate filter — omitted.
- Sort + substate filter combo crashes — script auto-routes around.

---

## 5. Hard rules
- VirusTotal uploads are public — never upload client material.
- Cache KEV + EPSS daily for repeatable triage.
- Disclosed reports = inspiration, not vuln confirmation against target.
- Always cross-check vendor advisory before claiming CVE applicability.
