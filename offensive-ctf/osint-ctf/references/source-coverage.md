# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-osint`
- Target skill: `osint-ctf`
- Preserved files: 4

## Imported files and topic cues

### `source-skill.md`

- CTF OSINT
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- DNS recon
- Image metadata
- Web archive
- Username lookup
- Shodan
- String Identification
- Twitter/X Account Tracking
- Tumblr Investigation
- Username OSINT
- Image Analysis & Reverse Image Search
- Geolocation
- MGRS Coordinates
- Google Plus Codes
- Metadata Extraction
- Google Dorking
- Google Docs/Sheets
- DNS Reconnaissance
- Tor Relay Lookups
- GitHub Repository Analysis

### `geolocation-and-media.md`

- Geolocation and Media Analysis
- Table of Contents
- Image Analysis
- Reverse Image Search
- Geolocation Techniques
- MGRS (Military Grid Reference System)
- Google Plus Codes / Open Location Codes
- Metadata Extraction
- Hardware/Product Identification
- Newspaper Archives and Historical Research
- Google Street View Panorama Matching
- Street View metadata API
- GET https://maps.googleapis.com/maps/api/streetview/metadata?location=LAT,LNG&key=KEY
- Street View image API
- GET https://maps.googleapis.com/maps/api/streetview?size=640x480&location=LAT,LNG&heading=90&key=KEY
- Panorama ID from page source (parsed from JavaScript):
- Look for panoId in page data structures
- Road Sign Language and Driving Side Analysis
- Post-Soviet Architecture and Brand Identification
- IP Geolocation and Attribution
- IP-API (no key required)
- ipinfo.io
- Google Lens Cropped Region Search
- Reflected and Mirrored Text Reading

### `social-media.md`

- Social Media OSINT
- Table of Contents
- Twitter/X Account Tracking
- Find all archived URLs for a username
- Also check profile images
- Check t.co shortlinks
- Tumblr Investigation
- BlueSky Advanced Search
- Username OSINT
- Platform False Positives
- Social Media General Tips
- Multi-Platform OSINT Chain
- Gaming Platform OSINT / MMO Character Lookup
- World of Warcraft character/guild lookup:
- - Blizzard API: https://develop.battle.net/documentation/world-of-warcraft
- - WoW Progress: https://www.wowprogress.com
- - Raider.IO: https://raider.io
- Search: guild name + realm name (e.g., "Blackfathom Deep Dish" on US-Turalyon)
- Steam profile search:
- - steamcommunity.com/id/[username]
- - steamid.io for SteamID lookups
- Minecraft player lookup:
- - NameMC: https://namemc.com
- - Shows skin, name history, servers

### `web-and-dns.md`

- Web and DNS OSINT
- Table of Contents
- Google Dorking
- Google Docs/Sheets in OSINT
- DNS Reconnaissance
- DNS TXT Record OSINT
- Tor Relay Lookups
- GitHub Repository Comments
- Telegram Bot Investigation
- Search browser history for Telegram URLs
- Example: https://t.me/comrade404_bot
- FEC Political Donation Research
- Wayback Machine
- Find all archived URLs for a site
- WHOIS Investigation
- Basic WHOIS lookup
- Key fields to extract:
- - Registrant name/email/org (often redacted by privacy services)
- - Creation/expiration dates (timeline correlation)
- - Name servers (shared hosting identification)
- - Registrar (can indicate sophistication level)
- Historical WHOIS (before privacy was enabled)
- Use SecurityTrails, WhoisXML API, or DomainTools
- Reverse WHOIS — find all domains registered by same entity

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
