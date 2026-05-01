# Person & Identity Research

Identity OSINT reveals who someone is, their online presence, breach exposure, and social connections—purely from public sources.

## Research Objectives

- **Profile verification**: Confirm identity, location, employment, education.
- **Breach exposure**: Which platforms/services exposed their credentials?
- **Online footprint**: Usernames, email aliases, abandoned accounts.
- **Social graph**: Connections, communities, relationships.
- **Risk assessment**: Involvement in illegal activities, extremism, fraud.

---

## Email-Centric Pivots

Email is the most powerful pivot for person research. Start with the email if you have it.

### Email → Platforms (Holehe Model)

Use **Holehe** (CLI/API) or **Epieos** (web) to check which platforms are registered to an email:

- **Input**: email address
- **Output**: Platform list (Gmail, X, LinkedIn, Facebook, GitHub, Adobe, Slack, Crunchbase, Twitter, etc.)
- **Leverage**: Found a platform? Pivot to that platform's public profile.
- **Example**: `email@example.com` registered on GitHub → check GitHub public repos, starred projects, followers, contributions.

### Email → Breach Lookups

- **Have I Been Pwned** (haveibeenpwned.com): Free breach search by email. Returns which breaches exposed the email.
- **Dehashed** (dehashed.com): Credential search; shows leaked username + password pairs.
- **LeakCheck** (leakcheck.io): Aggregated breach index; freemium access.
- **IntelX** (intelx.io): Dark web index; email/username/hash search across leaks, pastes, breaches.
- **Breached Data Alerts**: Sites like xkcd's excellent list maintain curated breach databases.

**Actionable**: If you find a password hash, feed it to VirusTotal or local cracking tools. If plaintext password, check against known compromises.

### Email → Domain Harvesting

- **Hunter.io** (API + web): Reverse email finder. Input domain → returns emails associated with that domain. Also verifies if an email is valid for a domain.
- **Clearbit** (API): Company email enrichment; returns person profile, role, location, linked social accounts.
- **RocketReach / Apollo**: Email pattern guessing for a company (firstname.lastname@domain, initials@domain, etc.).

---

## Username Enumeration

Usernames are shared across platforms. A single username can reveal profiles across social media, gaming, forums, dating sites, etc.

### Tools

- **Sherlock** (CLI): Search a username across 300+ platforms. Returns which platforms have that username registered.
- **Maigret** (CLI): Similar scope but collects additional metadata (profile URLs, names, locations).
- **What's My Name** (whatsmyname.app): Web interface; visual + copyable results.
- **OSINT Framework / IntelTechniques Tools**: Bookmarked lists of social sites + search shortcuts.

### Workflow

1. Input username.
2. Note which platforms returned matches (e.g., GitHub, Reddit, Instagram, Medium, Twitch).
3. Visit each profile (preferably via archive.today or screenshot, not directly) and note public data.
4. Look for usernames used on *different* platforms (people often have a primary + backup usernames).

---

## Social Media Profiling

Each platform has different visibility and archival challenges.

### X (Twitter)

- **snscrape** (CLI, preferred): No API key needed; scrapes public tweets, replies, likes, followers.
- **Advanced search**: `from:@username since:2024-01-01 until:2024-12-31` to scope by time.
- **Wayback Machine**: Archive.org snapshots of profiles for historical tweets.
- **Retweets, Likes, Mentions**: Follow the graph; find communities.

### LinkedIn

- **Web scraping**: LinkedIn API is limited; web scraping via tools like `linkedin2username` or manual profile visits.
- **InMail & Endorsements**: Public endorsements can reveal professional associations.
- **Company Pages**: Check who works/worked at a target company (employment history).

### Instagram

- **Picuki**: View Instagram profiles without account login.
- **Metadata & Geolocation**: Look for location tags in posts, EXIF data if available.
- **Stories Archive**: Stories disappear, but followers may remember content.

### GitHub

- **Public repos, starred projects, contributions**: Reveals interests, coding style, projects.
- **Commits**: Author name + email often in git logs.
- **Organizations & Teams**: Employment/project affiliations.

### Telegram & Discord

- **TGStat** (Telegram): Channel analytics, growth, overlaps, forwards.
- **Telemetr** (Telegram): Similar analytics.
- **Discord**: Less structured; mostly manual search + member lists if you can view them.

### Mastodon & Fediverse

- **FediSearch**: Cross-instance search for public posts.
- **Fedifinder**: Find Twitter users on Mastodon (username linking).
- **Instance exploration**: Understand which instance the user is on (affects privacy policies, logging practices).

### Bluesky (AT Protocol)

- **Handle resolver**: `https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=<handle>` returns DID (unique ID).
- **Identity document**: `https://plc.directory/<did>` shows handle history, PDS endpoint.
- **Firesky**: Real-time keyword/hashtag monitoring across entire network.
- **SkyView**: Follower graphs, post engagement, network analysis.

---

## Face & Image Search

### Reverse Face Search

- **PimEyes** (pimeyes.com): Facial search engine. Upload a face photo → returns matches across indexed sites.
- **FaceCheck** (facecheck.id) / **FaceSeek**: Similar, may have different datasets.
- **Google Lens**: Reverse image search; often finds social media matches.

**Privacy note**: Facial search results can be inaccurate; verify via other means.

### Reverse Image Search (Non-Face)

- **Google Images / Google Lens**: Standard reverse image search.
- **TinEye** (tineye.com): Specialized reverse image search; good for finding reposts.
- **Yandex Images**: Strong for Russian/Eastern European content.
- **Bing Image Search**: Alternative dataset.

### EXIF & Metadata Extraction

- **ExifTool** (CLI): Read EXIF data (geolocation, camera, timestamp).
- **Jeffrey's EXIF Viewer** (web): Online EXIF reader.
- **Forensically** (29a.ch/photo-forensics/): Error Level Analysis, metadata, clone detection.

---

## Phone Number Intelligence

### Phone Lookups

- **TrueCaller** (truecaller.com): Reverse phone search, caller ID.
- **ThatsThem** (thatsthem.com): Reverse phone + people search.
- **NumlookupAPI**: Programmatic carrier + line-type checks.
- **FreeCarrierLookup**: Carrier info (US).
- **Advanced Background Checks**: Phone → linked people.

### Carrier & Line Type

- Knowing the carrier (Verizon, AT&T, regional) can narrow down location.
- Line type (mobile, landline, VOIP) affects privacy options.

---

## People Search APIs & Databases

### Free / Freemium

- **TruePeopleSearch** (truepeoplesearch.com): Free U.S. people search.
- **WhitePages** (whitepages.com): Contact information, address history.
- **Spokeo** (spokeo.com): People search engine.
- **Webmii** (webmii.com): Web-based people finder.

### Paid / Premium

- **Pipl** (pipl.com): Deep web people search.
- **Clearbit** (clearbit.com): Company + individual enrichment (API).

---

## Geolocation & Timeline Clues

### Check-In Data

- **Swarm / Foursquare history**: If public, reveals frequent locations.
- **Google Maps Timeline**: If accessible, shows movement history.
- **Snap Map**: Public stories can reveal location + time.

### Temporal Clues

- **Post timestamps**: Timezone hints, work hours, activity patterns.
- **Account creation dates**: When did they join each platform?
- **Activity heatmaps**: Tools like SocialBlade show posting frequency.

---

## Workflow: Putting It Together

1. **Start with email**: Have I Been Pwned → breach list. Holehe → platform list.
2. **Each platform**: Visit public profile, capture data, look for linked usernames.
3. **Username enumeration**: Sherlock/Maigret on discovered usernames.
4. **Cross-reference**: Map same person across platforms (same profile pic? Same bio? Linked social graphs?).
5. **Archive everything**: Screenshots, URLs, timestamps.
6. **Validate**: Does the person exist at this employment? LinkedIn/company website match?
7. **Report**: Profile summary, breach exposure, linked identities, confidence notes.
