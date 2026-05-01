---
name: asnmap
description: "ProjectDiscovery tool for mapping IP ranges from ASN data. Given a domain, IP, organization name, or ASN number, returns all associated CIDR ranges. Use during passive recon to discover the full IP space owned by a target organization before port sweeping, and to identify cloud vs. on-prem allocation."
license: MIT
compatibility: "Linux/macOS/Windows; Go binary. Requires network access for ASN API queries."
metadata:
  author: AeonDave
  version: "1.0"
---

# asnmap

Map an organization's full IP space from ASN data. Feeds directly into masscan/nmap scopes.

## Quick start

```bash
# Domain → ASN → IP ranges
asnmap -d target.com

# IP → ASN → all ranges for that ASN
asnmap -i 1.2.3.4

# Organization name → all ASNs and ranges
asnmap -org "Target Corporation"

# ASN number → CIDR ranges
asnmap -a AS12345

# Output CIDR list for tool consumption
asnmap -d target.com -o cidr_ranges.txt
```

## Input modes

```bash
# Multiple domains
asnmap -d target.com,sub.target.com

# From file
asnmap -list domains.txt -o ranges.txt

# Multiple IPs
asnmap -i 1.2.3.4,5.6.7.8

# Org name (fuzzy match against WHOIS data)
asnmap -org "Target Inc" -json
```

## Output formats

```bash
# Plain CIDR list (default)
asnmap -d target.com
# → 1.2.3.0/24
# → 10.0.0.0/16

# JSON output (includes ASN metadata)
asnmap -d target.com -json

# Silent mode (CIDRs only, no banners)
asnmap -d target.com -silent

# CSV output
asnmap -d target.com -csv
```

## Pipeline integration

```bash
# Full pipeline: domain → CIDRs → masscan port sweep
asnmap -d target.com -silent | masscan --ports 80,443,8080,8443 -iL - --rate 5000

# CIDRs → nmap (small ranges only — use masscan for large ranges)
asnmap -d target.com -silent | nmap -iL - -sV --top-ports 100

# CIDRs → shodan API query
asnmap -d target.com -silent | while read cidr; do
  shodan search "net:$cidr"
done

# Discover all subdomains per IP range (reverse DNS)
asnmap -d target.com -silent | dnsx -resp-only -ptr -o ptr_records.txt
```

## CDN and cloud filtering

Before scanning, filter out CDN and cloud provider IP ranges to avoid wasting time on shared infrastructure.

```bash
# Download cloud provider CIDR lists
curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | jq -r '.prefixes[].ip_prefix' > aws_ranges.txt
curl -s https://www.gstatic.com/ipranges/cloud.json | jq -r '.prefixes[].ipv4Prefix // empty' > gcp_ranges.txt

# Filter target ranges against cloud provider lists (remove overlaps)
asnmap -d target.com -silent > target_ranges.txt

# Use cdncheck to tag CDN-hosted IPs before scanning
cat target_ips.txt | cdncheck -resp -o cdncheck_results.txt
```

Cloud-hosted ranges are valid targets, but:
- Scanning Cloudflare/Akamai origin IPs leaks your source to CDN logs.
- Scanning shared cloud ranges may hit other tenants — check authorization scope.

## ASN investigation workflow

```bash
# 1. Find all ASNs for a domain
asnmap -d target.com -json | jq '.asn'

# 2. For each ASN, get full CIDR list
asnmap -a AS12345 -silent

# 3. Check if ranges are consistent with WHOIS
whois AS12345

# 4. Look for additional ASNs via BGP neighbors
# Check: https://bgp.he.net/AS12345#_peers

# 5. Cross-reference against Shodan (passive)
shodan search "asn:AS12345" --fields ip_str,port,org
```

## OPSEC notes

- asnmap queries public ASN databases (WHOIS, BGP sources) — passive, no target contact.
- Combine with `cdncheck` to tag CDN-hosted IPs before active scanning.
- Large organizations may have dozens of ASNs across regions — always run org name search in addition to domain lookup.
- Cloud provider subnets change frequently — pull fresh CIDR lists before each engagement.
