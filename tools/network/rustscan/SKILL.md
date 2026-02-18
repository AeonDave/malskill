---
name: rustscan
description: "RustScan: modern port scanner that finds open ports in seconds then pipes results directly into nmap for service/version detection. Use when you need fast port discovery with automatic nmap handoff, especially against individual hosts or small ranges."
license: MIT
compatibility: "Linux / macOS / Windows. Install via cargo, package manager, or Docker. Requires nmap."
metadata:
  author: AeonDave
  version: "1.0"
---

# RustScan

Fast port scanner with built-in nmap pipeline.

## Quick Start

```bash
rustscan -a 10.10.10.5 -- -sV -sC
rustscan -a 10.10.10.5 -p 22,80,443,445 -- -A
rustscan -a 10.10.10.0/24 --ulimit 5000 -- -sV
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-a <addr>` | Target IP, CIDR, or hostname |
| `-p <ports>` | Specific ports |
| `--ulimit` | File descriptor limit (higher = faster) |
| `-b <batch>` | Batch size for simultaneous probes |
| `-t <ms>` | Timeout per port in ms |
| `--no-nmap` | Skip nmap, list open ports only |
| `-- <nmap flags>` | Flags passed directly to nmap |

## Common Workflows

### Full service scan
```bash
rustscan -a 192.168.1.100 --ulimit 5000 -- -sV -sC -O
```

### Discovery only
```bash
rustscan -a 10.0.0.0/24 --no-nmap -b 1024 | tee open_ports.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Tuning and Docker usage |
