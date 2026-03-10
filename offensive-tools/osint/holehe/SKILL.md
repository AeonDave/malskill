---
name: holehe
description: "Check if an email address is registered on 120+ websites (Google, Twitter, GitHub, etc.). Use during OSINT to enumerate target digital presence and identify accounts across platforms."
license: MIT
compatibility: "Python 3; pip install holehe; Linux/macOS/Windows; github.com/megadose/holehe"
metadata:
  author: AeonDave
  version: "1.0"
---

# Holehe

Email-to-account mapper — check if an email is registered across 120+ services.

## Quick Start

```bash
pip install holehe

# Check a single email
holehe target@gmail.com

# Output only registered sites
holehe target@gmail.com --only-used

# JSON output
holehe target@gmail.com --only-used --json > results.json
```

## Core Flags

| Flag | Purpose |
|------|---------|
| `--only-used` | Show only sites where email is registered |
| `--no-color` | Disable color output |
| `--json` | JSON output |
| `-T N` | Timeout per request |

## Sites Checked (examples)

`Google` · `Twitter/X` · `GitHub` · `Instagram` · `LinkedIn` · `Reddit` · `Snapchat` · `Spotify` · `Adobe` · `Airbnb` · `Amazon` · `Dropbox` · `Flickr` · `Pinterest` · `Tumblr` + 100 more

## Common Workflows

**OSINT on target email:**
```bash
holehe ceo@targetcompany.com --only-used --json | tee email_presence.json
```

**Batch check from file:**
```bash
cat emails.txt | xargs -I {} holehe {} --only-used
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Interpreting results and account takeover paths |
