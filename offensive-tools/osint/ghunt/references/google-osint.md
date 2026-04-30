# GHunt — Google OSINT Reference

## Google Dorks for Target Discovery

```
# Find Google-linked profiles
"@gmail.com" site:linkedin.com "target company"
"target name" site:google.com/maps/contrib

# Google Drive exposed files
site:drive.google.com "target.com"
site:docs.google.com "target.com" "confidential"
site:docs.google.com inurl:/spreadsheets/d "password" OR "api key"

# Google Calendar public events
site:calendar.google.com "target company"

# Google Sites
site:sites.google.com "target company"

# Google Groups leaks
site:groups.google.com "target.com"
```

## Google Drive / Docs Metadata

```bash
# Drive file metadata (public link)
FILEID="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
curl -s "https://www.googleapis.com/drive/v3/files/${FILEID}?key=<API_KEY>&fields=name,owners,createdTime,modifiedTime"

# Without API key (limited)
curl -s "https://docs.google.com/document/d/${DOCID}/export?format=txt"

# Google Docs revision history (if edit access)
# File → Version history → See version history
```

## Maps Reviews — Location Data

Google Maps reviews reveal:
- Locations visited (business names, addresses)
- Review patterns (frequency = regularity of visits)
- Profile photo in reviews context

```bash
# Direct review URL from Gaia ID
https://www.google.com/maps/contrib/<GAIA_ID>/reviews

# Scrape with ghunt
ghunt gaia <GAIA_ID>  # includes Maps activity summary
```

## YouTube Channel from Gmail

```bash
# Check if email has YouTube channel
curl -s "https://www.googleapis.com/youtube/v3/channels?forUsername=<username>&key=<KEY>&part=snippet"

# Or: search YouTube for the name from ghunt
# youtube.com/results?search_query=<name>
```

## Google Play Reviews

```bash
# Reviews visible via Google Maps profile
https://www.google.com/maps/contrib/<GAIA_ID>

# Play Store reviews (via ghunt play)
ghunt play target@gmail.com
# Reveals: app names, review text, ratings
# Useful for: target's occupation hints, interests, security tools installed
```

## Epieos (GHunt Web Alternative)

`https://epieos.com` — web interface wrapping similar Google OSINT:
- Enter email → returns Google profile, Gaia ID, linked services
- No cookie auth needed (uses their backend)
- Free tier: limited queries

## Google Analytics ID Pivot

If a website has a Google Analytics ID (UA-XXXXXX or G-XXXXXX):
```bash
# Find other sites owned by the same person/org
curl -s "https://osint.sh/analytics/?query=UA-XXXXXX"
# or: publicwww.com/websites/UA-XXXXXX
```

## Google Tag Manager ID Pivot

```bash
# GTM IDs often cross domains (GTM-XXXXXX)
curl -s "https://publicwww.com/websites/GTM-XXXXXX"
```

## Google Photos Shared Albums

```bash
# Shared album URL → extract owner
ghunt gaia <owner_gaia_from_album_url>

# If album is embedded in a site:
# Check page source for: photos.app.goo.gl or lh3.googleusercontent.com
```

## Reverse Image Search (Profile Photo)

After getting profile photo from ghunt:

```bash
# Download photo
PHOTO_URL="https://lh3.googleusercontent.com/..."
curl -O photo.jpg "$PHOTO_URL"

# Automated reverse search (pimeyes alternative)
# Manual: tineye.com, yandex.com/images, Google Images
# Paid: pimeyes.com (face recognition)

# yandex API (best for faces)
curl -X POST "https://yandex.com/images/search?rpt=imageview&format=json" \
  --form "upfile=@photo.jpg"
```

## Gmail Availability Check

```bash
# Check if an email exists (via account recovery probe)
curl -s "https://accounts.google.com/_/signup/validatepersonalinfo?hl=en" \
  -d "Email=target@gmail.com" | grep -i "taken\|available"

# Or use holehe which does this via password-reset probe
holehe target@gmail.com
```
