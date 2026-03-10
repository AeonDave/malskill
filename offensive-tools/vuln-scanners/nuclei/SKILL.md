---
name: nuclei
description: "Template-based vulnerability scanner for web apps, networks, and infrastructure. Use when asked to scan for known CVEs, misconfigurations, default credentials, exposed panels, or run a template-based vulnerability assessment against a target URL or IP."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest or download binary. Pre-installed on Kali."
metadata:
  author: AeonDave
  version: "1.0"
---

# Nuclei

Template-based vulnerability scanner — 10,000+ community templates covering CVEs, misconfigs, and exposures.

## Quick Start

```bash
# Scan a URL with auto-updated templates
nuclei -u https://example.com

# Scan from a list of URLs
nuclei -l urls.txt

# Run specific template category
nuclei -u https://example.com -t technologies/
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-u <url>` | Single target URL |
| `-l <file>` | File with list of URLs |
| `-t <path>` | Template file/directory/URL |
| `-tags <tags>` | Run templates by tag (e.g., `cve,rce,lfi`) |
| `-severity <s>` | Filter by severity: `info,low,medium,high,critical` |
| `-et <path>` | Exclude template path |
| `-etags <tags>` | Exclude tags |
| `-es <severity>` | Exclude severity |
| `-H <header>` | Custom HTTP header |
| `-V <var=val>` | Template variable override |
| `-o <file>` | Output file (default stdout) |
| `-json` | JSON output |
| `-jsonl` | JSON Lines output |
| `-c <n>` | Concurrent templates (default 25) |
| `-rate-limit <n>` | Max requests/second |
| `-timeout <n>` | HTTP timeout (default 5s) |
| `-retries <n>` | Retries on timeout |
| `-rl <n>` | Rate limit per host |
| `-proxy <url>` | HTTP/SOCKS5 proxy |
| `-update-templates` | Update community templates |
| `-nt` | New templates only (since last update) |
| `-silent` | Print findings only |
| `-v` | Verbose |
| `-stats` | Display scan statistics |

## Template Categories

```bash
nuclei -u https://target.com -t cves/              # CVE templates
nuclei -u https://target.com -t exposures/         # Exposed files/panels
nuclei -u https://target.com -t technologies/      # Tech fingerprinting
nuclei -u https://target.com -t misconfigurations/ # Misconfigs
nuclei -u https://target.com -t default-logins/    # Default credentials
nuclei -u https://target.com -t network/           # TCP/UDP templates
```

## Common Workflows

```bash
# Update templates first
nuclei -update-templates

# Full web scan (skip info)
nuclei -l urls.txt -es info -o findings.txt

# CVE-focused scan
nuclei -u https://target.com -tags cve -severity medium,high,critical

# Exposed panels and admin interfaces
nuclei -u https://target.com -tags panel,login,exposure

# Custom template
nuclei -u https://target.com -t /path/to/custom.yaml

# Scan with proxy (Burp)
nuclei -u https://target.com -proxy http://127.0.0.1:8080

# Fast recon with tech fingerprint
nuclei -l urls.txt -t technologies/ -silent
```

## Resources

| File | When to load |
|------|--------------|
| `references/templates.md` | Template syntax, custom template writing, tag reference |
