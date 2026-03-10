---
name: sublist3r
description: "Subdomain enumeration using OSINT sources (Google, Bing, Baidu, DNSDumpster, VirusTotal, ThreatCrowd). Use when passively enumerating subdomains from public search engines and threat intel platforms."
license: MIT
compatibility: "Python 3; pip install sublist3r; Linux/macOS/Windows; github.com/aboul3la/Sublist3r"
metadata:
  author: AeonDave
  version: "1.0"
---

# Sublist3r

Passive subdomain enumeration via OSINT — search engines, DNSDumpster, VirusTotal.

## Quick Start

```bash
pip install sublist3r

# Basic subdomain enum
sublist3r -d target.com

# With brute-force
sublist3r -d target.com -b -w wordlist.txt

# Save output
sublist3r -d target.com -o subdomains.txt

# Verbose (show sources)
sublist3r -d target.com -v
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-d DOMAIN` | Target domain |
| `-b` | Enable brute-force |
| `-w FILE` | Brute-force wordlist |
| `-p PORTS` | Check ports on found hosts |
| `-v` | Verbose (show each source) |
| `-t N` | Threads (default: 10) |
| `-o FILE` | Output file |
| `-e ENGINES` | Comma-separated engines |

## Sources Used

Google · Bing · Yahoo · Baidu · Ask · Netcraft · DNSDumpster · VirusTotal · ThreatCrowd · SSL certs · PassiveDNS

## Common Workflows

**Passive only (stealthy):**
```bash
sublist3r -d target.com -o passive_subs.txt
```

**Active brute + passive combined:**
```bash
sublist3r -d target.com -b -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -o all_subs.txt
```

**Pipe to resolver:**
```bash
sublist3r -d target.com -o subs.txt
cat subs.txt | dnsx -silent -a -resp > live.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Engine API keys and wordlist sources |
