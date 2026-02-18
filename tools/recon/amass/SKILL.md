---
name: amass
description: "OWASP attack surface mapping tool for subdomain enumeration, DNS brute-force, and asset discovery using passive and active techniques. Use when asked for deep subdomain reconnaissance, attack surface mapping, DNS enumeration, or when subfinder alone is insufficient."
license: Apache-2.0
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/owasp-amass/amass/v4/...@master or download binary from GitHub releases."
metadata:
  author: AeonDave
  version: "1.0"
---

# Amass

OWASP Attack Surface Mapper — combines passive OSINT with active DNS enumeration.

## Quick Start

```bash
# Passive enumeration
amass enum -passive -d example.com

# Active enumeration (DNS brute-force + passive)
amass enum -active -d example.com

# Save results to output directory
amass enum -d example.com -o subs.txt -dir amass_out/
```

## Sub-commands

| Command | Description |
|---------|-------------|
| `enum` | Subdomain enumeration (main workflow) |
| `intel` | Gather org/ASN/CIDR intelligence |
| `viz` | Generate graph visualizations |
| `track` | Track changes over time |
| `db` | Manage the Amass graph database |

## Enum Flags

| Flag | Description |
|------|-------------|
| `-d <domain>` | Target domain |
| `-dL <file>` | Domain list file |
| `-passive` | Passive only (no DNS probing) |
| `-active` | Active mode (DNS + cert grabbing) |
| `-brute` | DNS brute-force with wordlist |
| `-w <wordlist>` | Custom wordlist for brute-force |
| `-r <resolvers>` | Custom DNS resolvers file |
| `-o <file>` | Output file |
| `-dir <path>` | Output directory for all files |
| `-config <file>` | Config file (API keys, settings) |
| `-timeout <mins>` | Enum timeout in minutes |

## Config File (API Keys)

Create `~/.config/amass/config.yaml`:

```yaml
scope:
  domains:
    - example.com
data_sources:
  Shodan:
    - apikey: YOUR_KEY
  VirusTotal:
    - apikey: YOUR_KEY
  Censys:
    - apikey: YOUR_ID
      secret: YOUR_SECRET
```

## Common Workflows

```bash
# Passive recon only
amass enum -passive -d example.com -o passive_subs.txt

# Full active enum with brute-force
amass enum -active -brute -w /usr/share/wordlists/subdomains.txt -d example.com

# Org intelligence (find related ASNs/CIDRs)
amass intel -org "Target Corp" -max-dns-queries 2500

# Multiple domains
amass enum -passive -dL domains.txt -o all_subs.txt

# Visualization after enum
amass viz -d3 -dir amass_out/ -d example.com
```

## Resources

| File | When to load |
|------|--------------|
| `references/enum-modes.md` | Deep-dive on intel/enum/viz modes, config file syntax, resolver setup |
