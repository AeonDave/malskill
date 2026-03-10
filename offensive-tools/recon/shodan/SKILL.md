---
name: shodan
description: "Shodan CLI for passive internet-wide host and service discovery. Use when asked to search Shodan, find internet-exposed services, discover infrastructure passively, look up an IP or org, query specific banners or CVEs, or enumerate assets without touching the target."
license: MIT
compatibility: "Linux, Windows, macOS. Install: pip install shodan. Requires a Shodan API key (free tier available; paid for full access)."
metadata:
  author: AeonDave
  version: "1.0"
---

# Shodan CLI

Passive reconnaissance via Shodan — internet-wide host/service discovery without touching targets.

## Quick Start

```bash
# Initialize with API key
shodan init YOUR_API_KEY

# Search for a service/banner
shodan search "apache 2.4.49"

# Host lookup
shodan host 203.0.113.10

# Account info / credits
shodan info
```

## Core Commands

| Command | Description |
|---------|-------------|
| `shodan search <query>` | Search Shodan index |
| `shodan host <ip>` | Detailed host info (open ports, banners, vulns) |
| `shodan count <query>` | Count results (no credits consumed) |
| `shodan download <file> <query>` | Download results to compressed JSON |
| `shodan parse <file>` | Parse downloaded results |
| `shodan domain <domain>` | Domain intelligence |
| `shodan alert` | Manage monitoring alerts |
| `shodan stats <query>` | Statistics for a query |
| `shodan honeyscore <ip>` | Honeypot score (0-1) |
| `shodan myip` | Your public IP |

## Search Filters

| Filter | Example |
|--------|---------|
| `hostname:` | `hostname:example.com` |
| `ip:` | `ip:1.2.3.0/24` |
| `org:` | `org:"Target Corp"` |
| `port:` | `port:8080` |
| `product:` | `product:Apache` |
| `version:` | `version:2.4.49` |
| `country:` | `country:IT` |
| `os:` | `os:Windows` |
| `vuln:` | `vuln:CVE-2021-44228` |
| `http.title:` | `http.title:"Login"` |
| `html:` | `html:"admin panel"` |
| `ssl:` | `ssl:"example.com"` |
| `asn:` | `asn:AS12345` |
| `net:` | `net:192.168.0.0/16` |

## Common Workflows

```bash
# Find infrastructure for an org
shodan search org:"Target Corp" --fields ip_str,port,product

# Download and parse org results
shodan download results.json.gz org:"Target Corp"
shodan parse --fields ip_str,port,product results.json.gz

# Find exposed login panels
shodan search http.title:"administration" org:"Target"

# CVE-based research
shodan search vuln:CVE-2021-44228

# SSL cert pivot — find all hosts sharing a cert
shodan search ssl:"example.com"

# Count without consuming query credits
shodan count org:"Target Corp"

# Reverse lookup / host details
shodan host 8.8.8.8
```

## Resources

| File | When to load |
|------|--------------|
| `references/search-filters.md` | Full filter reference, dork recipes, API integration examples |
