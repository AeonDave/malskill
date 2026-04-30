---
name: spiderfoot
description: "Automated OSINT platform with 200+ modules for target profiling: DNS, email, username, IP, ASN, breach data, dark web, social media, threat intel. Use when you need automated multi-source OSINT on a domain, IP, email, or username — runs all relevant modules and correlates results. CLI for scripting; web UI for interactive investigation."
license: MIT
compatibility: "Python 3.7+; pip install spiderfoot OR git clone github.com/smicallef/spiderfoot; Linux/macOS/Windows"
metadata:
  author: AeonDave
  version: "1.0"
---

# SpiderFoot

Automated OSINT platform — 200+ modules, correlates all data types around a target.

## Quick Start

```bash
git clone https://github.com/smicallef/spiderfoot
cd spiderfoot
pip install -r requirements.txt

# CLI scan on domain
python3 sf.py -s target.com -t INTERNET_NAME -o json -q

# Web UI (interactive)
python3 sf.py -l 127.0.0.1:5001
# → http://127.0.0.1:5001
```

## Target Types (`-t`)

| Type | Description | Example |
|------|-------------|---------|
| `INTERNET_NAME` | Hostname / domain | `target.com` |
| `IP_ADDRESS` | IPv4 address | `1.2.3.4` |
| `EMAILADDR` | Email address | `user@target.com` |
| `USERNAME` | Social username | `johndoe` |
| `PHONE_NUMBER` | Phone number | `+14151234567` |
| `HUMAN_NAME` | Person's name | `"John Doe"` |
| `NETBLOCK_OWNER` | ASN or CIDR | `AS12345` |
| `BGP_AS_OWNER` | ASN number | `12345` |
| `URL_FORM` | URL to scan | `https://target.com/login` |

## CLI Usage

```bash
# Domain scan — all passive modules
python3 sf.py -s target.com -t INTERNET_NAME -o json -q > results.json

# Email scan
python3 sf.py -s ceo@target.com -t EMAILADDR -o json -q

# Specific modules only
python3 sf.py -s target.com -t INTERNET_NAME -m sfp_dnsresolve,sfp_sublist3r,sfp_crtsh -o json -q

# List all modules
python3 sf.py -M

# List modules by type
python3 sf.py -M | grep -i "passive"
```

## Key CLI Flags

| Flag | Purpose |
|------|---------|
| `-s <target>` | Target value |
| `-t <type>` | Target type |
| `-m <modules>` | Specific modules (comma-separated) |
| `-o json/csv/tab` | Output format |
| `-q` | Quiet (no progress) |
| `-l <host:port>` | Start web UI |
| `-M` | List all modules |
| `--timeout <sec>` | Global timeout |

## Module Categories

```bash
# List all categories
python3 sf.py -M | awk '{print $1}' | sort -u

# Useful module groups
sfp_dnsresolve      # DNS resolution
sfp_crtsh           # Certificate transparency
sfp_sublist3r       # Subdomain enumeration
sfp_shodan          # Shodan integration (API key)
sfp_virustotal      # VirusTotal (API key)
sfp_hunter          # Hunter.io emails (API key)
sfp_emailharvest    # Email harvesting
sfp_haveibeenpwned  # Breach check (API key)
sfp_linkedin        # LinkedIn profiles
sfp_twitter         # Twitter profiles
sfp_github          # GitHub user/org data
sfp_pastebin        # Pastebin leaks
sfp_darkweb         # Dark web mentions (Tor)
sfp_threatintel     # Threat intelligence feeds
sfp_whois           # WHOIS data
```

## Web UI Workflow

```bash
python3 sf.py -l 127.0.0.1:5001
```

1. Browse to `http://127.0.0.1:5001`
2. New Scan → enter target + type
3. Select scan profile: **Passive**, **Investigate**, **Footprint**, **All**
4. Run → watch live graph of discovered entities
5. Browse results by data type: emails, IPs, subdomains, leaked credentials, social profiles
6. Export: JSON/CSV for downstream use

## Scan Profiles

| Profile | Modules | Use |
|---------|---------|-----|
| Passive | ~50 | No direct target contact |
| Investigate | ~100 | Mixed passive + active |
| Footprint | ~150 | Full external footprint |
| All | 200+ | Everything (loud) |

## API Key Configuration

```ini
# spiderfoot.db stores settings after first run
# Or configure via web UI: Settings → API Keys
```

High-value API keys:
```
Hunter.io       → email harvest
Shodan          → port/service data
VirusTotal      → malware/domain intel
HaveIBeenPwned  → breach lookup
SecurityTrails  → DNS history
IntelX          → dark web / leaks
```

## Parse JSON Output

```python
import json

with open("results.json") as f:
    results = json.load(f)

# Group by data type
from collections import defaultdict
by_type = defaultdict(list)
for item in results:
    by_type[item["type"]].append(item["data"])

# Print emails found
for email in set(by_type.get("EMAILADDR", [])):
    print(email)

# Print subdomains
for sub in set(by_type.get("INTERNET_NAME", [])):
    print(sub)
```

## Resources

| File | When to load |
|------|--------------|
| `references/modules.md` | Full module list with descriptions, API requirements, and recommended scan configurations |
