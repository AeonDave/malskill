---
name: massdns
description: "High-performance DNS resolver for bulk subdomain resolution. Use when you have a large subdomain list and need to resolve all entries quickly using public resolvers."
license: MIT
compatibility: "C; Linux/macOS; build from source; github.com/blechschmidt/massdns"
metadata:
  author: AeonDave
  version: "1.0"
---

# MassDNS

High-speed DNS bulk resolver — resolve millions of subdomains per minute.

## Quick Start

```bash
git clone https://github.com/blechschmidt/massdns
cd massdns && make

# Resolve subdomain list
./bin/massdns -r resolvers.txt -t A subdomains.txt -o S -w resolved.txt

# Built-in resolver list
./bin/massdns -r lists/resolvers.txt -t A subdomains.txt -o S > resolved.txt
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-r FILE` | Resolver list file |
| `-t TYPE` | DNS type (A/AAAA/MX/NS/CNAME) |
| `-o FORMAT` | Output format (S=simple, J=JSON, L=list) |
| `-w FILE` | Write output to file |
| `-s N` | Concurrent resolvers |
| `--root` | Use root server for NS lookups |
| `--verify-ip` | Verify A record IPs |

## Common Workflows

**Subdomain enumeration pipeline:**
```bash
# Generate candidates with subfinder
subfinder -d target.com -silent -o subs.txt

# Resolve with massdns
./bin/massdns -r lists/resolvers.txt -t A subs.txt -o S | grep -v NXDOMAIN > live.txt
```

**Extract live IPs:**
```bash
cat resolved.txt | grep " A " | awk '{print $3}' | sort -u > ips.txt
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Resolver list sources and rate tuning |
