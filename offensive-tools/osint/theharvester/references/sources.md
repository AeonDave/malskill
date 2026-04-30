# theHarvester — Sources, API Keys & Integration

## Full Source List

| Source | Type | Key Required | Best for |
|--------|------|-------------|---------|
| `google` | Search engine | No | General emails, mentions |
| `bing` | Search engine | No | Emails, hosts |
| `yahoo` | Search engine | No | Emails |
| `duckduckgo` | Search engine | No | General |
| `baidu` | Search engine | No | Chinese targets |
| `crtsh` | Certificate transparency | No | Subdomains |
| `certspotter` | Certificate transparency | No | Subdomains |
| `dnsdumpster` | DNS | No | Subdomains, DNS records |
| `hackertarget` | DNS | No | Subdomains |
| `rapiddns` | DNS | No | Subdomains |
| `sublist3r` | DNS aggregator | No | Subdomains |
| `hunter` | Email finder | Yes (hunter.io) | Emails + pattern |
| `securitytrails` | DNS/IP history | Yes | Subdomains, IP history |
| `shodan` | Port scan | Yes | Open ports, banners |
| `censys` | Port scan | Yes | Open ports, certs |
| `virustotal` | Malware/DNS | Yes | Subdomains |
| `intelx` | Dark web/leaks | Yes | Leaked data |
| `linkedin` | Social | No (rate limited) | Employee names/titles |
| `fullhunt` | Attack surface | Yes | Subdomains, open ports |
| `bevigil` | Mobile OSINT | Yes | Subdomains from APKs |
| `binaryedge` | Internet scan | Yes | Ports, services |

## API Key Setup

```bash
# File location (choose one):
# /etc/theHarvester/api-keys.yaml  (system-wide)
# ~/.theHarvester/api-keys.yaml    (user)
```

```yaml
apikeys:
  hunter:
    key: ""           # hunter.io — free: 50 searches/month
  securitytrails:
    key: ""           # securitytrails.com — free: 50/month
  shodan:
    key: ""           # shodan.io — free (limited)
  censys:
    id: ""
    secret: ""        # censys.io — free: 250 queries/month
  virustotal:
    key: ""           # virustotal.com — free
  intelx:
    key: ""           # intelx.io — free tier
  fullhunt:
    key: ""           # fullhunt.io — free: 10/day
  binaryedge:
    key: ""           # binaryedge.io — paid
  bevigil:
    key: ""           # bevigil.com — free tier
```

## Recommended Source Combinations

```bash
# Fastest passive (no keys, low noise)
-b google,bing,crtsh,certspotter,dnsdumpster

# Best subdomain coverage (no keys)
-b crtsh,certspotter,dnsdumpster,hackertarget,rapiddns,sublist3r

# Best email coverage (with hunter key)
-b google,bing,linkedin,hunter,intelx

# Maximum coverage (all keys configured)
-b all
```

## Output Parsing Scripts

```bash
# Emails only (from XML)
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('results.xml')
for el in tree.iter('email'):
    print(el.text)
" | sort -u > emails.txt

# Subdomains only
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('results.xml')
for el in tree.iter('host'):
    print(el.text)
" | sort -u > subdomains.txt

# Quick grep alternative
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' results.xml | sort -u
grep -oE '([a-zA-Z0-9_-]+\.)+target\.com' results.xml | sort -u
```

## Integration Pipeline

```bash
#!/bin/bash
# Full passive recon pipeline
DOMAIN="$1"

echo "[1] theHarvester — passive harvest"
theHarvester -d "$DOMAIN" -b google,bing,crtsh,certspotter,dnsdumpster,hackertarget \
  -l 500 -f "harvest_${DOMAIN}" 2>/dev/null

echo "[2] Extract artifacts"
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "harvest_${DOMAIN}.xml" | sort -u > emails.txt
grep -oE '([a-zA-Z0-9_-]+\.)+'"$DOMAIN" "harvest_${DOMAIN}.xml" | sort -u > subdomains.txt

echo "[3] Holehe on emails"
while read email; do
  holehe "$email" --only-used --json >> holehe_results.json 2>/dev/null
done < emails.txt

echo "[4] Amass on domain (passive)"
amass enum -passive -d "$DOMAIN" -o amass_subdomains.txt 2>/dev/null

echo "[5] Merge subdomains"
cat subdomains.txt amass_subdomains.txt | sort -u > all_subdomains.txt
echo "[+] Total subdomains: $(wc -l < all_subdomains.txt)"
echo "[+] Total emails: $(wc -l < emails.txt)"
```
