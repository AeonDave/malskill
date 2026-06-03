---
name: maigret
description: "Auth/lab ref: Build a dossier on a person from a single username: searches 2800+ sites, extracts profile data (name, bio, location, linked accounts), and generates HTML/PDF/CSV reports."
license: MIT
compatibility: "Python 3.8+; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Maigret

Username dossier builder — 2800+ sites, profile data extraction, identity correlation.

## Quick Start

```bash
pip install maigret

# Basic search
maigret username

# Search with HTML report
maigret username --html

# Limit to top N sites (faster)
maigret username --top-sites 500

# Search multiple usernames
maigret username1 username2
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--top-sites <n>` | Search only top N sites by Alexa rank |
| `--html` | Generate HTML report |
| `--pdf` | Generate PDF report |
| `--csv` | CSV output |
| `--json` | JSON output |
| `--timeout <n>` | Per-site timeout (default: 30s) |
| `--retries <n>` | Retries per site |
| `--proxy <url>` | Use proxy |
| `--tor` | Route via Tor |
| `-a` | All sites (no limit) |
| `--parse-url <url>` | Extract username from profile URL |
| `--self-check` | Test site database integrity |
| `--tags <tags>` | Filter by site tags (e.g. `social`, `dating`, `gaming`) |

## Common Workflows

**Deep profile investigation:**
```bash
maigret johndoe --html --pdf --top-sites 1000
# Opens report in browser; PDF for reporting
```

**Fast sweep (quick wins):**
```bash
maigret johndoe --top-sites 200 --timeout 10
```

**Tagged category search:**
```bash
# Social media only
maigret johndoe --tags social

# Dating sites (for social engineering intel)
maigret johndoe --tags dating

# Gaming platforms
maigret johndoe --tags gaming
```

**Extract username from a known profile URL:**
```bash
maigret --parse-url https://twitter.com/johndoe
# Auto-extracts "johndoe", runs full search
```

**Via Tor (opsec):**
```bash
# Start tor first
sudo service tor start
maigret johndoe --tor --top-sites 500
```

**Multiple username variants (pipeline):**
```bash
for user in johndoe john.doe john_doe jdoe83; do
  maigret "$user" --csv --top-sites 300 2>/dev/null
done
```

## vs Sherlock

| | maigret | sherlock |
|--|---------|---------|
| Sites | 2800+ | 400 |
| Profile data | Extracts name/bio/location | URL only |
| Linked accounts | Detects aliases | No |
| Reports | HTML/PDF/CSV | TXT/JSON/CSV |
| Speed | Slower | Fast |
| Best for | Deep investigation | Fast initial sweep |

**Recommended workflow:** sherlock for fast sweep → maigret on confirmed usernames.

## Parse JSON Output

```bash
# Accounts found (from JSON report)
cat maigret_johndoe.json | jq '.sites | to_entries[] | select(.value.status == "Claimed") | {site: .key, url: .value.url}'

# Extracted personal data
cat maigret_johndoe.json | jq '.sites | to_entries[] | select(.value.extracted_data != null) | {site: .key, data: .value.extracted_data}'
```

## Resources

| File | When to load |
|------|--------------|
| `references/dossier.md` | Report interpretation, linked account correlation, data extraction patterns |
