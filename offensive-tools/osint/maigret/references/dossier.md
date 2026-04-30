# Maigret — Dossier Building & Identity Correlation

## What Maigret Extracts

From profile pages (when publicly available):

| Data Point | Source Examples |
|-----------|-----------------|
| Real name | LinkedIn, Facebook, Reddit |
| Profile photo | All social platforms |
| Bio / description | Twitter, Instagram, GitHub |
| Location | Twitter, LinkedIn, Foursquare |
| Website / links | GitHub, Twitter bio |
| Joined date | Reddit, GitHub, Twitter |
| Post count / activity | Reddit, forums |
| Linked accounts | Keybase, About.me, Linktree |

## Linked Account Detection

Maigret auto-detects when profiles link to other usernames:

```json
{
  "github.com/johndoe": {
    "status": "Claimed",
    "extracted_data": {
      "name": "John Doe",
      "blog": "https://johndoe.io",
      "twitter": "jdoe83"    ← different username detected
    }
  }
}
```

When a new username is found → re-run maigret on it:

```bash
maigret jdoe83 --html --top-sites 500
```

## Building Full Dossier (Manual Steps)

1. Start: email from breach/LinkedIn/theHarvester
2. → `holehe email` → active platforms
3. → derive username from email prefix
4. → `sherlock username` → quick platform sweep
5. → `maigret username --html` → extract profile data
6. → new username discovered in profile
7. → `maigret new_username --html` → repeat
8. → phone number found in profile
9. → `phoneinfoga scan -n +<number>` → carrier/location

## Parse Dossier JSON

```python
import json

with open("maigret_johndoe.json") as f:
    data = json.load(f)

# All claimed sites
claimed = {k: v for k, v in data["sites"].items()
           if v.get("status") == "Claimed"}

# Extract personal data from all sites
for site, info in claimed.items():
    if info.get("extracted_data"):
        print(f"\n=== {site} ===")
        for k, v in info["extracted_data"].items():
            print(f"  {k}: {v}")
```

## Report Structure (HTML)

The HTML report contains:
- **Summary card**: detected real name, most common location, aggregated data
- **Platform grid**: all found accounts with preview data
- **Timeline**: account creation dates across platforms
- **Graph**: username / alias relationships

## Linked Sites Pattern

```bash
# Linktree aggregator pages reveal all linked accounts
# Look for: linktr.ee/username, beacons.ai/username, bio.link/username

# If found, manually scrape links
curl -s "https://linktr.ee/johndoe" | grep -oE 'https?://[a-zA-Z0-9./%-]+'
```

## Keybase Verification

Keybase links verified identities across platforms (GitHub, Twitter, Reddit, etc.):

```bash
curl -s "https://keybase.io/_/api/1.0/user/lookup.json?username=johndoe" \
  | jq '.them[0].proofs_summary.all[] | {service:.proof_type, username:.nametag, url:.human_url}'
```

## About.me / Gravatar

```bash
# About.me profile
curl -s "https://about.me/johndoe" | grep -oE '"[a-z_]+":"[^"]{3,}"'

# Gravatar (from email hash)
python3 -c "
import hashlib
email = 'johndoe@example.com'
h = hashlib.md5(email.strip().lower().encode()).hexdigest()
import urllib.request
data = urllib.request.urlopen(f'https://www.gravatar.com/{h}.json').read()
print(data.decode())
"
```

## OPSEC Notes

- Maigret leaves connection logs on target sites (HTTP requests)
- Use `--tor` or `--proxy` for sensitive targets
- High volume searches may trigger Cloudflare/bot protection
- `--top-sites 200` with `--timeout 10` for faster, quieter scans
