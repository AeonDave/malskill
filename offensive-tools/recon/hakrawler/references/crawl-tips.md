# Hakrawler — Scope Filtering, JS Analysis & Pipeline Patterns

## Scope Control

### URL Pattern Scoping

```bash
# Only crawl target.com and subdomains
echo https://target.com | hakrawler -scope ".*\.?target\.com.*"

# Limit to specific path prefix
echo https://target.com | hakrawler -scope ".*target\.com/app/.*"

# Exclude common noise paths
echo https://target.com | hakrawler -d 3 | \
  grep -vE "(logout|signout|\.png|\.jpg|\.gif|\.css|\.woff|\.svg)"
```

### Output Type Filtering

```bash
# JSON output — select by type
echo https://target.com | hakrawler -json | jq -r '.source'

# Types: link, script, form, href
echo https://target.com | hakrawler -json | jq -r 'select(.type=="script") | .source'
echo https://target.com | hakrawler -json | jq -r 'select(.type=="form") | .source'
```

## JavaScript Analysis

### Extract JS Files

```bash
# All JS files from crawl
echo https://target.com | hakrawler -d 3 -u | \
  grep -E "\.js(\?|$)" | sort -u > js_files.txt

# Fetch and search for secrets
cat js_files.txt | while read url; do
  curl -sk "$url" | grep -oE "(api[_-]?key|secret|token|password|bearer)[[:space:]]*[:=][[:space:]]*['\"][^'\"]{8,}['\"]" && echo "  # $url"
done
```

### JS Secret Scanning with trufflehog/gf

```bash
# Download all JS files
cat js_files.txt | xargs -P10 -I{} sh -c 'curl -sk "{}" > "js/$(echo {} | md5sum | cut -d" " -f1).js"'

# Scan with gf (grep patterns)
cat js/ | gf aws-keys
cat js/ | gf firebase
cat js/ | gf generic-api-key

# Scan with trufflehog
trufflehog filesystem js/
```

### Find Hardcoded Endpoints in JS

```bash
cat js_files.txt | while read url; do
  curl -sk "$url" | grep -oE '(https?://[a-zA-Z0-9./_-]+(/api/|/v[0-9]/)[a-zA-Z0-9./_?=-]*)' | sort -u
done
```

## Pipeline Patterns

### Full Recon → Crawl Pipeline

```bash
#!/bin/bash
TARGET=$1

# Step 1: live hosts
subfinder -d "$TARGET" -silent | httpx -silent > live.txt

# Step 2: crawl all live hosts
cat live.txt | hakrawler -d 3 -u -subs -scope ".*${TARGET}.*" > all_urls.txt

# Step 3: extract interesting categories
grep -E "\.js$" all_urls.txt | sort -u > js_files.txt
grep -E "(/api/|/v[0-9]+/)" all_urls.txt | sort -u > api_endpoints.txt
grep -E "\.(php|asp|aspx|jsp)" all_urls.txt | sort -u > server_pages.txt

echo "JS: $(wc -l < js_files.txt)"
echo "API: $(wc -l < api_endpoints.txt)"
echo "Server pages: $(wc -l < server_pages.txt)"
```

### Feed to Fuzzer

```bash
# Crawl → extract param URLs → fuzz
echo https://target.com | hakrawler -d 2 -u | \
  grep "?" | \
  while read url; do
    # Replace param values with FUZZ
    param_url=$(echo "$url" | sed 's/=[^&]*/=FUZZ/g')
    echo "$param_url"
  done | sort -u > fuzz_targets.txt

# Feed to ffuf
ffuf -w fuzz_targets.txt:URL -u URL -ac -mc 200
```

### Find Admin / Sensitive Paths

```bash
echo https://target.com | hakrawler -d 4 -u | \
  grep -iE "(admin|login|dashboard|panel|config|backup|secret|token|api-key|password)"
```

## Authenticated Crawling

```bash
# With session cookie
echo https://target.com | hakrawler -d 3 \
  -cookie "session=abc123; auth=token" \
  -H "Authorization: Bearer TOKEN"

# Custom User-Agent (avoid bot detection)
echo https://target.com | hakrawler -d 2 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
```

## Comparison with Other Crawlers

| Feature | hakrawler | gau | gospider | katana |
|---------|-----------|-----|----------|--------|
| Active crawl | Yes | No (passive) | Yes | Yes |
| JS rendering | No | No | No | Yes |
| Depth control | Yes | No | Yes | Yes |
| Passive sources | No | Yes | No | No |
| Speed | Fast | Fastest | Fast | Medium |

**Use hakrawler** for: fast active crawl, JS file discovery, form discovery
**Use gau** for: passive URL mining from archives (no requests to target)
**Use katana** for: JS-heavy SPAs needing headless browser rendering
