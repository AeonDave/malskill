# Active Recon — Deep Dive

Active recon makes direct contact with target infrastructure. Target-side logs will record probes.
Always confirm authorization scope and rate limits before starting.

---

## DNS resolution and validation

Before spending time on dead hosts, resolve the passive subdomain list to live IPs.

### Wildcard detection

Wildcard DNS (`*.target.com → 1.2.3.4`) pollutes subdomain lists with false positives.
Detect before bulk resolution:

```bash
# Query a random subdomain — if it resolves, wildcard is active
dig DOES-NOT-EXIST-ABCXYZ.target.com A

# dnsx wildcard detection
dnsx -l subdomains.txt -wd target.com -o resolved.txt
```

### Bulk resolution

```bash
# dnsx — resolve, filter wildcards, output live hosts
dnsx -l subdomains.txt -resp -wd target.com -o resolved.txt

# massdns — high-throughput resolution
massdns -r resolvers.txt -t A -o S subdomains.txt > resolved_raw.txt
```

Use public resolver lists (e.g., from `public-dns.info`) for massdns — do not use the target's own resolvers.

### DNS record types to query

| Record | Value |
|--------|-------|
| A / AAAA | Live IPv4/IPv6 — primary target list |
| MX | Mail servers — phishing surface, SMTP auth |
| TXT | SPF, DKIM, DMARC, verification tokens (reveal cloud providers) |
| CNAME | Subdomain takeover candidates (dangling CNAME → defunct provider) |
| NS | Nameserver — useful for zone transfer attempts (rare success) |

```bash
# Check all record types for a subdomain
dnsx -l subdomains.txt -a -aaaa -cname -mx -txt -resp -o full_dns.txt
```

### Subdomain takeover candidates

CNAME pointing to an unclaimed cloud service is a takeover vector.

- `sub.target.com CNAME foo.s3.amazonaws.com` → S3 bucket unclaimed → claim it
- Common providers: GitHub Pages, Heroku, AWS S3, Azure blob, Fastly, Shopify

Tools: `subjack`, `nuclei -t takeovers/`.

### Active DNS brute-force and permutation expansion

After resolving the passive subdomain list, expand it with active brute-force. Two strategies compound each other:

**1. Wordlist brute-force**

```bash
# puredns — brute-force with resolver validation and wildcard filtering
puredns bruteforce /path/to/subdomains.txt target.com \
  --resolvers resolvers-trusted.txt -w brute_results.txt

# shuffledns — mass brute-force with wildcard-safe resolution
shuffledns -d target.com -w /path/to/subdomains.txt \
  -r resolvers.txt -o shuffle_results.txt
```

Recommended wordlists: `SecLists/Discovery/DNS/subdomains-top1million-110000.txt`, `jhaddix/all.txt`.

**2. Permutation expansion**

Generate new candidates from already-confirmed subdomains (`dev-api`, `api-staging`, `v2-app`, `app-prod`):

```bash
# altdns — generate permutation candidates from confirmed list (no dedicated skill — pip install altdns)
altdns -i confirmed_subdomains.txt -o permutation_candidates.txt -w /path/to/words.txt

# gotator — alternative permutation generator with depth control (no dedicated skill — go install)
gotator -sub confirmed_subdomains.txt -perm /path/to/words.txt -depth 1 -silent > gotator_candidates.txt

# Resolve permutation candidates with puredns
puredns resolve permutation_candidates.txt \
  --resolvers resolvers-trusted.txt -w resolved_permutations.txt
```

Permutation expansion finds dev, staging, internal, and regional subdomains that passive sources never index. Run it as a second pass after initial brute-force.

---

## Port sweep

### Strategy

Two-profile approach:

| Profile | Scope | Tool | Ports | Use case |
|---------|-------|------|-------|---------|
| Fast breadth | All confirmed IPs | masscan / rustscan | Top 1000 | Initial inventory |
| Thorough depth | High-value hosts only | nmap | All 65535 | Complete picture |

Never run full-port nmap across the entire IP range — too slow and too noisy.

### masscan fast sweep

```bash
# Top 1000 ports across IP range
masscan -p1-1000,8080,8443,8888,9090,9443 10.0.0.0/24 --rate 5000 -oJ masscan_out.json

# Common service ports (broader custom list)
masscan -p21,22,23,25,53,80,110,143,443,445,1433,1521,3306,3389,5432,6379,8080,8443,9200,27017 \
  -iL ips.txt --rate 10000 -oG masscan_grepable.txt
```

Rate guidance:
- Internal authorized scope: 10,000–50,000 pps (confirm with scope owner)
- External engagement: 1,000–5,000 pps typical — check for rate-limiting / IPS

### rustscan + nmap handoff

```bash
# Discover open ports fast, hand off to nmap for service detection
rustscan -a 10.0.0.0/24 --range 1-65535 --batch-size 5000 -- -sV -sC -oN nmap_services.txt

# Single host full port
rustscan -a target.com --ulimit 5000 -- -A -oN target_full.txt
```

### nmap targeted enumeration

Run nmap only on ports and hosts confirmed open by the sweep:

```bash
# Service + version + default scripts on open ports
nmap -sV -sC -p 22,80,443,8080 -iL live_hosts.txt -oA nmap_targeted

# Aggressive scan on single high-value host
nmap -A -p- target.com -oA target_aggressive

# UDP scan (top 100 — slow, worth it for DNS/SNMP/NTP)
nmap -sU --top-ports 100 -iL live_hosts.txt -oA nmap_udp

# NSE script categories
nmap --script=vuln target.com          # known vulnerability checks
nmap --script=auth target.com          # default credential checks
nmap --script=discovery target.com     # service discovery
```

#### High-value NSE scripts per service

| Service | NSE scripts |
|---------|------------|
| SMB | `smb-vuln-ms17-010`, `smb-enum-shares`, `smb-os-discovery` |
| HTTP | `http-title`, `http-headers`, `http-methods`, `http-auth-finder` |
| FTP | `ftp-anon`, `ftp-bounce` |
| SSH | `ssh-auth-methods`, `ssh-hostkey` |
| MSSQL | `ms-sql-info`, `ms-sql-empty-password` |
| MySQL | `mysql-empty-password`, `mysql-info` |
| SNMP | `snmp-info`, `snmp-sysdescr` |

---

## HTTP fingerprinting

After port sweep, probe every web-accessible host before investing time in content discovery.

### httpx at scale

```bash
# Probe all resolved hosts on common web ports
httpx -l resolved.txt -ports 80,443,8080,8443,8888,9090 \
  -title -tech-detect -status-code -follow-redirects \
  -o httpx_results.txt

# Output JSON for further processing
httpx -l resolved.txt -json -o httpx_results.json

# Filter for interesting status codes
httpx -l resolved.txt -mc 200,301,302,403 -o live_web.txt

# Extract specific tech (e.g. find all PHP hosts)
httpx -l resolved.txt -tech-detect -o all.json
cat all.json | jq '.tech[]?' | grep -i php
```

### Fingerprint priority targets

After httpx scan, rank by:
1. **Admin/management panels** — title contains "Admin", "Dashboard", "Management", "Control"
2. **Login pages** — title/path suggests auth (`/login`, `/signin`, `/auth`)
3. **API endpoints** — `/api/`, `/v1/`, `/graphql`, swagger docs
4. **Forgotten/legacy tech** — PHP on modern infrastructure, Apache 2.2, Tomcat 7
5. **403 responses** — resource exists but access denied (worth bypass attempts)

### EyeWitness visual triage

For large scope (50+ hosts), screenshot all web services for rapid visual ranking:

```bash
eyewitness --web -f live_web.txt --threads 10 -d eyewitness_output/
```

Open the HTML report — visually identify: login pages, admin panels, default pages (unfinished installs), error pages revealing tech.

### WAF and security control detection

Identify WAFs before content discovery or fuzzing — a blocked IP mid-scan wastes work and creates noise.

```bash
# wafw00f — targeted WAF fingerprinting per host
wafw00f https://target.com
wafw00f -l live_web.txt               # batch mode

# httpx tech-detect — WAF detected inline during fingerprinting
httpx -l resolved.txt -tech-detect -o tech_results.json
cat tech_results.json | jq '.technologies[]?' | grep -i "waf\|cloudflare\|akamai\|imperva\|f5"

# nuclei — WAF/CDN detection templates
nuclei -l live_web.txt -t technologies/waf-detect.yaml -o waf_results.txt
```

Once a WAF is identified:
- Reduce scan rate and add delays before probing that host.
- Check for WAF bypass: alternative IPs behind CDN (try direct IP, historical DNS, origin IP leaks).
- Use tamper scripts in fuzzing tools that support them (e.g., sqlmap `--tamper`, ffuf with custom headers).
- Document per-host WAF presence in the attack plan.

---

## Web content discovery

Target only fingerprinted high-value hosts. Full brute-force on every host wastes time.

### Wordlist selection

| Target type | Wordlist |
|-------------|---------|
| General content | `SecLists/Discovery/Web-Content/raft-medium-directories.txt` |
| API endpoints | `SecLists/Discovery/Web-Content/api/objects.txt` |
| Admin panels | `SecLists/Discovery/Web-Content/big.txt` + `admin` focused |
| PHP specific | `SecLists/Discovery/Web-Content/PHP.fuzz.txt` |
| Backup files | `SecLists/Discovery/Web-Content/Common-DB-Backups.txt` |

Use target-specific wordlists when available (from Wayback URL extraction or JS analysis).

### feroxbuster recursive discovery

```bash
# Basic recursive scan
feroxbuster -u https://target.com -w wordlist.txt -x php,html,js,json -o ferox_out.txt

# Status code filter (skip noise)
feroxbuster -u https://target.com -w wordlist.txt --filter-status 404,429 -o ferox_out.txt

# Scan multiple hosts
feroxbuster --stdin -w wordlist.txt --filter-status 404 < live_web.txt

# Slow/careful scan (rate-limited target)
feroxbuster -u https://target.com -w wordlist.txt --rate-limit 50 --threads 5
```

### gobuster for specific paths

```bash
# Directory brute-force
gobuster dir -u https://target.com -w wordlist.txt -x php,txt,bak -o gobuster_out.txt

# DNS subdomain brute-force (active)
gobuster dns -d target.com -w subdomains.txt -o dns_brute.txt

# VHOST enumeration (virtual host discovery)
gobuster vhost -u https://target.com -w subdomains.txt --append-domain -o vhost_out.txt
```

### Key paths to always check

```
/admin /administrator /manage /management /backend /staff
/api /api/v1 /api/v2 /graphql /swagger /swagger-ui /api-docs /openapi.json
/login /signin /auth /oauth /sso
/.env /.git /config.php /wp-config.php /web.config /app.config
/backup /db /database /dump /export
/phpinfo.php /info.php /test.php /debug
/actuator /actuator/env /actuator/heapdump (Spring Boot)
/metrics /health /status /version
```

---

## URL and parameter harvesting

Collect known URLs and parameters from historical sources and live JS analysis.

### gau — passive URL collection

```bash
# Fetch all known URLs for a domain from public archives
gau target.com | tee gau_urls.txt

# Multiple providers
gau --providers wayback,commoncrawl,otx,urlscan target.com

# Extract unique parameters
gau target.com | grep "?" | cut -d"?" -f2 | tr "&" "\n" | cut -d"=" -f1 | sort -u > params.txt
```

### hakrawler — live web crawl

```bash
# Crawl and extract links + JS endpoints
echo "https://target.com" | hakrawler -depth 3 -js -subs -o links.txt

# Crawl multiple hosts
cat live_web.txt | hakrawler -js -o all_links.txt
```

### JS endpoint extraction — katana

Katana is the standard tool for JS-aware crawling. It uses JSLuice and regex to extract endpoints from JavaScript files, including XHR/fetch calls and dynamic routes.

```bash
# JS crawl — extract endpoints from JS files
katana -u https://target.com -jc -o js_endpoints.txt

# Headless mode for SPA/React/Angular apps (renders JS before crawl)
katana -u https://target.com -headless -jc -o js_endpoints.txt

# XHR/fetch call tracing
katana -u https://target.com -jc -xhr -o xhr_endpoints.txt

# Filter results to API paths only
katana -u https://target.com -jc | grep -E "(/api/|/v[0-9]+/|/graphql|/rest/)"

# Pipeline: all live web hosts → crawl all JS endpoints
httpx -l live_hosts.txt -silent | katana -jc -o all_js_endpoints.txt
```

See `offensive-tools/recon/katana/` for full crawl configuration.

### Parameter discovery

```bash
# arjun — HTTP parameter discovery (offensive-tools/fuzzing/arjun/)
arjun -u https://target.com/endpoint -oJ arjun_out.json

# Extract parameters from gau URL output
gau target.com | grep "?" | cut -d"?" -f2 | tr "&" "\n" | cut -d"=" -f1 | sort -u > params.txt
```

---

## Active recon quality checklist

- [ ] DNS wildcard detection before bulk resolution
- [ ] All subdomains resolved — dead hosts removed
- [ ] CNAME records checked for subdomain takeover candidates
- [ ] Port sweep on all confirmed IPs complete
- [ ] Service + version enumeration on open ports
- [ ] HTTP fingerprinting on all web-accessible hosts
- [ ] Visual triage (EyeWitness) completed for large scope
- [ ] Content discovery on top-priority hosts
- [ ] Key paths checked (admin, api, actuator, .env, .git)
- [ ] URL and parameter harvest complete per priority host
- [ ] Attack plan produced: asset inventory + ranked entry points
- [ ] WAF/security controls identified per host
- [ ] Cloud storage assets checked (S3/Azure/GCS — see cloud-recon.md)
