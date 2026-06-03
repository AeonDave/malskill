---
name: masscan
description: "Auth/lab ref: ultra-fast async TCP SYN port scanner capable of scanning the entire IPv4 internet in minutes."
license: MIT
compatibility: "Linux / macOS / Windows (WSL); Build from source or package manager."
metadata:
  author: AeonDave
  version: "1.1"
---

# Masscan

Ultra-fast TCP SYN scanner for large-scale port discovery.

## Quick Start

```bash
masscan 10.0.0.0/16 -p445 --rate=10000 -oG out.gnmap
masscan 10.0.0.0/8 -p0-1023 --rate=50000 -oX out.xml
masscan -iL targets.txt -p80,443,8080,445 --rate=10000
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-p <ports>` | Port list / range (e.g. `0-65535`, `80,443`) |
| `--rate <n>` | Packets per second (start low) |
| `-oG / -oX / -oJ` | Output: grepable / XML / JSON |
| `-iL <file>` | Read targets from file |
| `--banners` | Grab service banners |
| `--excludefile` | Exclude IPs from scan |
| `--adapter-ip` | Source IP |
| `--router-mac` | Default gateway MAC |

## Common Workflows

### Feed results into nmap

```bash
# Discover open ports fast
masscan 10.0.0.0/24 -p1-65535 --rate=5000 -oG masscan.out

# Extract unique ports
grep "open" masscan.out | awk '{print $4}' | cut -d/ -f1 | sort -u | paste -sd, > ports.txt

# Extract unique hosts
grep "open" masscan.out | awk '{print $6}' | sort -u > hosts.txt

# Deep scan on discovered ports/hosts
nmap -sV -sC -O -p$(cat ports.txt) -iL hosts.txt -oA nmap_deep
```

### Banner grabbing

```bash
masscan 10.0.0.0/24 -p22,80,443,445,8080 --banners --rate=1000 -oJ results.json
```

### Config file (repeat scans)

```ini
# masscan.conf
rate = 10000
ports = 0-65535
output-format = json
output-filename = results.json
excludefile = /etc/masscan/exclude.conf
```

```bash
masscan 10.0.0.0/8 -c masscan.conf
```

### Resume interrupted scan

```bash
masscan 10.0.0.0/8 -p- --rate=50000 --resume paused.conf
```

## Rate Tuning

| Environment | Safe Rate |
|-------------|-----------|
| Internal lab | 10,000–100,000 |
| Corporate network | 1,000–5,000 |
| Internet | 10,000–1,000,000 |
| Stealth | 100–500 |

- Start at `--rate=1000` and increase; watch for packet loss
- Set `--adapter-ip` if multiple interfaces exist
- Use `--router-mac` if default gateway detection fails

## Resources

| File | When to load |
|------|--------------|
| `references/tuning.md` | Config file options, adapter settings, exclude lists |
