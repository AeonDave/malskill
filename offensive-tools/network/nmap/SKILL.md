---
name: nmap
description: "Network port scanner for host discovery, port scanning, service/version detection, OS fingerprinting, and NSE script execution. Use when asked to scan a target, find open ports, enumerate services, identify OS, run vuln scripts, or perform network reconnaissance on an IP, range, or domain."
license: GPL-2.0
compatibility: "Linux, Windows, macOS. Pre-installed on Kali/Parrot. Windows: download installer from nmap.org. Requires raw socket access (root/admin for SYN scans)."
metadata:
  author: AeonDave
  version: "1.1"
---

# Nmap

Fast, scriptable network scanner — the standard for port scanning and service enumeration.

## Quick Start

```bash
# Basic TCP SYN scan, top 1000 ports
nmap -sS -T4 <target>

# Full port scan with version + scripts + OS detection
nmap -sS -sV -sC -O -p- -T4 <target> -oA output/nmap_full

# Fast top-100 ports
nmap -F -T4 <target>
```

## Core Scan Types

| Flag | Scan Type | Notes |
|------|-----------|-------|
| `-sS` | TCP SYN (stealth) | Requires root; most common |
| `-sT` | TCP Connect | No root needed; louder |
| `-sU` | UDP scan | Slow; combine with `-sS` |
| `-sN/sF/sX` | Null/FIN/Xmas | Firewall evasion |
| `-sA` | ACK scan | Map firewall rules |
| `-sV` | Version detection | Service banners |
| `-sC` | Default scripts | Runs common NSE scripts |
| `-O` | OS detection | Requires root |
| `-A` | Aggressive | `-sV -sC -O --traceroute` |

## Port Selection

```bash
-p 22,80,443          # specific ports
-p 1-1024             # range
-p-                   # all 65535 ports
--top-ports 1000      # top N most common
-F                    # top 100 (fast)
```

## Output Formats

```bash
-oN file.txt          # normal (human-readable)
-oX file.xml          # XML (parseable)
-oG file.gnmap        # grepable
-oA basename          # all three formats
```

## Timing & Performance

| Template | Use Case |
|----------|----------|
| `-T0` | Paranoid — IDS evasion |
| `-T1` | Sneaky |
| `-T3` | Default |
| `-T4` | Aggressive — fast networks |
| `-T5` | Insane — may miss results |

Fine-grain: `--min-rate 1000 --max-retries 2`

## Target Specification

```bash
nmap 192.168.1.1
nmap 192.168.1.0/24
nmap 192.168.1.1-254
nmap -iL targets.txt        # from file
nmap --exclude 192.168.1.5
```

## NSE Scripts

```bash
# Run a specific script
nmap --script smb-vuln-ms17-010 -p 445 <target>

# Run a category
nmap --script vuln <target>
nmap --script "safe and discovery" <target>

# Auth brute-force
nmap --script http-brute -p 80 <target>
```

Script categories: `auth`, `broadcast`, `brute`, `default`, `discovery`, `dos`, `exploit`, `external`, `fuzzer`, `intrusive`, `malware`, `safe`, `version`, `vuln`

## Common Workflows

```bash
# Host discovery only (ping sweep)
nmap -sn 192.168.1.0/24

# Full recon one-liner
nmap -sS -sV -sC -O -p- -T4 --open -oA full_scan <target>

# Internal Windows network
nmap -sS -p 135,139,445,3389,5985 -T4 192.168.1.0/24

# Web surface
nmap -sV -p 80,443,8080,8443 --script http-headers,http-title <target>

# UDP top services
nmap -sU --top-ports 20 -T4 <target>
```

## Firewall / IDS Evasion

```bash
# Fragment packets (bypass stateless packet filters)
nmap -f <target>

# Decoy scan (blend with fake source IPs)
nmap -D RND:10 <target>
nmap -D 192.168.1.5,192.168.1.10,ME <target>

# Idle scan (use zombie host — completely spoofed source)
nmap -sI <zombie_ip> <target>

# Custom source port (bypass firewall rules allowing DNS/HTTP back-traffic)
nmap --source-port 53 <target>
nmap --source-port 80 <target>

# Slow timing (T1/T2 to avoid threshold-based IDS)
nmap -T1 -p 22,80,443 <target>

# Randomize host order + append random data
nmap --randomize-hosts --data-length 25 <target>
```

## IPv6

```bash
nmap -6 -sV fe80::1%eth0
nmap -6 -sS -p 22,80,443 2001:db8::/32
```

## Resources

| File | When to load |
|------|--------------|
| `references/nse-scripts.md` | NSE script list by category, syntax, vuln scripts, auth brute, discovery |
