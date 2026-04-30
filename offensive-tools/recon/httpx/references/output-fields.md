# httpx — Output Fields, Filters & Pipeline Patterns

## All Output Field Flags

```bash
httpx -l hosts.txt \
  -status-code \        # HTTP status code
  -title \              # Page title
  -tech-detect \        # Wappalyzer tech stack
  -web-server \         # Server header
  -content-type \       # Content-Type header
  -ip \                 # Resolved IP
  -cname \              # CNAME record
  -location \           # Redirect location
  -content-length \     # Response body size
  -response-time \      # Time to first byte
  -hash sha256 \        # Body hash (md5/sha1/sha256)
  -favicon \            # Favicon mmh3 hash
  -tls-probe \          # TLS certificate data
  -cdn \                # CDN detection
  -asn \                # ASN info
  -o full.json -json
```

## JSON Output Schema

```json
{
  "url": "https://sub.target.com",
  "status-code": 200,
  "title": "Login — Target Portal",
  "webserver": "nginx/1.18.0",
  "tech": ["WordPress", "PHP", "MySQL"],
  "ip": "1.2.3.4",
  "cname": ["target.cdn.example.com"],
  "content-length": 8291,
  "response-time": "312ms",
  "hash": {"body-sha256": "abc123..."},
  "favicon-mmh3": -247388890,
  "tls": {
    "subject_cn": "*.target.com",
    "issuer_cn": "Let's Encrypt",
    "not_after": "2025-12-31T00:00:00Z"
  },
  "cdn": true,
  "asn": {"as_number": "AS12345", "as_org": "Target Corp"}
}
```

## Match / Filter Options

```bash
# Match by status codes
-mc 200,201,204         # include
-fc 301,302,404,403     # exclude

# Match by response size
-ms 1024               # exact size
-mls 100               # min size (lines)
-mws 10                # min words

# Match by body content
-match-string "admin"
-match-regex "version [0-9]+\.[0-9]+"

# Filter by body
-filter-string "cloudflare"
-filter-regex "error|forbidden"

# Match by content type
-match-cdn              # only CDN hosts
-filter-cdn             # exclude CDN hosts
```

## Pipeline Patterns

### Subdomain → Live Hosts → Tech Stack

```bash
subfinder -d target.com -silent -all | \
  dnsx -silent | \
  httpx -silent -status-code -title -tech-detect -web-server -ip -o recon.json -json
```

### Find Interesting Panels (Pipeline)

```bash
cat recon.json | jq -r 'select(.status_code==200) | select(.title | test("admin|login|dashboard|portal|jenkins|grafana|kibana";"i")) | .url'
```

### Group by Technology

```bash
cat recon.json | jq -r '.tech[]?' | sort | uniq -c | sort -rn | head -20
```

### Favicon Hash → Shodan Pivot

```bash
httpx -l live_hosts.txt -favicon -silent -json | \
  jq -r 'select(.favicon_mmh3 != null) | "\(.url) \(.favicon_mmh3)"' | \
  while read url hash; do
    echo "shodan search http.favicon.hash:$hash  # $url"
  done
```

### Screenshot All Live Hosts

```bash
# httpx built-in (requires chromium)
httpx -l hosts.txt -screenshot -o screenshots/

# or pipe to eyewitness
cat live_hosts.txt | httpx -silent | xargs -I{} echo {} > urls.txt
eyewitness -f urls.txt --web -d eyewitness_out/ --no-prompt
```

### Detect Default/Interesting Services

```bash
# Jenkins, Grafana, GitLab, etc.
httpx -l hosts.txt -title -mc 200 -silent | \
  grep -iE "jenkins|grafana|gitlab|kibana|elasticsearch|sonarqube|jira|confluence|adminer|phpmyadmin"
```
