---
name: nuclei
description: "Template-based vulnerability and exposure scanner from ProjectDiscovery. Use when asked to scan a host or list for known vulnerabilities, misconfigurations, exposed panels, CVEs, default credentials, or security issues using community-maintained templates."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest or download binary. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.1"
---

# Nuclei

Template-based scanner — 10,000+ community templates covering CVEs, misconfigs, exposures, default creds.

## Quick Start

```bash
# Update templates first (always)
nuclei -update-templates

# Scan a target
nuclei -u https://target.com

# Scan a list
nuclei -l urls.txt -exclude-severity info -stats
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <url>` | Single target URL |
| `-l <file>` | File with list of URLs |
| `-t <path>` | Template file/directory/URL |
| `-tags <tags>` | Run templates by tag (e.g., `cve,rce,lfi`) |
| `-id <id>` | Run specific template by ID |
| `-severity <s>` | Filter by severity: `info,low,medium,high,critical` |
| `-exclude-severity <s>` | Exclude severity levels (alias: `-es`) |
| `-exclude-tags <tags>` | Exclude tags (alias: `-etags`) |
| `-et <path>` | Exclude template path |
| `-V <var=val>` | Template variable override |
| `-nt` | Run only new templates (since last update) |
| `-H <header>` | Custom HTTP header |
| `-c <n>` | Concurrent templates (default 25) |
| `-bs <n>` | Bulk size (targets per template batch) |
| `-rl <n>` | Rate limit req/sec (default 150) |
| `-timeout <n>` | HTTP timeout (default 5s) |
| `-retries <n>` | Retries on timeout |
| `-proxy <url>` | HTTP/SOCKS5 proxy |
| `-o <file>` | Output file |
| `-json` | JSON output |
| `-jsonl` | JSON Lines output |
| `-silent` | Print findings only |
| `-v` | Verbose |
| `-stats` | Show real-time stats |
| `-update-templates` | Update community templates |
| `-tl` | List all available templates |

## Template Categories (Tags)

| Tag | Description |
|-----|-------------|
| `cve` | CVE-based exploits and detections |
| `panel` | Admin/login panel detection |
| `exposure` | Exposed files, tokens, secrets |
| `misconfig` | Misconfigurations |
| `default-login` | Default credentials |
| `takeover` | Subdomain takeover |
| `tech` | Technology fingerprinting |
| `xss` | Cross-site scripting |
| `sqli` | SQL injection |
| `ssrf` | Server-side request forgery |
| `lfi` | Local file inclusion |
| `rce` | Remote code execution |
| `network` | Network-level checks |
| `dns` | DNS-level checks |
| `wordpress` | WordPress-specific |
| `jira` | Jira-specific |
| `gitlab` | GitLab-specific |

## Common Workflows

```bash
# Attack surface map (fast, no heavy scanning)
nuclei -l hosts.txt -tags tech,panel -severity info,low -silent

# CVE scan (high impact only)
nuclei -l hosts.txt -tags cve -severity critical,high -o cve_findings.jsonl -jsonl

# Exposed panels + default creds
nuclei -l hosts.txt -tags panel,default-login -severity medium,high,critical

# Find exposed secrets/tokens
nuclei -l urls.txt -tags exposure -silent

# Subdomain takeover check
nuclei -l subs.txt -tags takeover

# Injection testing (active)
nuclei -l urls.txt -tags xss,sqli,ssrf,lfi -severity medium,high,critical

# WordPress scan
nuclei -u https://target.com -tags wordpress -severity medium,high,critical

# Full scan (skip info noise)
nuclei -l hosts.txt -exclude-severity info -o findings.jsonl -jsonl -stats

# New templates only (post-update quick check)
nuclei -l hosts.txt -nt -severity high,critical

# Pipeline: subfinder → httpx → nuclei
subfinder -d target.com -silent | \
  httpx -silent | \
  nuclei -tags cve,panel,exposure,misconfig -severity high,critical

# Through Burp proxy
nuclei -u https://target.com -proxy http://127.0.0.1:8080
```

## Template Management

```bash
# Update templates
nuclei -update-templates

# List all templates
nuclei -tl

# List by tag
nuclei -tl -tags cve | head -20

# Run specific template
nuclei -u https://target.com -t cves/2021/CVE-2021-44228.yaml

# Run custom template directory
nuclei -l hosts.txt -t ~/custom-templates/

# Override template variable
nuclei -u https://target.com -t custom.yaml -V "target_path=/admin"
```

## Resources

| File | When to load |
|------|--------------|
| `references/templates.md` | Template structure, custom writing, matcher/extractor types, output parsing, rate tuning |
