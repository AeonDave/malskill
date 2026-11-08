---
name: massdns
description: "Auth/lab ref: High-performance DNS resolver for bulk subdomain resolution. For you have a large subdomain list and need to resolve all entries quickly using public resolvers."
license: MIT
compatibility: "C; Linux/macOS; build from source."
metadata:
  author: AeonDave
  version: "1.1"
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
| `-s N` | Concurrent lookups (default: 10000) |
| `--root` | Do not drop privileges when running as root (not recommended) |
| `--verify-ip` | Verify source IP addresses of incoming replies |
| `--flush` | Flush output file after each response |
| `-q` | Quiet mode |
| `--status-format <fmt>` | Status line format |
| `--retry` | Specify unacceptable DNS response codes to retry |

## Output Formats

| Flag | Format | Example Output |
|------|--------|----------------|
| `-o S` | Simple (default) | `sub.target.com. A 1.2.3.4` |
| `-o J` | JSON | Full DNS response JSON |
| `-o L` | List | `sub.target.com` (only names) |
| `-o F` | Full | All DNS fields |

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

**DNS brute-force (generate + resolve):**
```bash
# Generate permutations with puredns or subfinder, then resolve at scale
subfinder -d target.com -silent -all | \
  massdns -r lists/resolvers.txt -t A -o S 2>/dev/null | \
  grep -v "NXDOMAIN\|SERVFAIL" > resolved.txt
```

**CNAME hunting for subdomain takeover:**
```bash
massdns -r lists/resolvers.txt -t CNAME subs.txt -o J 2>/dev/null | \
  jq -r 'select(.answers[0].type=="CNAME") | "\(.name) \(.answers[0].data)"' | \
  grep -v "target\.com"
```

**MX record enumeration:**
```bash
massdns -r lists/resolvers.txt -t MX domains.txt -o S 2>/dev/null | \
  grep " MX " | sort -u
```

`-s` limits concurrent lookups, not requests per second. Choose resolvers and concurrency appropriate for the authorized workload.

## Resources

| File | When to load |
|------|--------------|
| `references/resolvers.md` | Resolver list sources, rate tuning, wildcard handling, puredns integration |
