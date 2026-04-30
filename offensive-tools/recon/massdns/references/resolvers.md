# MassDNS — Resolvers, Rate Tuning & puredns Integration

## Resolver List Sources

| Source | Count | Notes |
|--------|-------|-------|
| massdns built-in (`lists/resolvers.txt`) | ~1700 | Included in repo, pre-verified |
| [janmasarik/resolvers](https://github.com/janmasarik/resolvers) | 1000+ | Community maintained, tested |
| [trickest/resolvers](https://github.com/trickest/resolvers) | 5000+ | Large, regularly verified |
| [proabiral/fresh-resolvers](https://github.com/proabiral/fresh-resolvers) | Varies | Fresh daily |

```bash
# Download trickest resolvers
wget https://raw.githubusercontent.com/trickest/resolvers/main/resolvers.txt -O resolvers.txt

# Verify resolver list (massdns script)
./scripts/resolvability_whitelist.sh
```

## Rate Tuning

| Scenario | `-s` value | Notes |
|----------|-----------|-------|
| Local lab | 5000+ | No limits |
| Standard | 500 | Default, safe |
| Slow resolvers | 100-200 | Reduce SERVFAIL rate |
| Rate-sensitive | 50-100 | External targets |

```bash
# Standard
massdns -r resolvers.txt -t A subs.txt -s 500 -o S 2>/dev/null

# Conservative
massdns -r resolvers.txt -t A subs.txt -s 100 --resolvers-rnd -o S 2>/dev/null

# Max speed (local/internal)
massdns -r resolvers.txt -t A subs.txt -s 10000 -o S 2>/dev/null
```

## Wildcard Detection

Wildcards = domains that resolve any subdomain. Must filter before massdns.

```bash
# Manual check
dig randomtest123456abc.target.com
# Resolves → wildcard exists

# massdns wildcard script
python3 scripts/wildcard.py target.com resolvers.txt

# puredns handles wildcard filtering automatically (recommended)
puredns bruteforce wordlist.txt target.com -r resolvers.txt
```

## puredns Integration (Recommended Wrapper)

[puredns](https://github.com/d3mondev/puredns) wraps massdns with:
- Wildcard detection + filtering
- Public resolver validation
- Result deduplication
- Rate limiting

```bash
# Install
go install github.com/d3mondev/puredns/v2@latest

# Brute-force with wildcard filtering
puredns bruteforce /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  target.com \
  -r resolvers.txt \
  --write valid_subs.txt

# Resolve existing list
puredns resolve subs.txt -r resolvers.txt --write resolved.txt

# Use trusted resolvers for final verification
puredns bruteforce wordlist.txt target.com \
  -r resolvers.txt \
  --resolvers-trusted trusted.txt

# trusted.txt: 8.8.8.8, 1.1.1.1, 9.9.9.9 — small set, authoritative
```

## Output Processing

```bash
# Simple output (default: massdns -o S)
# Format: name. TTL type data
# sub.target.com. 300 A 1.2.3.4

# Extract A record IPs
grep " A " resolved.txt | awk '{print $3}' | sort -u > ips.txt

# Extract only resolved names
grep " A " resolved.txt | awk '{print $1}' | sed 's/\.$//' | sort -u > live_subs.txt

# JSON output processing
massdns -r resolvers.txt -t A subs.txt -o J 2>/dev/null | \
  jq -r 'select(.data.answers != null) |
    .name + " " + (.data.answers[0].data // "")' | \
  grep -v "^$"

# Filter NXDOMAIN/SERVFAIL
massdns ... | grep -v "NXDOMAIN\|SERVFAIL\|REFUSED"
```

## Full Pipeline: Brute + Resolve + Screenshot

```bash
#!/bin/bash
TARGET=$1
RESOLVERS="resolvers.txt"

# Step 1: passive enum
subfinder -d "$TARGET" -silent -all -o passive.txt

# Step 2: brute-force + resolve (puredns handles wildcards)
puredns bruteforce \
  /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  "$TARGET" -r "$RESOLVERS" \
  --write brute.txt 2>/dev/null

# Step 3: merge
cat passive.txt brute.txt | sort -u > all_subs.txt

# Step 4: final resolution
puredns resolve all_subs.txt -r "$RESOLVERS" \
  --write live_subs.txt 2>/dev/null

# Step 5: live HTTP check
cat live_subs.txt | httpx -silent -status-code -title -o live_http.txt

echo "Live subdomains: $(wc -l < live_subs.txt)"
echo "HTTP services: $(wc -l < live_http.txt)"
```

## Comparison: massdns vs dnsx

| Feature | massdns | dnsx |
|---------|---------|------|
| Speed | Extremely fast (C) | Fast (Go) |
| Wildcard filter | Manual/scripts | Built-in (`-wildcard`) |
| Record types | Any | Any |
| Output formats | S/J/L/F | Text/JSON |
| Pipeline (stdin) | File-based | stdin/stdout |
| Part of PD stack | No | Yes (projectdiscovery) |

**Use massdns/puredns** for: massive brute-force (millions of names), fastest raw resolution
**Use dnsx** for: pipeline integration with subfinder/httpx, record extraction, ASN/CDN info
