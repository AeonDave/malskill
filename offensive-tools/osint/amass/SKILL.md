---
name: amass
description: "OWASP attack surface mapping tool for subdomain enumeration, DNS brute-forcing, and infrastructure discovery using 50+ data sources. Use when performing thorough subdomain enumeration, mapping an organization's full internet-facing attack surface, tracking asset changes over time, or feeding a list of hosts into web app testing."
license: Apache-2.0
compatibility: "Go binary; Linux/macOS/Windows; apt install amass (Kali) or download from github.com/owasp-amass/amass/releases"
metadata:
  author: AeonDave
  version: "1.0"
---

# Amass

OWASP attack surface mapper — thorough subdomain enumeration via 50+ passive + active sources.

## Quick Start

```bash
# Passive enumeration (no direct target interaction)
amass enum -passive -d target.com

# Active enumeration (DNS brute force + zone transfer attempts)
amass enum -active -d target.com -brute

# Save results
amass enum -d target.com -o subdomains.txt

# Full enumeration with output files
amass enum -d target.com -brute -o subs.txt -oA results/amass
```

## Subcommands

| Subcommand | Purpose |
|-----------|---------|
| `enum` | Subdomain enumeration (main use) |
| `intel` | Gather intel on an org (ASN, CIDRs, root domains) |
| `viz` | Visualize attack surface (Maltego, Gephi, GraphViz) |
| `track` | Track changes in attack surface over time |
| `db` | Interact with local Amass database |

## Core Flags (enum)

| Flag | Purpose |
|------|---------|
| `-d <domain>` | Target domain (repeat for multiple) |
| `-passive` | Passive only (no direct DNS queries to target) |
| `-active` | Active (DNS queries, zone transfer, cert grabbing) |
| `-brute` | DNS brute-force with wordlist |
| `-w <wordlist>` | Custom brute-force wordlist |
| `-r <resolvers>` | Custom DNS resolvers file |
| `-o <file>` | Plain text output |
| `-oA <prefix>` | All output formats (json, txt, etc.) |
| `-json <file>` | JSON output |
| `-ip` | Include IP addresses in output |
| `-src` | Show data source for each result |
| `-timeout <n>` | Minutes before timeout (default: 30) |
| `-max-depth <n>` | Max DNS brute-force recursion depth |
| `-config <file>` | Config file path |
| `-dir <path>` | Output directory for all files |
| `-dL <file>` | File with list of domains |

## Common Workflows

**Passive recon (silent, no DNS to target):**
```bash
amass enum -passive -d target.com -src -o passive_subs.txt
```

**Active + brute force:**
```bash
amass enum -active -d target.com -brute -o active_subs.txt
```

**Multiple domains from file:**
```bash
amass enum -passive -dL domains.txt -o all_subs.txt
```

**D3.js visualization of attack surface:**
```bash
amass viz -d3 -dir amass_out/ -d target.com
# Opens interactive graph in browser at amass_out/vis/d3.html
```

**With IP resolution:**
```bash
amass enum -d target.com -ip -o subs_with_ips.txt
```

**Organization intelligence (find all CIDRs + domains):**
```bash
# Find ASN for organization
amass intel -org "Target Corp"

# Enumerate from ASN
amass intel -asn 12345 -ip

# Enumerate from CIDR
amass intel -cidr 203.0.113.0/24
```

## Config File (API Keys)

```ini
# ~/.config/amass/config.ini or /etc/amass/config.ini

[data_sources]

[data_sources.CertSpotter]
[data_sources.CertSpotter.Credentials]
apikey = YOUR_KEY

[data_sources.Shodan]
[data_sources.Shodan.Credentials]
apikey = YOUR_KEY

[data_sources.SecurityTrails]
[data_sources.SecurityTrails.Credentials]
apikey = YOUR_KEY

[data_sources.VirusTotal]
[data_sources.VirusTotal.Credentials]
apikey = YOUR_KEY

[data_sources.Hunter]
[data_sources.Hunter.Credentials]
apikey = YOUR_KEY
```

## Post-Processing

```bash
# Sort and deduplicate
sort -u subdomains.txt > unique_subs.txt

# Resolve live hosts (dnsx)
cat unique_subs.txt | dnsx -silent -a -resp > live_hosts.txt

# HTTP probe (httpx)
cat unique_subs.txt | httpx -silent -status-code -title -tech-detect > web_services.txt

# Feed into nmap
nmap -iL unique_subs.txt -sV -p 80,443,8080,8443 --open -T4
```

## Resources

| File | When to load |
|------|--------------|
| `references/config.md` | Full config file options, API source list, wordlist recommendations, pipeline with httpx/dnsx |
