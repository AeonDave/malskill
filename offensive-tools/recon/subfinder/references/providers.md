# Subfinder — Passive Sources & Provider Config

## Provider Config File

```yaml
# ~/.config/subfinder/provider-config.yaml

shodan:
  - YOUR_SHODAN_KEY
censys:
  - YOUR_CENSYS_ID:YOUR_CENSYS_SECRET
virustotal:
  - YOUR_VT_KEY
binaryedge:
  - YOUR_KEY
securitytrails:
  - YOUR_KEY
hunter:
  - YOUR_KEY
passivetotal:
  - YOUR_EMAIL:YOUR_KEY
intelx:
  - YOUR_KEY
github:
  - YOUR_GITHUB_TOKEN      # finds subdomains in code/commits
urlscan:
  - YOUR_KEY
chaos:
  - YOUR_KEY               # projectdiscovery chaos dataset
recon_dev:
  - YOUR_KEY
```

## Free Sources (No Key Required)

`alienvault`, `anubis`, `bufferover`, `c99`, `certspotter`, `crtsh`, `digitorus`, `dnsdumpster`, `dnsrepo`, `dnsspy`, `fullhunt` (free tier), `hackertarget`, `ipv4info`, `leakix`, `omnisint`, `quake`, `rapiddns`, `riddler`, `robtex`, `securitytrails` (free tier), `shrewdeye`, `sitedossier`, `sslmate`, `subdomainfinder`, `threatbook`, `threatcrowd`, `threatminer`, `waybackarchive`, `whoisxmlapi` (free tier)

## Recommended Minimal Key Set

For best coverage with minimal cost:

| Provider | Free Tier | Value |
|----------|-----------|-------|
| `shodan` | 100 results/query | IP + port data |
| `virustotal` | 4 req/min | Subdomain aggregation |
| `securitytrails` | 50 req/month | DNS + history |
| `github` | Personal token | Code search for subdomains |
| `chaos` | ProjectDiscovery key | Curated subdomain dataset |

## Comparing Coverage

```bash
# Compare subfinder vs amass vs other tools
subfinder -d target.com -silent -all -o subs_subfinder.txt
amass enum -passive -d target.com -o subs_amass.txt

# Merge and count
cat subs_subfinder.txt subs_amass.txt | sort -u > combined.txt
echo "Subfinder: $(wc -l < subs_subfinder.txt)"
echo "Amass: $(wc -l < subs_amass.txt)"
echo "Combined unique: $(wc -l < combined.txt)"
```

## Bulk Domain Enumeration

```bash
# provider-config.yaml set up
cat domains.txt | subfinder -silent -all -o all_subs.txt

# With rate limiting (avoid bans)
subfinder -dL domains.txt -silent -t 5 -timeout 30
```
