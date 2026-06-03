---
name: holehe
description: "Auth/lab ref: Check if an email address is registered on 120+ websites using account-recovery probes (not login attempts)."
license: MIT
compatibility: "Python 3; Linux/macOS/Windows."
metadata:
  author: AeonDave
  version: "1.1"
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

**Combine with username pivot:**
```bash
# If target email is johndoe@gmail.com, extract username
holehe johndoe@gmail.com --only-used --json | jq '.[] | .name' | \
  xargs -I {} echo "sherlock johndoe --site {}"
```

## How It Works

Holehe uses account-recovery flows (password reset) — not login attempts. Most sites respond differently to "email not found" vs "reset link sent", so holehe detects registration without credentials. Low noise, does not lock accounts.

## Email Sources for OSINT

```bash
# From company domain — harvest emails with theHarvester first
theHarvester -d target.com -b google,bing,linkedin -l 200

# From breach databases
# dehashed.com, haveibeenpwned.com, intelx.io

# From GitHub commits
curl "https://api.github.com/repos/<owner>/<repo>/commits" | \
  jq '.[].commit.author.email' | sort -u
```

## Resources

| File | When to load |
|------|--------------|
| `references/email-osint.md` | Email harvesting sources, breach lookup APIs, pivot from email to full profile |
