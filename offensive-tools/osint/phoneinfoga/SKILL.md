---
name: phoneinfoga
description: "Phone number OSINT tool — gather carrier, location, and online presence data for phone numbers. Use when pivoting on phone numbers during target profiling or social engineering preparation."
license: MIT
compatibility: "Go binary; Linux/macOS/Windows; github.com/sundowndev/phoneinfoga"
metadata:
  author: AeonDave
  version: "1.1"
---

# PhoneInfoga

Phone number reconnaissance — carrier, country, online presence, breach data.

## Quick Start

```bash
# Download from GitHub releases
# Or Docker
docker run --rm sundowndev/phoneinfoga scan -n +1234567890

# Scan a number (international format)
phoneinfoga scan -n +14151234567

# Start web UI
phoneinfoga serve
# → http://localhost:5000
```

## Core Commands

| Command | Purpose |
|---------|---------|
| `scan -n NUMBER` | Full scan on number |
| `serve` | Launch web dashboard |
| `--output json` | JSON output |

## Information Retrieved

- Country, carrier, line type (mobile/landline/VoIP)
- Possible owner via reverse lookup
- Google dork results (social media, directories)
- NumVerify / Numinfo API data (if configured)
- Breach lookups (HaveIBeenPwned linked accounts)

## Common Workflows

**Quick scan:**
```bash
phoneinfoga scan -n +14151234567
```

**Web dashboard for manual investigation:**
```bash
phoneinfoga serve &
open http://localhost:5000
```

**JSON output for automation:**
```bash
phoneinfoga scan -n +14151234567 --output json > phone.json
```

**Multiple numbers from file:**
```bash
while read num; do
  phoneinfoga scan -n "$num" --output json >> all_results.json
done < numbers.txt
```

## API Keys (Optional, Extend Results)

Configured in `~/.phoneinfoga/config.yaml`:

```yaml
numverify_api_key: "YOUR_KEY"    # numverify.com — validation + carrier
googlecse_api_key: "YOUR_KEY"    # Google Custom Search Engine
googlecse_cx: "YOUR_CX_ID"
```

Without keys: basic OSINT via Google dorks only.
With NumVerify: carrier, line type, country validation.

## Google Dork Expansion

PhoneInfoga auto-generates dorks. Run manually for deeper coverage:

```
"+14151234567" site:linkedin.com
"+14151234567" site:facebook.com
"+14151234567" -site:yellowpages.com -site:whitepages.com
"+14151234567" "resume" OR "contact" OR "WhatsApp"
```

## Resources

| File | When to load |
|------|--------------|
| `references/api-setup.md` | NumVerify setup, Google CSE config, alternative phone lookup sources |
