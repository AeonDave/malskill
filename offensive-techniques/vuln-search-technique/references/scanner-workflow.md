# Scanner Workflow — Orchestration and Interpretation

Layered scanning workflow: broad automated coverage → targeted tech-specific probes → manual gap fill.

---

## Layer 1 — Nuclei (primary automated scanner)

Nuclei is template-driven and covers CVEs, misconfigs, exposures, and tech-specific patterns. Run first on all web-accessible targets.

### Template selection by phase

```bash
# Phase A — fast initial sweep (high/critical only)
nuclei -u https://target.com -severity critical,high -o phase_a.txt

# Phase B — exposure and misconfiguration
nuclei -u https://target.com -t exposures/ -t misconfigurations/ -o phase_b.txt

# Phase C — CVE-specific sweep
nuclei -u https://target.com -t cves/ -o phase_c.txt

# Phase D — technology detection + version-specific
nuclei -u https://target.com -t technologies/ -t vulnerabilities/ -o phase_d.txt

# Full scan (slower — use when time permits)
nuclei -u https://target.com -o full_scan.txt
```

### Bulk scan from recon output

```bash
# Scan list of live web hosts
nuclei -list live_web.txt -severity critical,high -o bulk_high.txt

# Technology-matched scans
# After httpx detects PHP hosts:
cat httpx.json | jq -r 'select(.tech[]? | test("PHP")) | .url' > php_hosts.txt
nuclei -list php_hosts.txt -t cves/php/ -t technologies/php/ -o php_cves.txt

# WordPress hosts → wpscan + nuclei wordpress templates
cat httpx.json | jq -r 'select(.tech[]? | test("WordPress")) | .url' > wp_hosts.txt
nuclei -list wp_hosts.txt -t cves/wordpress/ -t vulnerabilities/wordpress/ -o wp_cves.txt
```

### Interpreting nuclei output

| Severity | Field | Action |
|----------|-------|--------|
| critical | `[critical]` | Manual verify immediately, escalate to exploit |
| high | `[high]` | Manual verify, queue for exploit |
| medium | `[medium]` | Verify, document, lower priority |
| info | `[info]` | Fingerprint data — no direct exploit path |

**Always manually verify nuclei findings** — false positives occur on:
- CVE templates that match version string without confirming behavior
- Exposure templates that detect path without checking actual content
- Header-based checks that infer version from headers

Manual verification: replicate the HTTP request shown in nuclei output. Confirm the response matches the expected vulnerable indicator.

### Custom template writing (when no template exists)

```yaml
# Minimal nuclei template structure
id: custom-TARGETNAME-vuln-YYYYMMDD
info:
  name: "Custom — TargetName Vulnerability Description"
  author: yourhandle
  severity: high
  tags: custom,web

requests:
  - method: GET
    path:
      - "{{BaseURL}}/vulnerable/endpoint"
    matchers:
      - type: word
        words:
          - "vulnerable_response_indicator"
        part: body
```

---

## Layer 2 — Nikto (web server config audit)

Nikto covers server-level issues nuclei templates don't: dangerous HTTP methods, security headers, legacy content, default files.

### Standard run

```bash
# Basic scan
nikto -h https://target.com -o nikto_out.txt -Format txt

# Include all plugins
nikto -h https://target.com -Plugins @@ALL -o nikto_full.txt

# Specific port
nikto -h target.com -p 8080 -ssl

# Tuning: limit to specific check types
# 0=File Upload 1=Interesting File 2=Misconfiguration 3=Info Disclosure
# 4=Injection 5=Remote File Retrieval 6=Denial of Service 7=Remote Shell
nikto -h https://target.com -Tuning 1,2,3,5
```

### Key nikto findings to action

| Finding | Priority | What it means |
|---------|----------|--------------|
| `TRACE method enabled` | Medium | XST attack possible; test with `curl -X TRACE` |
| `PUT method allowed` | High | Potential file upload to server |
| `Missing X-Frame-Options` | Low | Clickjacking possible |
| `Missing Content-Security-Policy` | Low-Medium | XSS mitigation absent |
| `Server: Apache/2.4.49` old version | High | CVE lookup immediately |
| `phpinfo.php found` | High | Full server info exposure |
| `/.git/HEAD found` | Critical | Source code accessible |
| `Default content: /manager/html` | High | Tomcat manager default path |

---

## Layer 3 — Nmap NSE scripts

Run after port sweep, targeted to confirmed open ports.

### Script categories and use

```bash
# Run by category
nmap --script auth -p <port> target          # default credentials
nmap --script default -p <port> target       # standard enum scripts
nmap --script vuln -p <port> target          # vulnerability checks (noisy)
nmap --script discovery -p <port> target     # service discovery

# Run all in category (risky — may trigger IDS)
nmap --script "http-*" -p 80,443 target
```

### Per-service NSE script reference

**HTTP / HTTPS**
```bash
nmap --script http-title,http-server-header,http-methods -p 80,443 target
nmap --script http-auth-finder -p 80,443 target
nmap --script http-vuln-cve2017-5638 -p 80 target      # Apache Struts RCE
nmap --script http-vuln-cve2021-41773 -p 80,443 target # Apache path traversal
nmap --script http-shellshock -p 80,443 target         # CGI Shellshock
nmap --script http-git -p 80,443 target                # exposed .git
```

**SMB**
```bash
nmap --script smb-vuln-ms17-010 -p 445 target          # EternalBlue
nmap --script smb-vuln-cve-2017-7494 -p 445 target     # SambaCry
nmap --script smb-enum-shares,smb-os-discovery -p 445 target
nmap --script smb2-security-mode -p 445 target
```

**SSH**
```bash
nmap --script ssh-auth-methods -p 22 target
nmap --script ssh-vuln-cve2018-10933 -p 22 target      # libssh auth bypass
nmap --script ssh-hostkey -p 22 target
```

**SSL / TLS**
```bash
nmap --script ssl-enum-ciphers -p 443 target
nmap --script ssl-heartbleed -p 443 target             # Heartbleed
nmap --script ssl-poodle -p 443 target
nmap --script ssl-dh-params -p 443 target              # Logjam
```

**FTP**
```bash
nmap --script ftp-anon -p 21 target                    # anonymous login
nmap --script ftp-bounce -p 21 target
nmap --script ftp-vuln-cve2010-4221 -p 21 target
```

**Databases**
```bash
nmap --script ms-sql-info,ms-sql-empty-password -p 1433 target
nmap --script mysql-info,mysql-empty-password -p 3306 target
nmap --script pgsql-brute -p 5432 target
nmap --script oracle-sid-brute -p 1521 target
nmap --script mongodb-info -p 27017 target
nmap --script redis-info -p 6379 target
```

**Other services**
```bash
nmap --script snmp-info,snmp-sysdescr -p 161 target --script-args snmpcommunity=public
nmap --script ldap-rootdse -p 389,636 target
nmap --script vnc-info -p 5900 target
nmap --script rdp-enum-encryption -p 3389 target
```

---

## Layer 4 — Targeted scanners by technology

Run only when the technology is confirmed via fingerprinting.

### testssl — TLS/SSL comprehensive audit

```bash
# Full audit
testssl --full https://target.com

# High-severity only
testssl --severity HIGH --parallel https://target.com

# Batch mode
testssl --parallel --file hosts_443.txt

# Key findings to act on:
# POODLE / BEAST / CRIME / BREACH / Heartbleed — verify manually
# TLS 1.0/1.1 enabled → cipher downgrade
# Weak ciphers (RC4, DES, 3DES) → negotiation attack
# Certificate: expired, self-signed, wrong CN → misconfiguration
```

### wpscan — WordPress

```bash
# Enumerate plugins, themes, users (passive)
wpscan --url https://target.com --enumerate vp,vt,u --no-update

# With vuln database (requires API token)
wpscan --url https://target.com --enumerate vp,vt,u --api-token <TOKEN>

# Key findings:
# Plugin with known CVE → searchsploit plugin_name
# Admin user discovered → password spray / brute-force
# xmlrpc.php enabled → brute-force amplification, SSRF
# Debug log exposed → path disclosure, credentials
```

### OpenVAS — comprehensive infrastructure scan

Use for full network infrastructure assessment where full port/service coverage is needed.

```bash
# CLI run (after OpenVAS setup)
gvm-cli --gmp-username admin --gmp-password admin \
  socket --xml "<create_target><name>target</name><hosts>10.0.0.1</hosts></create_target>"

# Run from Greenbone Web UI — create scan, select policy, launch
```

---

## Scanner output consolidation

After all layers complete, merge and deduplicate:

```bash
# Merge nuclei findings
cat phase_a.txt phase_b.txt phase_c.txt phase_d.txt | sort -u > nuclei_all.txt

# Extract unique vulnerability names
cat nuclei_all.txt | grep -oP '\[[^\]]+\] \[[^\]]+\]' | sort -u

# Triage by severity
grep "\[critical\]" nuclei_all.txt
grep "\[high\]" nuclei_all.txt
```

Final triage step — for every finding:
1. Confirm it's not a scanner false positive (manual HTTP verification)
2. Note: target, vuln class/CVE, evidence, severity
3. Assign to exploit phase (infrastructure → `vuln-exploit-technique`, web → `web-exploit-technique`)
