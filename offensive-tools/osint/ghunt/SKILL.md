---
name: ghunt
description: "Google account OSINT tool — enumerate Google profile data, linked services, Calendar events, Maps reviews, YouTube activity, and photo metadata from an email address or Gaia ID. Use when you have a Gmail address and need to map the target's Google footprint: profile photo, account creation hints, linked Android apps, location history artifacts, and public activity."
license: MIT
compatibility: "Python 3.10+; pip install ghunt; Linux/macOS/Windows; requires Google auth cookies; github.com/mxrch/GHunt"
metadata:
  author: AeonDave
  version: "1.0"
---

# GHunt

Google account OSINT — profile, services, location artifacts, linked apps from Gmail address.

## Quick Start

```bash
pip install ghunt

# First-time setup — authenticate with Google cookies
ghunt login

# Investigate a Gmail address
ghunt email target@gmail.com

# Investigate by Gaia ID (Google internal user ID)
ghunt gaia 123456789

# Investigate a Google Drive link
ghunt drive https://drive.google.com/file/d/FILEID/view
```

## Authentication Setup

GHunt requires valid Google cookies from a logged-in browser session.

```bash
# Interactive login (opens browser URL to capture cookies)
ghunt login

# Or manually export cookies from browser
# Install "Cookie-Editor" extension (Firefox/Chrome)
# Export cookies from google.com as JSON → ghunt login --file cookies.json
```

> Use a throwaway Google account for OPSEC — your account appears as a viewer in some cases.

## Commands

| Command | Target | Output |
|---------|--------|--------|
| `ghunt email <email>` | Gmail address | Profile, Gaia ID, services |
| `ghunt gaia <id>` | Google Gaia ID | Same as email |
| `ghunt drive <url>` | Google Drive link | File metadata, owner |
| `ghunt doc <url>` | Google Docs link | Document metadata |
| `ghunt calendar <id>` | Calendar ID | Public events |
| `ghunt play <email>` | Gmail | Google Play reviews |

## What GHunt Reveals

### Profile Data

- Full name (if public profile)
- Profile photo → reverse image search
- Gaia ID (Google internal identifier — persistent, links across services)
- Account type (Google Workspace vs personal)
- Last profile edit timestamp

### Linked Services

Whether the account has active:
- **Google Maps** — reviews posted (with location data)
- **YouTube** — channel (links to public videos/comments)
- **Google Calendar** — public calendars (may contain events/locations)
- **Google Play** — app reviews (reveals installed apps)
- **Google Photos** — shared albums
- **Blogger** — published posts

### Location Artifacts

- Maps reviews reveal locations visited
- Calendar events with locations
- Photo metadata (if shared)

## Common Workflows

**Full email investigation:**
```bash
ghunt email target@gmail.com
# Outputs: name, Gaia ID, profile photo URL, active services
```

**Reverse image search profile photo:**
```bash
# Get photo URL from ghunt output, then:
# yandex.com/images → search by image URL
# images.google.com → paste image URL
# tineye.com → reverse image search
```

**Drive file owner identification:**
```bash
# From a shared Google Drive link (e.g., from LinkedIn/email)
ghunt drive "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/view"
# Reveals: owner email, file name, creation date
```

**Calendar public event scraping:**
```bash
ghunt calendar target_calendar_id@group.calendar.google.com
```

**JSON output for automation:**
```bash
ghunt email target@gmail.com --json > ghunt_results.json
```

## Parse Output

```python
import json, subprocess

result = subprocess.run(
    ["ghunt", "email", "target@gmail.com", "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

print("Name:", data.get("name"))
print("Gaia ID:", data.get("gaia_id"))
print("Services:", [s for s, active in data.get("services", {}).items() if active])
```

## OPSEC Notes

- GHunt uses your Google account's cookies — the target may see view events in some products
- Use a dedicated throwaway Google account
- Rotate cookies regularly (session cookies expire)
- Maps reviews and Play reviews are publicly scraped — no notification to target

## Gaia ID Use Cases

The Gaia ID is Google's internal persistent user identifier:

```bash
# Search Gaia ID in Google URLs
https://plus.google.com/<GAIA_ID>           # legacy, redirects
https://www.google.com/maps/contrib/<GAIA_ID>/reviews  # Maps reviews
```

## Resources

| File | When to load |
|------|--------------|
| `references/google-osint.md` | Google dorking, Drive/Doc metadata extraction, Maps review scraping, Gaia ID pivot |
