---
name: arjun
description: "Arjun: HTTP parameter discovery fuzzer with a large curated parameter dictionary. Use when hunting hidden GET/POST/JSON/XML parameters on web apps and APIs before SQLi/XSS/IDOR testing. Designed for fast attack-surface expansion and easy handoff into ffuf, dalfox, sqlmap, and custom replay pipelines."
license: GNU GPL v3
compatibility: "Linux / macOS / Windows. Python 3. pip3 install arjun or git clone https://github.com/s0md3v/Arjun"
metadata:
  author: AeonDave
    version: "1.2"
---

# Arjun

HTTP parameter discovery for hidden GET/POST/JSON/XML attack surface expansion.

## Pre-Flight (real usage)

```bash
# Confirm installed version and available options
arjun --help

# Start with one endpoint and explicit auth context before batch mode.
# Hidden params are often role-dependent (guest vs user vs admin).
```

## Quick Start

```bash
pip3 install arjun

# GET parameters
arjun -u "https://target.com/search"

# POST parameters
arjun -u "https://target.com/search" -m POST

# JSON API
arjun -u "https://api.target.com/user" -m JSON

# Batch scan from file
arjun -i urls.txt -oJ params.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `-u <url>` | Target URL |
| `-i <file>` | URL list for batch scanning |
| `-m <method>` | Method: `GET` / `POST` / `JSON` / `XML` (default: GET) |
| `-w <wordlist>` | Wordlist: path or `small` / `medium` / `large` (default: large) |
| `-oJ <file>` | JSON output (for tool integration) |
| `-oT <file>` | Text output |
| `-oB [proxy]` | Output to Burp proxy (default: 127.0.0.1:8080) |
| `--headers <h>` | Custom headers (newline-separated) |
| `--include <data>` | Include data in every request (cookies, tokens) |
| `-t <N>` | Threads (default: 5) |
| `-d <s>` | Delay between requests (seconds) |
| `-T <s>` | Request timeout (default: 15s) |
| `--rate-limit <N>` | Max requests/second |
| `--passive [domain]` | Collect params from Wayback/CommonCrawl/OTX (no active requests) |
| `--stable` | Prefer stability over speed (unreliable servers) |
| `--disable-redirects` | Don't follow HTTP redirects |
| `--casing <style>` | Parameter casing: `like_this` / `likeThis` / `likethis` |
| `-c <N>` | Chunk size (params sent per request) |
| `-q` | Quiet mode |

## Common Workflows

```bash
# Authenticated GET scan
arjun -u "https://target.com/profile" \
    --headers "Cookie: session=abc123" \
    --include "csrf_token=XYZ"

# POST + save results
arjun -u "https://target.com/api/update" -m POST \
    --headers "Authorization: Bearer TOKEN" \
    -oJ post_params.json

# JSON API discovery
arjun -u "https://api.target.com/v2/user" -m JSON \
    --headers "Authorization: Bearer TOKEN\nX-API-Version: 2"

# Batch scan with rate limit (bug bounty / not-your-server)
arjun -i targets.txt -d 1 --rate-limit 3 -oJ all_params.json

# Passive discovery (stealthy, no active requests)
arjun --passive target.com

# Feed to ffuf for fuzzing
arjun -u "https://target.com/page" -oT params.txt
cat params.txt | while read p; do
    ffuf -u "https://target.com/page?$p=FUZZ" -w payloads.txt -fc 404
done
```

## Real-Tool Workflow (recommended)

1. Run Arjun on a single endpoint in the correct auth state.
2. Save JSON output (`-oJ`) as source of truth.
3. Replay discovered params with benign values and compare baseline response.
4. Only then escalate to SQLi/XSS/IDOR fuzz payloads.
5. Repeat after privilege/context changes (user role, tenant, feature flag).

## Reconnaissance Pipeline

```bash
# Full recon → parameter discovery → injection testing
subfinder -d target.com | httpx -silent > live_hosts.txt
cat live_hosts.txt | while read url; do
    arjun -u "$url" -oJ /tmp/params_$(echo $url | md5sum | cut -c1-8).json
done

# Discovered params → sqlmap
arjun -u "https://target.com/search" -oJ params.json
# Use params as --data to sqlmap

# Discovered params → dalfox XSS scan
arjun -u "https://target.com/search" -oT params.txt
cat params.txt | xargs -I{} dalfox url "https://target.com/search?{}=FUZZ"

# Discovered params → ffuf value fuzzing
arjun -u "https://target.com/search" -oT params.txt
cat params.txt | while read p; do
    ffuf -u "https://target.com/search?$p=FUZZ" -w values.txt -mc all -fc 404
done
```

## Passive Mode

```bash
# Collect historical params without touching target
arjun --passive target.com

# Good for: stealth recon, bug bounty programs with strict scope
# Sources: Wayback Machine, CommonCrawl, OTX
```

## Arjun vs Param Miner

| | Arjun | Param Miner (Burp) |
|-|-------|--------------------|
| Type | CLI / automation | Burp extension |
| Wordlist | 25,890 params | 50,000+ |
| Batch | Yes (`-i`) | Per-endpoint |
| Output | JSON/text/Burp | Burp only |
| **Use** | Automation, pipelines | Manual testing in Burp |

## Practical Triage Tips

- Confirm discovered parameters with at least two payload classes (benign + malicious) before escalation.
- Prioritize parameters that alter response size/status/body structure.
- Re-run Arjun after authentication-state changes (guest vs user vs admin) to detect role-dependent parameters.
- Keep batch scans rate-limited on production targets to avoid noisy false negatives from temporary blocking.
- Treat every discovered parameter as candidate input sink, not immediate vulnerability.

## Resources

| File | When to load |
|------|--------------|
| `references/param-discovery.md` | Passive discovery, custom wordlists, full recon pipelines, integration patterns |
