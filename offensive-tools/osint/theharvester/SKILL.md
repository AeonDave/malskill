---
name: theharvester
description: "Harvest emails, subdomains, hostnames, employee names, open ports, and banners for a target domain from public sources. Use at the start of recon to build an attack surface map: enumerate email addresses for phishing, discover subdomains for web app testing, and identify infrastructure from passive sources."
license: GPL-2.0
compatibility: "Python 3; pip install theHarvester OR pre-installed on Kali; github.com/laramies/theHarvester"
metadata:
  author: AeonDave
  version: "1.0"
---

# theHarvester

Email, subdomain, and hostname harvester from public OSINT sources.

## Quick Start

```bash
# Install
pip install theHarvester
# or on Kali: already installed

# Basic harvest (google + bing sources)
theHarvester -d target.com -b google,bing

# All available sources
theHarvester -d target.com -b all -l 500

# Save results
theHarvester -d target.com -b google,bing,linkedin -l 300 -f results
# Outputs: results.html + results.xml
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-d <domain>` | Target domain |
| `-b <sources>` | Data sources (comma-separated or `all`) |
| `-l <n>` | Limit results per source (default: 500) |
| `-f <filename>` | Save to HTML/XML (no extension needed) |
| `-n` | DNS lookup on discovered hosts |
| `-c` | DNS brute force (uses built-in wordlist) |
| `-v` | Verify hostnames via DNS resolution |
| `-e <ip>` | Use custom DNS server |
| `-p` | Port scan open ports on discovered hosts |
| `-s <n>` | Start result offset |
| `--screenshot <dir>` | Screenshot discovered web services |

## Data Sources

```bash
# Passive (no key needed)
-b google,bing,yahoo,duckduckgo,baidu,crtsh,certspotter,hackertarget,dnsdumpster,rapiddns,sublist3r

# Requires API keys
-b hunter,securitytrails,shodan,censys,fullhunt,intelx,virustotal,bevigil,binaryedge

# LinkedIn (extracts names/titles — no key needed, rate limited)
-b linkedin,linkedin_links

# All sources at once
-b all
```

## Common Workflows

**Recon on target company:**
```bash
# Phase 1: passive — no noise
theHarvester -d corp.com -b google,bing,duckduckgo,crtsh,certspotter,hackertarget -l 500 -f corp_passive

# Phase 2: extended — with APIs
theHarvester -d corp.com -b all -l 1000 -f corp_full

# Phase 3: verify + port scan discovered hosts
theHarvester -d corp.com -b google,crtsh -v -p -l 200
```

**Email harvest for phishing prep:**
```bash
theHarvester -d target.com -b google,bing,linkedin,hunter -l 500 -f emails
# Check results.html for email list
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' results.xml | sort -u > emails.txt
```

**Subdomain discovery:**
```bash
theHarvester -d target.com -b crtsh,certspotter,dnsdumpster,sublist3r,hackertarget -l 500 -f subdomains
```

## API Keys Setup

```bash
# Config: /etc/theHarvester/api-keys.yaml or ~/.theHarvester/api-keys.yaml
```

```yaml
apikeys:
  hunter:
    key: YOUR_KEY         # hunter.io — free 50/month
  securitytrails:
    key: YOUR_KEY         # securitytrails.com — free 50/month
  shodan:
    key: YOUR_KEY         # shodan.io — free tier
  virustotal:
    key: YOUR_KEY         # virustotal.com — free
  intelx:
    key: YOUR_KEY         # intelx.io — free tier
```

## Parse Output

```bash
# Extract emails from XML output
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' results.xml | sort -u

# Extract subdomains
grep -oE '([a-zA-Z0-9_-]+\.)+target\.com' results.xml | sort -u

# Use holehe on harvested emails
while read email; do holehe "$email" --only-used; done < emails.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/sources.md` | Full source list, API key setup, output parsing, integration with amass/holehe |
