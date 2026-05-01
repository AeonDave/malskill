# ffuf — Filters, Matchers & Advanced Patterns

## Filter / Matcher Reference

### Match (include only matching responses)

| Flag | Description | Example |
|------|-------------|---------|
| `-mc <codes>` | Match status codes | `-mc 200,201,204` |
| `-ml <n>` | Match line count | `-ml 50` |
| `-mw <n>` | Match word count | `-mw 100` |
| `-ms <n>` | Match response size (bytes) | `-ms 4096` |
| `-mr <regex>` | Match body regex | `-mr "Welcome"` |
| `-mtime <n>` | Match response time (ms) | `-mtime 500` |

### Filter (exclude matching responses)

| Flag | Description | Example |
|------|-------------|---------|
| `-fc <codes>` | Filter status codes | `-fc 404,302` |
| `-fl <n>` | Filter line count | `-fl 10` |
| `-fw <n>` | Filter word count | `-fw 42` |
| `-fs <n>` | Filter response size (bytes) | `-fs 1234` |
| `-fr <regex>` | Filter body regex | `-fr "Not Found"` |
| `-ftime <n>` | Filter response time (ms) | `-ftime 5000` |

### Auto-Calibration (best practice)

```bash
# -ac: sends fake probes, auto-detects "default" response, filters it
ffuf -u https://target.com/FUZZ -w wordlist.txt -ac

# -ach: auto-calibrate per-host (multi-FUZZ scenarios)
ffuf -u https://FUZZ.target.com -w vhosts.txt -H "Host: FUZZ.target.com" -ach
```

## Noise Reduction Strategy

### 1. Start with -ac (auto-calibrate)
Most reliable, handles dynamic pages.

### 2. Identify false positive pattern
```bash
# Run small wordlist, observe false positive structure
ffuf -u https://target.com/FUZZ -w small.txt -v 2>&1 | head -50
# Note: response size/words/lines of 404 equivalents
```

### 3. Apply targeted filter
```bash
# All "404" pages are 1234 bytes → filter
ffuf -u https://target.com/FUZZ -w wordlist.txt -fs 1234

# "Not found" error varies in size but has 42 words → filter words
ffuf -u https://target.com/FUZZ -w wordlist.txt -fw 42

# Page says "Resource not found" → filter regex
ffuf -u https://target.com/FUZZ -w wordlist.txt -fr "Resource not found"
```

## Multiple FUZZ Patterns

### Two wordlists (default = clusterbomb)

```bash
# All combinations of W1 and W2
ffuf -u https://target.com/W1/W2 \
  -w dirs.txt:W1 \
  -w files.txt:W2 \
  -ac
```

### Pitchfork (pairs — same index)

```bash
# user1:pass1, user2:pass2, ...
ffuf -u https://target.com/login \
  -X POST -d "user=U&pass=P" \
  -w users.txt:U -w passes.txt:P \
  -mode pitchfork -fc 401
```

### Clusterbomb (full cartesian product)

```bash
ffuf -u https://target.com/W1?W2=W3 \
  -w paths.txt:W1 \
  -w params.txt:W2 \
  -w values.txt:W3 \
  -mode clusterbomb -ac
```

## Common Attack Patterns

### Directory + Extension Combo

```bash
ffuf -u https://target.com/FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
  -e .php,.bak,.conf,.txt,.html,.xml \
  -ac -t 50 -o dirs.json -of json
```

### Parameter Discovery

```bash
# GET parameter fuzzing
ffuf -u "https://target.com/page?FUZZ=testvalue" \
  -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
  -ac -mc 200

# POST parameter fuzzing
ffuf -u https://target.com/api/endpoint \
  -X POST -d "FUZZ=testvalue" \
  -w params.txt -ac

# Value fuzzing (known param, unknown value)
ffuf -u "https://target.com/page?id=FUZZ" \
  -w /usr/share/seclists/Fuzzing/Integers/Integers.txt \
  -ac -mc 200
```

### Vhost / Subdomain Discovery

```bash
# Filter noise by word count (default response word count)
# 1. Get default response
curl -s https://target.com -o /dev/null -w "%{size_download} bytes\n"

# 2. Run with filter
ffuf -u https://target.com \
  -H "Host: FUZZ.target.com" \
  -w subdomains.txt \
  -fs <DEFAULT_SIZE>
# or use -ac for auto-calibration
```

### Auth Bypass Fuzzing

```bash
# Header injection
ffuf -u https://target.com/admin \
  -w /usr/share/seclists/Fuzzing/Headers/x-forwarded-for.txt \
  -H "X-Forwarded-For: FUZZ" \
  -mc 200

# HTTP method fuzzing
ffuf -u https://target.com/api/resource \
  -w /usr/share/seclists/Fuzzing/http-request-methods.txt \
  -X FUZZ -mc 200,201,204,405
```

### Recursive Fuzzing

```bash
ffuf -u https://target.com/FUZZ \
  -w common.txt \
  -recursion \
  -recursion-depth 2 \
  -recursion-strategy greedy \
  -ac -t 40
# greedy = recurse into everything found (even 403s)
# default = recurse only into redirects
```

## Output Processing

```bash
# JSON output → extract found URLs
ffuf -u https://target.com/FUZZ -w wordlist.txt -ac -of json -o out.json
cat out.json | jq -r '.results[] | "\(.status) \(.length)b \(.url)"'

# Filter only 200s from JSON
cat out.json | jq -r '.results[] | select(.status==200) | .url'

# All formats at once
ffuf -u https://target.com/FUZZ -w wordlist.txt -ac -of all -o results
# Creates results.json, results.html, results.csv, results.md
```

## Rate Limiting & Evasion

```bash
# Slow down (avoid WAF/rate limit)
ffuf -u https://target.com/FUZZ -w wordlist.txt -p 0.1-0.5 -t 10

# Randomized delay
ffuf -u https://target.com/FUZZ -w wordlist.txt -p 0.05-2.0 -t 5

# Through Burp proxy (for manual review)
ffuf -u https://target.com/FUZZ -w wordlist.txt -x http://127.0.0.1:8080 -k

# Custom User-Agent
ffuf -u https://target.com/FUZZ -w wordlist.txt \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
```
