---
name: masscan
description: "Masscan: ultra-fast async TCP SYN port scanner capable of scanning the entire IPv4 internet in minutes. Use when performing wide-area network sweeps, identifying open ports across large CIDR ranges, or as a first-pass discovery step before nmap service scanning."
license: MIT
compatibility: "Linux / macOS / Windows (WSL). Build from source or package manager."
metadata:
  author: AeonDave
  version: "1.0"
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
masscan 10.0.0.0/24 -p1-65535 --rate=5000 -oG masscan.out
grep "open" masscan.out | awk '{print $4}' | cut -d/ -f1 | sort -u > ports.txt
nmap -sV -p$(paste -sd, ports.txt) -iL hosts.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Extended options and tuning notes |
