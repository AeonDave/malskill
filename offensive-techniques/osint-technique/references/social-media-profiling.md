# Social Media Profiling

Social media platforms host billions of public profiles, posts, comments, and metadata. Each platform has distinct visibility, archival challenges, and research tactics.

## Platform-Specific Techniques

### X (Twitter)

- **snscrape** (CLI): broken for X since mid-2023 (login-wall; author will not add auth). Only viable against Wayback-archived pages; live public-tweet scraping requires paid X API (pay-per-use credits) or logged-in tooling.
- **Advanced Search**: `from:@username since:2024-01-01 until:2024-12-31` for time scoping.
- **Wayback Machine**: Archive.org snapshots; useful for deleted tweets.
- **Follower analysis**: Mutual followers, friends of friends → social graph.

### LinkedIn

- **Web scraping**: LinkedIn API is restrictive; manual profile visits or light scraping tools.
- **Company pages**: Employee lists, hiring activity.
- **Endorsements**: Reveal professional associations.
- **Job search**: `site:linkedin.com "title:engineer" "company X"` to find specific employees.

### Instagram

- **Picuki** (picuki.com): Instagram service shut down early 2025 (domain now targets TikTok only). Successor viewers (Imginn, Storiesig, Iganony) come and go — verify freshness before use.
- **Geolocation tags**: Geotag data reveals location + time.
- **Stories**: Ephemeral content; captured via screenshot or archived via third-party.
- **Following/followers**: Social graph analysis.

### GitHub

- **Public profiles**: Repos, starred projects, contributions.
- **Commits**: Author email often reveals employment/domain.
- **Organizations**: Employment affiliations.
- **Search**: `org:companyname language:python` → find company repositories.

### Telegram

- **TGStat** (tgstat.com): Channel analytics, growth, overlaps.
- **Telemetr** (telemetr.io): Similar analytics; Russian interface.
- **Public channels**: `https://t.me/s/<channel>` access via browser.

### Mastodon & Fediverse

- **FediSearch** (fedisearch.skorpil.cz): Cross-instance public post search.
- **Fedifinder**: original (`fedifinder.glitch.me`) discontinued 2023-12 (X API loss); Glitch ended app hosting on 2025-07-08. Successor at `fedifinder.party`.
- **Instance enumeration**: [Fediverse Observer](https://fediverse.observer/) lists instances + moderation policies.
- **WebFinger**: `https://<instance>/.well-known/webfinger?resource=acct:<user>@<instance>` returns ActivityPub actor URL.

### Bluesky (AT Protocol)

- **Handle resolver**: `https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=<handle>` → DID.
- **Identity document**: `https://plc.directory/<did>` shows handle history, PDS endpoint.
- **Firesky** (firesky.tv): Real-time keyword/hashtag monitoring.
- **Atlas** (bsky.jazco.dev; previously SkyView): engagement-based social graph for Bluesky.

### Discord

- **Less structured OSINT**: No public API for member enumeration (unless server is very open).
- **Manual investigation**: Profile URLs, public server listings.
- **Linked accounts**: Users may link social media (visible if profile allows).

### TikTok

- **Profile geolocation**: Location tags in videos.
- **Trending sounds**: May identify creator location by sound origin.

### Reddit

- **Reveddit** (reveddit.com): client-side app, maintained as of 2026-11. Add `ve` to a reddit URL (`reveddit.com/user/<name>`, `/r/<sub>`, `/domain/<d1,d2>`) to see removed content; user pages are compared against the same content shown elsewhere on reddit, subreddit pages against archived Pushshift data. Reads run from your browser against reddit.com or oauth.reddit.com with your own API key. The **Reveddit Real-Time** extension notifies on removals/locks for your logged-in account and items you subscribe to, and scans an open thread or profile for mod removals while signed in.
- **Subreddit analysis**: Communities reveal interests, beliefs, affiliations.

---

## Social Graph Analysis

### Relationship Mapping

- **Follower/following**: Visible on most platforms.
- **Mutual connections**: Overlap between user A's followers and user B's followers.
- **Behavioral clustering**: Users interacting with same posts/hashtags → likely community.

### Tools

- **Maltego**: Automated relationship mapping (commercial; extensive social connectors).
- **NetworkX (Python)**: Build network graphs from social data.
- **Neo4j**: Graph database for relationship visualization.

---

## Content Archives & Preservation

### Archive Methods

- **archive.today**: One-page content archiver with screenshot.
- **Wayback Machine** (archive.org): Snapshots of websites (including social profiles).
- **URLScan.io**: On-demand webpage scan; resource map + screenshot.
- **SingleFileZ** (browser extension): Offline HTML archives.
- **ArchiveBox**: Self-hosted web archiver (WARC export).

### Why Archive

- Platforms delete content (tweets, stories, posts).
- Users delete/deactivate accounts.
- Screenshots can be edited; archive captures (WARC, SingleFile) are ordinary files and can be edited too — hash the capture and record its retrieval time.
- Reproducibility: timestamp + URL + hash.

---

## Platform-Specific Risks

### Account Deactivation

- **Ephemeral data**: Story/story-like features disappear after 24-48 hours.
- **Account deletion**: May make historical posts inaccessible.
- **Mitigation**: Archive early and often.

### API Changes & Access Restrictions

- **X (Twitter)**: API paywalled (pay-per-use credits); snscrape broken since mid-2023. Public-data collection now requires paid API, logged-in scrapers, or Wayback for historical.
- **Instagram, TikTok**: No official API for scraping; rely on web scraping or Picuki-like alternatives.
- **LinkedIn**: no people-search API (OpenID Connect and the Marketing APIs cover the signed-in member and pages they administer). Logged-out requests get public profile pages (`/in/<slug>`) and company pages; people search and feeds redirect to the authwall.

### Geoblocking & Language

- **Content varies by region** (geo-restricted posts, language-specific networks).
- **Mastodon/Bluesky instances**: May require understanding instance-specific moderation.
- **Chinese platforms** (WeChat, Douyin, Weibo): Require local accounts or VPN; language barriers.

---

## Workflow: Profile a Person via Social Media

1. **Username enumeration**: Sherlock/Maigret on known username.
2. **Each platform found**: Visit profile, note public data (posts, followers, location, employment).
3. **Activity patterns**: Posting times, timezones, frequency hints at location/routine.
4. **Connections**: Followers, following, mutual friends → social graph.
5. **Content analysis**: Topics, engagement, communities → interests/beliefs/professional focus.
6. **Linked accounts**: Cross-platform usernames, email addresses, phone numbers.
7. **Archive everything**: Screenshots + archive.today/Wayback for reproducibility.
8. **Timeline construction**: Account creation → current; major posts/events.
9. **Risk assessment**: Involvement in problematic groups/content?
10. **Report**: Profile summary, social graph, activity timeline, breach exposure (if any), confidence levels.

---

## Anti-Patterns

- **Over-interpreting likes/follows**: Following someone is not endorsement.
- **Single platform = complete profile**: People often have different personas on different platforms.
- **Deleted content = truth hidden**: May simply mean privacy preference, not evidence of wrongdoing.
- **Geotags = exact location**: Geotags can be spoofed or from nearby locations; validate via landmarks.
- **Ignoring private accounts**: Can't scrape; focus on public interactions.
