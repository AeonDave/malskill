# dnsx — DNS Records, Wordlists & Takeover Detection

## DNS Record Types

| Record | Purpose | Security Interest |
|--------|---------|-------------------|
| `A` | IPv4 address | Direct host discovery |
| `AAAA` | IPv6 address | IPv6 attack surface |
| `CNAME` | Canonical name alias | Subdomain takeover pivot |
| `MX` | Mail server | Email security, SPF bypass |
| `NS` | Name server | NS delegation/takeover |
| `TXT` | Arbitrary text | SPF/DKIM/DMARC, domain verification tokens |
| `PTR` | Reverse DNS | IP → hostname mapping |
| `SOA` | Zone authority | Zone transfer check |
| `SRV` | Service record | Internal service discovery |
| `CAA` | Cert Authority Auth | Which CA can issue certs |

## Extract All Record Types

```bash
# All records for a domain
dnsx -d target.com -a -aaaa -cname -mx -ns -txt -resp -json -o dns_full.json

# Parse JSON
cat dns_full.json | jq -r '[.host, .a[]?, .cname[]?, .mx[]?, .txt[]?] | @csv'

# Only TXT records (SPF/DKIM/DMARC)
dnsx -d target.com -txt -resp-only
# Look for:
#   v=spf1 ...
#   v=DMARC1 ...
#   p=DKIM ...
```

## Brute-Force Wordlists

| Wordlist | Size | Best For |
|----------|------|----------|
| `/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt` | 5k | Quick sweep |
| `/usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt` | 20k | Standard |
| `/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt` | 110k | Deep |
| `/usr/share/seclists/Discovery/DNS/bitquark-subdomains-top100000.txt` | 100k | Bitquark |
| `/usr/share/seclists/Discovery/DNS/n0kovo_subdomains.txt` | 3M | Comprehensive |
| `commonspeak2` | 2M | GitHub-derived |

```bash
# Download commonspeak2 (not in SecLists)
wget https://raw.githubusercontent.com/assetnote/commonspeak2-wordlists/master/subdomains/subdomains.txt -O commonspeak2.txt
```

## Custom Resolver Files

```bash
# Public fast resolvers
cat > resolvers.txt << 'EOF'
1.1.1.1
1.0.0.1
8.8.8.8
8.8.4.4
9.9.9.9
208.67.222.222
208.67.220.220
EOF

# Use shuffledns resolver list (curated + verified)
# https://github.com/janmasarik/resolvers — 1000+ public resolvers
wget https://raw.githubusercontent.com/janmasarik/resolvers/master/resolvers.txt
```

## Wildcard Detection

Wildcard = domain returns valid for any subdomain (e.g., `*.target.com → 1.2.3.4`).
dnsx detects by querying random subdomains and comparing responses.

```bash
# Auto-detect and filter wildcards
dnsx -d target.com -w wordlist.txt -wildcard -silent

# Adjust threshold (how many random probes to confirm wildcard)
dnsx -d target.com -w wordlist.txt -wildcard -wt 5

# Manual check
dig randomgarbage123456.target.com
# If it resolves → wildcard exists
```

## Subdomain Takeover Detection

CNAME pointing to deprovisioned service = potential takeover.

```bash
# Extract dangling CNAMEs
cat subs.txt | dnsx -cname -resp -silent > cnames.txt

# Find CNAMEs NOT pointing back to target
grep -v "target\.com" cnames.txt

# Check common takeover targets
# AWS S3: *.s3.amazonaws.com, *.s3-website-*.amazonaws.com
# GitHub Pages: *.github.io
# Heroku: *.herokudns.com
# Fastly: *.fastly.net
# Netlify: *.netlify.app
# Azure: *.azurewebsites.net, *.cloudapp.azure.com
# Shopify: *.myshopify.com
```

### Takeover Fingerprints

```bash
# Check if CNAME target is claimable
cat cnames.txt | while read line; do
  cname=$(echo $line | awk '{print $NF}')
  # Check if CNAME resolves
  if ! dig +short "$cname" | grep -q "."; then
    echo "[POTENTIAL TAKEOVER] $line"
  fi
done
```

Tools: [subjack](https://github.com/haccer/subjack), [nuclei takeover templates](https://github.com/projectdiscovery/nuclei-templates/tree/main/http/takeovers)

## Email Security Checks

```bash
# SPF — who can send email as this domain
dnsx -d target.com -txt -resp-only | grep "v=spf1"
# No SPF → email spoofing possible

# DMARC — policy for failed SPF/DKIM
dnsx -d _dmarc.target.com -txt -resp-only
# p=none → monitoring only (no enforcement)
# p=quarantine → spam
# p=reject → strict

# DKIM selectors (common: default, google, k1, selector1/2)
for sel in default google k1 selector1 selector2 mail; do
  dnsx -d "${sel}._domainkey.target.com" -txt -resp-only 2>/dev/null | grep -q "DKIM" && echo "Found: $sel"
done
```

## Zone Transfer Attempt

```bash
# Get NS records
dnsx -d target.com -ns -resp-only

# Try AXFR against each NS
dig AXFR target.com @ns1.target.com
# Success = misconfigured, dumps entire zone
```

## Pipeline: Mega DNS Recon

```bash
#!/bin/bash
TARGET=$1
OUT="dns_recon_${TARGET}"
mkdir -p "$OUT"

# Step 1: passive subdomain enum
subfinder -d "$TARGET" -silent -all -o "${OUT}/subs_passive.txt"

# Step 2: DNS brute-force
dnsx -d "$TARGET" -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  -silent -wildcard -o "${OUT}/subs_brute.txt"

# Step 3: merge + resolve
cat "${OUT}/subs_passive.txt" "${OUT}/subs_brute.txt" | sort -u | \
  dnsx -a -cname -resp -silent -o "${OUT}/resolved.txt"

# Step 4: extract IPs
cat "${OUT}/resolved.txt" | grep -oP '\d+\.\d+\.\d+\.\d+' | sort -u > "${OUT}/ips.txt"

# Step 5: reverse DNS
cat "${OUT}/ips.txt" | dnsx -ptr -resp-only > "${OUT}/ptr.txt"

echo "Done. Subdomains: $(wc -l < ${OUT}/resolved.txt)"
```
