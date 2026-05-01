---
name: rustscan
description: |
  Ultra-fast port scanner that finds open ports in seconds then auto-pipes into nmap for service/version
  detection. Use for initial port discovery on individual hosts or small ranges where speed matters.
  Complements masscan (broad range) and nmap (deep single-host). Best for: CTF initial recon,
  quick service fingerprint after foothold, fast validation before exploitation.
license: MIT
compatibility: "Linux/macOS/Windows. Install: cargo install rustscan, apt, or Docker. Requires nmap."
metadata:
  author: AeonDave
  version: "2.0"
---

# RustScan

Blazing-fast port discovery with automatic nmap handoff. Find open ports in seconds, get nmap service data in one command.

## Installation

```bash
# Cargo
cargo install rustscan

# Apt (Kali/Debian)
sudo apt install rustscan

# Docker (no install)
docker run -it --rm --name rustscan rustscan/rustscan:latest -a TARGET -- -sV

# Snap
sudo snap install rustscan
```

---

## Core Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `-a <addr>` | Target — IP, CIDR, hostname, or file | required |
| `-p <ports>` | Specific ports to scan | all 65535 |
| `--range <start-end>` | Port range (e.g. `1-1024`) | — |
| `-b <batch>` | Ports probed per batch | 4500 |
| `-t <ms>` | Timeout per port | 1500ms |
| `--ulimit <n>` | File descriptor limit (higher = faster) | 8000 |
| `--no-nmap` | Skip nmap; output open ports only | false |
| `--scan-order <order>` | `Serial` or `Random` | Serial |
| `--scripts <script>` | nmap script category shorthand | `default` |
| `--top` | Scan top 1000 ports only | false |
| `--greppable`, `-g` | Machine-readable output | false |
| `--accessible` | Accessibility-friendly output | false |
| `--quiet`, `-q` | Suppress banner | false |
| `-- <nmap args>` | Any nmap flags passed through | — |

---

## Common Workflows

### Standard full scan (most useful for CTF/engagement)

```bash
# Fast discovery + full nmap service/script scan
rustscan -a 10.10.10.5 --ulimit 5000 -- -sV -sC

# Save output
rustscan -a 10.10.10.5 --ulimit 5000 -- -sV -sC -oA scans/target
```

### Top 1000 ports only (quicker initial check)

```bash
rustscan -a 10.10.10.5 --top -- -sV
```

### Specific ports

```bash
# Known service ports
rustscan -a 10.10.10.5 -p 22,80,443,445,1433,3306,3389,5985 -- -sV -sC

# Port range
rustscan -a 10.10.10.5 --range 1-10000 -- -sV
```

### Subnet discovery (port only, no nmap)

```bash
# Open port list only — no nmap overhead
rustscan -a 10.0.0.0/24 --no-nmap --ulimit 5000 -b 2048 | tee open_ports.txt
```

### Aggressive OS + version + script (thorough)

```bash
rustscan -a 10.10.10.5 --ulimit 10000 -- -A -T4
```

### Stealth-ish (lower rate, avoid IDS triggering)

```bash
rustscan -a 10.10.10.5 -b 200 -t 3000 --ulimit 2000 -- -sV -T2
```

---

## Docker Usage (no install required)

```bash
# Basic scan
docker run -it --rm rustscan/rustscan:latest -a TARGET -- -sV -sC

# With output directory mounted
docker run -it --rm -v $(pwd)/scans:/scans rustscan/rustscan:latest -a TARGET -- -sV -oA /scans/target

# Network mode host (for LAN targets)
docker run -it --rm --network host rustscan/rustscan:latest -a 192.168.1.0/24 --no-nmap
```

---

## Output Parsing

RustScan outputs open ports first, then spawns nmap. Key patterns:

```
Open 10.10.10.5:22
Open 10.10.10.5:80
Open 10.10.10.5:443

# Then nmap runs automatically on found ports:
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 8.9p1
80/tcp  open  http    nginx 1.18.0
443/tcp open  ssl/http nginx 1.18.0
```

**Greppable output:**
```bash
rustscan -a TARGET --no-nmap -g | grep "Open"
```

---

## Performance Tuning

```bash
# Fastest possible (Linux, permissive ulimit)
ulimit -n 65535
rustscan -a TARGET -b 65535 -t 500 --ulimit 65535 -- -sV

# Moderate (reliable on most targets)
rustscan -a TARGET --ulimit 5000 -b 3000 -- -sV -sC

# Conservative (slow targets, firewalled, Windows hosts)
rustscan -a TARGET -b 500 -t 3000 --ulimit 2000 -- -sV
```

**Guideline:** increase `-b` and `--ulimit` together. High `--ulimit` + low `-b` wastes file descriptors.

---

## Integration Patterns

### rustscan → full nmap follow-up

```bash
# 1. Fast port discovery
rustscan -a TARGET --no-nmap | grep "Open" | awk -F: '{print $2}' | tr '\n' ',' | sed 's/,$//' > ports.txt

# 2. Deep nmap on discovered ports
nmap -sV -sC -p $(cat ports.txt) -oA TARGET_deep TARGET
```

### rustscan → masscan comparison

```bash
# rustscan: per-host, fast + nmap integration
rustscan -a 10.10.10.5 --ulimit 5000 -- -sV

# masscan: wide range, many hosts
masscan 10.0.0.0/24 -p1-65535 --rate 10000 -oL masscan.txt
```

### Subnet → per-host deep scan

```bash
# 1. Discover live hosts with open ports
rustscan -a 192.168.1.0/24 --no-nmap -b 1024 | grep "Open" | cut -d: -f1 | sort -u > live_hosts.txt

# 2. Deep scan each live host
while read host; do
  rustscan -a $host --ulimit 5000 -- -sV -sC -oA "scans/$host"
done < live_hosts.txt
```

---

## OPSEC Notes

- Scanning at high rate (`-b 4500+`) is **very noisy** — triggers IDS/IPS and firewall logs
- Use `-b 200 -t 3000` for slower, lower-noise scan on monitored targets
- `--scan-order Random` randomizes port order — slightly less fingerprint-able than serial
- RustScan nmap invocation shows in process list on attacker — minor concern
- From internal position (post-pivot): match scan rate to expected legitimate traffic

## Resources

| File | When to load |
|------|--------------|
| `references/scan-workflow-and-nmap-integration.md` | Output parsing, NSE scripts per service, firewall evasion, port state interpretation, service-to-tool pipeline table |
