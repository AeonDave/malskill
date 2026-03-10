---
name: subfinder
description: "Passive subdomain enumeration tool using 40+ OSINT sources. Use when asked to find subdomains, enumerate attack surface, discover hidden hosts, or map a target domain's infrastructure passively without touching the target."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest or download binary from projectdiscovery releases."
metadata:
  author: AeonDave
  version: "1.0"
---

# Subfinder

Fast passive subdomain enumeration — part of the ProjectDiscovery toolkit.

## Quick Start

```bash
# Enumerate subdomains for a domain
subfinder -d example.com

# Output to file
subfinder -d example.com -o subs.txt

# Silent mode (subdomains only, no banner)
subfinder -d example.com -silent
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-d <domain>` | Target domain |
| `-dL <file>` | List of domains from file |
| `-o <file>` | Output file |
| `-oJ` | JSON output |
| `-silent` | Print subdomains only |
| `-t <n>` | Threads (default 10) |
| `-timeout <n>` | Timeout per source (seconds) |
| `-all` | Use all sources (slower, more results) |
| `-recursive` | Enumerate recursively |
| `-active` | Active DNS verification of results |
| `-v` | Verbose output |

## Provider Configuration

Configure API keys in `~/.config/subfinder/provider-config.yaml`:

```yaml
shodan:
  - YOUR_SHODAN_KEY
virustotal:
  - YOUR_VT_KEY
censys:
  - YOUR_CENSYS_ID:YOUR_SECRET
binaryedge:
  - YOUR_KEY
```

Without API keys, subfinder still uses free sources (crt.sh, hackertarget, etc.).

## Common Workflows

```bash
# Enumerate + pipe to httpx for live host check
subfinder -d example.com -silent | httpx -silent

# Recursive enumeration
subfinder -d example.com -recursive -silent -o all_subs.txt

# Multiple domains from file
subfinder -dL domains.txt -silent -o subs.txt

# Use all sources for maximum coverage
subfinder -d example.com -all -silent

# JSON output for automation
subfinder -d example.com -oJ -o subs.json
```

## Resources

| File | When to load |
|------|--------------|
| `references/providers.md` | Full list of supported passive sources and API key setup |
