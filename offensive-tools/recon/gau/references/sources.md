# gau — Sources, URL Parsing & Pipeline Patterns

## Provider Details

| Provider | Description | Coverage |
|----------|-------------|----------|
| `wayback` | Internet Archive Wayback Machine | Deep history, old snapshots |
| `commoncrawl` | CommonCrawl web index | Broad coverage, recent crawls |
| `urlscan` | URLScan.io submissions | Recent, includes status codes |
| `otx` | AlienVault OTX | Threat-intel sourced URLs |

```bash
# Compare provider coverage
gau --providers wayback target.com | wc -l
gau --providers commoncrawl target.com | wc -l
gau --providers urlscan target.com | wc -l

# URLScan has metadata (status codes, content types)
gau --providers urlscan --json target.com | \
  jq -r 'select(.statuscode==200) | .url'
```

## URL Parsing & Filtering

### Extract Parameters

```bash
# All URLs with query params
gau target.com | grep "?"

# Unique parameter names (Python)
gau target.com | grep "?" | \
  sed 's/#.*//' | \
  python3 -c "
import sys, urllib.parse
params = set()
for url in sys.stdin:
    qs = urllib.parse.urlparse(url.strip()).query
    params.update(urllib.parse.parse_qs(qs).keys())
print('\n'.join(sorted(params)))
"

# Unique parameter names (bash/awk)
gau target.com | grep "?" | \
  grep -oP '\?[^#]*' | tr '&' '\n' | \
  sed 's/=.*//' | sed 's/^\?//' | sort -u
```

### Filter by Extension

```bash
# Only dynamic pages (PHP, ASP, etc.)
gau target.com | grep -E "\.(php|asp|aspx|jsp|cgi)(\?|$)"

# Backup/sensitive files
gau target.com | grep -E "\.(bak|backup|old|orig|log|sql|env|config|conf|cfg|ini|tar|zip|gz|7z)(\?|$)"

# JavaScript files
gau target.com | grep "\.js" | sort -u

# JSON endpoints
gau target.com | grep "\.json" | sort -u
```

### De-duplicate Parameter Patterns

```bash
# Remove param values (keep structure)
gau target.com | grep "?" | \
  sed 's/=[^&]*/=FUZZ/g' | \
  sort -u > fuzz_urls.txt
```

## Integration Patterns

### gau + httpx (live check historical URLs)

```bash
# Find still-alive old endpoints
gau target.com | \
  httpx -silent -status-code -title -mc 200,201,301,302,403 | \
  grep -v "cloudflare\|akamai"
```

### gau + ffuf (parameter fuzzing)

```bash
# Mine params, then fuzz for IDOR/injection
gau target.com | grep "?" | \
  sed 's/=[^&]*/=FUZZ/g' | sort -u | \
  ffuf -w -:URL -u URL -ac -mc 200 -v
```

### gau + nuclei (historical endpoint scan)

```bash
gau --subs target.com | \
  sort -u | \
  httpx -silent | \
  nuclei -tags exposure,misconfig,xss,sqli -severity medium,high,critical
```

### gau + hakrawler (passive + active URL combo)

```bash
# Passive: gau
gau --subs target.com | sort -u > passive_urls.txt

# Active: hakrawler
cat live_hosts.txt | hakrawler -d 3 -u | sort -u > active_urls.txt

# Merge + deduplicate
cat passive_urls.txt active_urls.txt | sort -u > all_urls.txt
echo "Total unique: $(wc -l < all_urls.txt)"
```

## Advanced URL Analysis

### Find Potential IDOR Patterns

```bash
gau target.com | grep -E "(/[0-9]+|[?&](id|user|account|order|invoice)=[0-9]+)"
```

### Find Potential LFI/Path Traversal Parameters

```bash
gau target.com | grep -E "[?&](file|path|page|include|load|view|doc|template)="
```

### Find API Versioning

```bash
gau target.com | grep -oE "(https?://[^/]+/)(api/v[0-9]+|v[0-9]+/api)" | sort -u
```

### Detect Subdomains from URLs

```bash
gau --subs target.com | \
  grep -oP "https?://\K[^/]+" | \
  sort -u > discovered_subdomains.txt
```

## Comparison: gau vs hakrawler vs katana

| Feature | gau | hakrawler | katana |
|---------|-----|-----------|--------|
| Passive (no target requests) | Yes | No | No |
| JS rendering | No | No | Yes |
| Active crawling | No | Yes | Yes |
| Historical URLs | Yes | No | No |
| Parameter metadata | URLScan only | No | Yes |
| Speed | Fastest | Fast | Slowest |
| Best for | Historical mining | Active crawl | SPA/JS-heavy |

**Use gau first** (passive, safe) → then hakrawler for active crawl → katana for JS-heavy targets.
