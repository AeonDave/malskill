# Shodan — Search Filters, Dork Recipes & API Integration

## Full Filter Reference

| Filter | Type | Example |
|--------|------|---------|
| `hostname:` | String | `hostname:target.com` |
| `ip:` | CIDR | `ip:1.2.3.0/24` |
| `net:` | CIDR | `net:203.0.113.0/24` |
| `org:` | String | `org:"Target Corp"` |
| `asn:` | String | `asn:AS12345` |
| `port:` | Int | `port:8443` |
| `product:` | String | `product:nginx` |
| `version:` | String | `version:1.14.0` |
| `country:` | ISO | `country:US` |
| `city:` | String | `city:"New York"` |
| `os:` | String | `os:Windows` |
| `vuln:` | CVE | `vuln:CVE-2021-44228` |
| `http.title:` | String | `http.title:"admin panel"` |
| `http.html:` | String | `http.html:"login"` |
| `http.status:` | Int | `http.status:200` |
| `http.favicon.hash:` | Int | `http.favicon.hash:-247388890` |
| `ssl:` | String | `ssl:"target.com"` |
| `ssl.cert.subject.cn:` | String | `ssl.cert.subject.cn:"target.com"` |
| `ssl.cert.issuer.cn:` | String | `ssl.cert.issuer.cn:"Let's Encrypt"` |
| `ssl.cert.fingerprint:` | Hash | `ssl.cert.fingerprint:"AA:BB:..."` |
| `before:` | Date | `before:2024-01-01` |
| `after:` | Date | `after:2023-01-01` |
| `has_screenshot:` | Bool | `has_screenshot:true` |

## Dork Recipes

### Infrastructure Discovery

```
# All open ports for an org
org:"Target Corp"

# Specific product in org
org:"Target Corp" product:Apache

# Jenkins instances (common unauth RCE target)
http.title:"Dashboard [Jenkins]"
product:Jenkins country:US

# Admin panels
http.title:"admin" http.status:200
http.title:"administration" -country:CN

# Database admin panels
http.title:"phpMyAdmin" country:IT
http.title:"Adminer" http.status:200

# Exposed Grafana
http.title:"Grafana" http.status:200

# GitLab instances
http.title:"GitLab" http.status:200
```

### Vulnerability Research

```
# Hosts with specific CVE
vuln:CVE-2021-44228
vuln:CVE-2017-0144    # EternalBlue

# Old Apache versions
product:Apache version:2.4.49
product:Apache version:2.4.50

# Exposed .git repos
http.html:".git" http.status:200

# Default credentials / weak auth
http.title:"Login" http.status:401 product:Cisco
```

### SSL/TLS Pivoting

```
# Find all hosts on same SSL cert (multi-domain pivot)
ssl:"target.com"

# Self-signed certs for an org
ssl.cert.issuer.cn:"target.com" ssl.cert.subject.cn:"target.com"

# Certificate transparency pivot
ssl.cert.subject.cn:"*.target.com"
```

### Favicon Hash Pivot (identify vendor/product)

```bash
# Step 1: get hash via httpx
httpx -u https://target.com -favicon
# or via Python
python3 -c "
import requests, mmh3, codecs
r = requests.get('https://target.com/favicon.ico', verify=False)
h = mmh3.hash(codecs.lookup('base64').encode(r.content)[0])
print('http.favicon.hash:', h)
"

# Step 2: search Shodan
shodan search "http.favicon.hash:-247388890"
```

## Python API Integration

```python
import shodan

api = shodan.Shodan("YOUR_API_KEY")

# Search
results = api.search('org:"Target Corp"')
for r in results['matches']:
    print(f"{r['ip_str']}:{r['port']} - {r.get('product','')}")

# Host lookup
host = api.host("1.2.3.4")
print(host['org'], host['country_name'])
for item in host['data']:
    print(f"  Port: {item['port']}, Product: {item.get('product','')}")

# Stream new results matching filter (needs enterprise)
for banner in api.stream.banners():
    print(banner)
```

## Shodan CLI Tips

```bash
# Download all results (consume query credits)
shodan download results org:"Target Corp" port:443
# Creates results.json.gz

# Parse only IPs and ports
shodan parse --fields ip_str,port results.json.gz | sort -u

# Parse with products
shodan parse --fields ip_str,port,product results.json.gz

# Stats breakdown (no credits)
shodan stats --facets port,product,country org:"Target Corp"
```

## Free API vs Paid

| Feature | Free | Paid |
|---------|------|------|
| Search results | 100 | Unlimited |
| Download | No | Yes |
| Filters | Limited | All |
| Alerting | No | Yes |
| History | No | Yes |
| Query credits/month | 100 | 10,000+ |
