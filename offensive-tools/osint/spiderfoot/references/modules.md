# SpiderFoot — Module Reference & Scan Configurations

## Recommended Module Sets by Use Case

### Subdomain + Infrastructure Discovery

```bash
python3 sf.py -s target.com -t INTERNET_NAME \
  -m sfp_dnsresolve,sfp_crtsh,sfp_sublist3r,sfp_hackertarget,sfp_dnsdumpster,sfp_threatcrowd,sfp_virustotal \
  -o json -q
```

### Email Harvest + Breach Check

```bash
python3 sf.py -s target.com -t INTERNET_NAME \
  -m sfp_emailharvest,sfp_hunter,sfp_haveibeenpwned,sfp_dehashed,sfp_emailformat \
  -o json -q
```

### Person Profile (from username)

```bash
python3 sf.py -s johndoe -t USERNAME \
  -m sfp_accounts,sfp_twitter,sfp_linkedin,sfp_github,sfp_keybase \
  -o json -q
```

### Threat Intel on IP

```bash
python3 sf.py -s 1.2.3.4 -t IP_ADDRESS \
  -m sfp_ipinfo,sfp_shodan,sfp_abuseipdb,sfp_threatintel,sfp_virustotal,sfp_bgpview \
  -o json -q
```

## Full Module List (Key Modules)

### DNS / Network

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_dnsresolve` | Resolve hostnames to IPs | No |
| `sfp_crtsh` | Certificate transparency | No |
| `sfp_sublist3r` | Subdomain enum aggregator | No |
| `sfp_hackertarget` | HackerTarget API | No |
| `sfp_dnsdumpster` | DNSDumpster passive | No |
| `sfp_dnsBrute` | DNS brute force | No |
| `sfp_shodan` | Port/service data | Yes |
| `sfp_censys` | Censys port data | Yes |
| `sfp_bgpview` | ASN/BGP data | No |
| `sfp_ipinfo` | IP geolocation + ASN | No |
| `sfp_whois` | WHOIS records | No |
| `sfp_whoisxml` | WhoisXML API | Yes |

### Email

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_emailharvest` | Email from search engines | No |
| `sfp_emailformat` | Email format guessing | No |
| `sfp_hunter` | Hunter.io email finder | Yes |
| `sfp_haveibeenpwned` | Breach lookup | Yes |
| `sfp_dehashed` | Breach data | Yes |
| `sfp_emailrep` | Email reputation | No |

### Social Media

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_accounts` | Check 200+ social sites | No |
| `sfp_twitter` | Twitter profile data | No |
| `sfp_linkedin` | LinkedIn profiles | No |
| `sfp_github` | GitHub user/org data | No |
| `sfp_keybase` | Keybase identity verification | No |
| `sfp_instagram` | Instagram profiles | No |

### Threat Intelligence

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_virustotal` | VirusTotal domain/IP | Yes |
| `sfp_threatintel` | Threat intel feeds | No |
| `sfp_abuseipdb` | AbuseIPDB | Yes |
| `sfp_alienvault` | AlienVault OTX | No |
| `sfp_cymon` | Cymon threat feed | No |
| `sfp_maltiverse` | Maltiverse threat intel | No |
| `sfp_fraudguard` | FraudGuard IP check | No |

### Dark Web / Leaks

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_darkweb` | Dark web mentions | Tor |
| `sfp_pastebin` | Pastebin leaks | No |
| `sfp_intelx` | IntelX leaked data | Yes |
| `sfp_rocketreach` | RocketReach profiles | Yes |

### Web Content

| Module | Description | Key Needed |
|--------|-------------|-----------|
| `sfp_spider` | Web crawler | No |
| `sfp_webframework` | Detect web frameworks | No |
| `sfp_robots` | robots.txt analysis | No |
| `sfp_webanalytics` | Analytics tags (GA ID, etc.) | No |
| `sfp_googlesafebrowsing` | Google Safe Browsing | Yes |
| `sfp_urlscan` | URLScan.io | Yes |
| `sfp_wayback` | Wayback Machine | No |

## Result Data Types

| Type | Description |
|------|-------------|
| `INTERNET_NAME` | Hostname / subdomain |
| `IP_ADDRESS` | IPv4 |
| `IPV6_ADDRESS` | IPv6 |
| `EMAILADDR` | Email address |
| `PHONE_NUMBER` | Phone |
| `USERNAME` | Social username |
| `SOCIAL_MEDIA` | Social profile URL |
| `ACCOUNT_EXTERNAL_OWNED` | Confirmed account |
| `LEAKED_CREDENTIAL` | Breach data |
| `DOMAIN_WHOIS` | WHOIS record |
| `TCP_PORT_OPEN` | Open port |
| `VULNERABILITY_CVE_CRITICAL` | Critical CVE |
| `LINKED_URL_INTERNAL` | Internal URLs |
| `WEB_TECHNOLOGY` | Tech stack |
| `GEOINFO` | Geographic info |

## Automation Script

```python
import subprocess, json

def spiderfoot_scan(target, target_type, modules=None, output_file="sf_results.json"):
    cmd = ["python3", "sf.py", "-s", target, "-t", target_type, "-o", "json", "-q"]
    if modules:
        cmd += ["-m", ",".join(modules)]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/path/to/spiderfoot")

    with open(output_file, "w") as f:
        f.write(result.stdout)

    return json.loads(result.stdout) if result.stdout else []

# Usage
results = spiderfoot_scan(
    "target.com", "INTERNET_NAME",
    modules=["sfp_dnsresolve", "sfp_crtsh", "sfp_emailharvest"]
)
emails = [r["data"] for r in results if r["type"] == "EMAILADDR"]
```
