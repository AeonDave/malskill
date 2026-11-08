---
name: maigret
description: "Auth/lab ref: Build a dossier on a person from a single username: searches 5,900 sites (default run: top-500 by traffic), extracts profile data (name, bio, location, linked accounts), and generates HTML/PDF/CSV reports."
license: MIT
compatibility: "Python 3.8+; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.0"
---

# Maigret

Username dossier builder — 5,900 sites (default run: top-500 by traffic), profile data extraction, identity correlation.

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
| `--top-sites <n>` | Search only top N sites by traffic rank |
| `--html` | Generate HTML report |
| `--pdf` | Generate PDF report |
| `--csv` | CSV output |
| `--json <type>` | Generate a JSON report in the selected format |
| `--timeout <n>` | Per-site timeout (default: 30s) |
| `--retries <n>` | Retries per site |
| `--proxy <url>` | Use proxy |
| `--tor` | Route via Tor |
| `-a` | All sites (no limit) |
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
| Sites | 5,900 (default top 500) | 400+ |
| Profile data | Extracts name/bio/location | URL only |
| Linked accounts | Detects aliases | No |
| Reports | HTML/PDF/CSV | TXT/CSV/XLSX |
| Speed | Slower | Fast |
| Best for | Deep investigation | Fast initial sweep |

**Recommended workflow:** sherlock for fast sweep → maigret on confirmed usernames.

Treat matches as candidates; independently corroborate account ownership before linking profiles to a person.

See [upstream](https://github.com/soxoj/maigret) for report formats and current options.
