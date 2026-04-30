# Amass — Config, Sources & Pipeline Reference

## Full Config File

```ini
# ~/.config/amass/config.ini

# Resolvers — use trusted public DNS
[resolvers]
resolver = 8.8.8.8
resolver = 1.1.1.1
resolver = 9.9.9.9

# Brute-force wordlist
[bruteforce]
enabled = true
wordlist = /usr/share/amass/wordlists/subdomains-top1mil-5000.txt
# or: /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt

# Scope — restrict to specific TLDs or CIDRs
[scope]
port = 80
port = 443

# Data source keys
[data_sources]

[data_sources.AlienVault]
[data_sources.AlienVault.Credentials]
apikey =

[data_sources.BinaryEdge]
[data_sources.BinaryEdge.Credentials]
apikey =

[data_sources.Censys]
[data_sources.Censys.Credentials]
username =
secret =

[data_sources.CertSpotter]
[data_sources.CertSpotter.Credentials]
apikey =

[data_sources.CIRCL]
[data_sources.CIRCL.Credentials]
username =
password =

[data_sources.GitHub]
[data_sources.GitHub.Credentials]
apikey =     # GitHub personal access token — finds subdomains in code

[data_sources.Hunter]
[data_sources.Hunter.Credentials]
apikey =

[data_sources.IntelX]
[data_sources.IntelX.Credentials]
apikey =

[data_sources.PassiveTotal]
[data_sources.PassiveTotal.Credentials]
username =
apikey =

[data_sources.SecurityTrails]
[data_sources.SecurityTrails.Credentials]
apikey =

[data_sources.Shodan]
[data_sources.Shodan.Credentials]
apikey =

[data_sources.URLScan]
[data_sources.URLScan.Credentials]
apikey =

[data_sources.VirusTotal]
[data_sources.VirusTotal.Credentials]
apikey =
```

## Wordlist Recommendations

| Wordlist | Size | Location |
|----------|------|----------|
| `subdomains-top1mil-5000.txt` | 5k | `/usr/share/amass/wordlists/` |
| `subdomains-top1million-5000.txt` | 5k | SecLists: `Discovery/DNS/` |
| `subdomains-top1million-20000.txt` | 20k | SecLists: `Discovery/DNS/` |
| `combined_subdomains.txt` | 650k | SecLists: `Discovery/DNS/` |
| `dns-Jhaddix.txt` | 86k | SecLists: `Discovery/DNS/` |

```bash
# Use specific wordlist
amass enum -d target.com -brute -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
```

## Passive Sources (no key needed)

AlienVault OTX, ArcticWolf, Ask, Baidu, Bing, BufferOver, CIRCL.lu, CommonCrawl, CrtSh, DNSRepo, DuckDuckGo, Entrust, GitHub (public), Google, HackerTarget, IntelX (free tier), Maltiverse, Mnemonic, NetworksDB, NSEC, PassiveTotal (free), Pgp, Rapiddns, RobtTex, Searchcode, Shodan (free), SiteDossier, Spyse, Sublist3rAPI, Threatbook, ThreatCrowd, ThreatMiner, Twitter, Umbrella, Urlscan, VirusTotal (free), Wayback, WhoisXML, Yahoo, ZoomEye

## Full Pipeline (Subdomain → Live Web → Vulnerabilities)

```bash
#!/bin/bash
DOMAIN="$1"
OUT="recon_${DOMAIN}"
mkdir -p "$OUT"

echo "[1] Amass passive enum"
amass enum -passive -d "$DOMAIN" -o "${OUT}/subs_amass.txt" -timeout 15 2>/dev/null

echo "[2] theHarvester passive"
theHarvester -d "$DOMAIN" -b crtsh,certspotter,hackertarget,dnsdumpster -l 500 -f "${OUT}/harvest" 2>/dev/null
grep -oE "([a-zA-Z0-9_-]+\\.)+${DOMAIN}" "${OUT}/harvest.xml" | sort -u > "${OUT}/subs_harvest.txt"

echo "[3] Merge + deduplicate"
cat "${OUT}/subs_amass.txt" "${OUT}/subs_harvest.txt" | sort -u > "${OUT}/all_subs.txt"
echo "[+] Unique subdomains: $(wc -l < "${OUT}/all_subs.txt")"

echo "[4] DNS resolution (dnsx)"
cat "${OUT}/all_subs.txt" | dnsx -silent -a -resp -o "${OUT}/resolved.txt" 2>/dev/null

echo "[5] HTTP probe (httpx)"
cat "${OUT}/resolved.txt" | awk '{print $1}' | httpx -silent -status-code -title -tech-detect \
  -o "${OUT}/web_services.txt" 2>/dev/null

echo "[6] Screenshot web services"
cat "${OUT}/web_services.txt" | cut -d' ' -f1 | eyewitness --urls - --web -d "${OUT}/screenshots/" --no-prompt 2>/dev/null

echo "[done] Results in ${OUT}/"
```

## Amass Database Queries

```bash
# After enumeration, query saved results
amass db -d target.com -names        # list discovered names
amass db -d target.com -show         # show full details
amass db -d target.com -ip           # show with IPs
amass db -d target.com -summary      # summary stats
```

## Track Changes Over Time

```bash
# First run
amass enum -d target.com -o baseline.txt

# Subsequent run
amass track -d target.com
# Reports new, removed, changed subdomains
```
