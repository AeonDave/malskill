---
name: dnsx
description: "Fast DNS resolution and brute-force tool from ProjectDiscovery. Use when asked to resolve a list of subdomains, perform DNS brute-force, extract DNS records (A, CNAME, MX, TXT, NS), or validate live DNS entries from a large list."
license: MIT
compatibility: "Linux, Windows, macOS. Install: go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest or download binary."
metadata:
  author: AeonDave
  version: "1.0"
---

# dnsx

Fast DNS toolkit — resolve, brute-force, and extract DNS records at scale.

## Quick Start

```bash
# Resolve a list of subdomains
cat subs.txt | dnsx

# DNS brute-force against a domain
dnsx -d example.com -w wordlist.txt

# Extract A records with response
cat subs.txt | dnsx -a -resp
```

## Core Flags

| Flag | Description |
|------|-------------|
| `-l <file>` | Input list of hosts/subdomains |
| `-d <domain>` | Target domain (for brute-force) |
| `-w <wordlist>` | Wordlist for brute-force |
| `-a` | Query A records |
| `-aaaa` | Query AAAA records |
| `-cname` | Query CNAME records |
| `-mx` | Query MX records |
| `-ns` | Query NS records |
| `-txt` | Query TXT records |
| `-ptr` | Query PTR records |
| `-resp` | Show DNS response |
| `-resp-only` | Show DNS response only |
| `-rcode <code>` | Filter by rcode (e.g., `noerror,nxdomain`) |
| `-r <resolvers>` | Custom resolver file |
| `-rl <n>` | Rate limit (requests/second) |
| `-t <n>` | Threads (default 100) |
| `-timeout <n>` | Timeout (default 5s) |
| `-silent` | Print results only |
| `-o <file>` | Output file |
| `-json` | JSON output |
| `-wildcard` | Filter wildcard subdomains |

## Common Workflows

```bash
# Pipeline: subfinder -> dnsx resolution
subfinder -d target.com -silent | dnsx -silent

# DNS brute-force with wordlist
dnsx -d target.com -w /usr/share/dnsrecon/subdomains-top1mil-5000.txt -t 50

# Get all record types in JSON
cat subs.txt | dnsx -a -cname -mx -txt -resp -o dns_records.json -json

# Resolve IPs for a list
cat domains.txt | dnsx -a -resp-only | sort -u

# Filter wildcard results
cat subs.txt | dnsx -wildcard -d target.com -silent

# Reverse DNS (PTR) on IPs
cat ips.txt | dnsx -ptr -resp-only
```

## Resources

| File | When to load |
|------|--------------|
| `references/dns-records.md` | DNS record types, brute-force wordlists, wildcard detection |
