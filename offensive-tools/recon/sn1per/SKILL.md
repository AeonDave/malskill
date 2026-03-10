---
name: sn1per
description: "Automated penetration testing recon framework combining 20+ tools in a single scan. Use when performing comprehensive target recon that combines port scanning, subdomain discovery, web crawling, and vulnerability detection."
license: MIT
compatibility: "Bash; Linux (Kali recommended); github.com/1N3/Sn1per"
metadata:
  author: AeonDave
  version: "1.0"
---

# Sn1per

Automated recon framework — orchestrates nmap, nikto, metasploit, amass, and 20+ tools.

## Quick Start

```bash
git clone https://github.com/1N3/Sn1per
cd Sn1per && bash install.sh

# Full recon on target
sniper -t target.com

# Network CIDR scan
sniper -t 10.10.10.0/24 -m discover

# Web scan only
sniper -t target.com -m web
```

## Scan Modes

| Mode | Purpose |
|------|---------|
| (default) | Full recon + vuln scan |
| `discover` | Network discovery (ping sweep, port scan) |
| `stealth` | Slower, quieter scan |
| `web` | Web-focused (nikto, gobuster, etc.) |
| `bruteforce` | Service brute-force |
| `airstrike` | Mass scan from CIDR |
| `nuke` | Full attack automation |

## Common Workflows

**Full target assessment:**
```bash
sniper -t target.com
# Results in /usr/share/sniper/loot/
```

**CIDR discovery:**
```bash
sniper -t 192.168.1.0/24 -m discover -w workspace1
```

**Web app assessment:**
```bash
sniper -t https://app.target.com -m web
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Module configuration and loot paths |
