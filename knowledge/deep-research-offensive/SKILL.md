---
name: deep-research-offensive
description: "Offensive security research: CVE analysis, exploit research, vulnerability assessment, red team reconnaissance, and threat intelligence synthesis. Use when researching CVEs, vulnerabilities, exploits, attack chains, PoC code, OSINT targets, red team planning, or security advisories. Uses MCP tools — Tavily, Firecrawl, Playwright — for live intelligence gathering."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
compatibility: "Requires MCP tools: Tavily, Firecrawl, Playwright. Authorized research use only."
---

# Deep Research — Offensive Security

Systematic offensive research workflow covering CVE analysis, exploit research, vulnerability assessment, and red team intelligence. Designed for authorized security research contexts.

> **Scope**: Use only against targets for which you have explicit written authorization.

---

## MCP Tool Reference (verified)

| Function name | Tool | Use |
|---|---|---|
| `mcp_io_github_tav_tavily_search` | Tavily Search | Keyword search across the web — primary search tool |
| `mcp_io_github_tav_tavily_map` | Tavily Map | Enumerate URLs of an advisory/doc site before scraping |
| `mcp_firecrawl_fir_firecrawl_scrape` | Firecrawl Scrape | Full page content from a known URL |
| `mcp_firecrawl_fir_firecrawl_extract` | Firecrawl Extract | Structured JSON fields from a known URL — fastest for CVSS, CPE |
| `mcp_firecrawl_fir_firecrawl_crawl` | Firecrawl Crawl | All pages of a multi-page advisory portal |
| `mcp_microsoft_pla_browser_run_code` | Playwright | JS-rendered pages, DataTables (ExploitDB), login-gated content |
| xcancel.com via Playwright | X/Twitter Search | No-auth Twitter search proxy — tweets about CVEs, malware, PoCs |
| `api.fxtwitter.com` via Firecrawl | FxTwitter API | Zero-auth JSON for full post/thread content and user info |
| `tg.i-c-a.su/json/{channel}` via Firecrawl | Telegram (zero-auth) | Full JSON messages from any public Telegram channel |
| `t.me/s/{channel}` via Playwright | Telegram preview | Last ~30 posts from public channels, JS-rendered |

---

## Call Optimization

Follow this decision tree — **stop at first success** to avoid wasted calls:

```
1. Need broad search across multiple sites?
   → Tavily search  (fast, 1 credit)

2. Need specific fields from a known URL (CVSS, CPE, refs)?
   → Firecrawl extract  with JSON schema  (structured, 1-shot)

3. Need full page content from a known URL?
   → Firecrawl scrape  with onlyMainContent:true

4. Firecrawl returned "Processing..." or empty tables?
   → Playwright  with waitUntil:'networkidle'

5. Need ALL pages of a site (vendor bulletin portal)?
   → Firecrawl crawl  (most expensive — use last, limit ≤ 10)
```

**Run independent calls in parallel** — Tavily searches and Firecrawl calls on different URLs are independent.

---

## Tavily: Query Optimization (from official docs)

### Query rules
- **Max 400 characters** per query — treat as a concise web search, not a prompt
- **One topic per query** — break complex research into focused sub-queries run in parallel
- **Use `include_domains`** to restrict to trusted sources (max 300 domains; keep the list short)
- **Use `exclude_domains`** to remove noise (max 150 domains)
- **Never use `site:` inside the query string** — use the `include_domains` parameter instead

### `search_depth` — choose by use case

| Depth | Credits | Content type | When to use |
|---|---|---|---|
| `ultra-fast` | 1 | NLP summary | Real-time, latency-critical |
| `fast` | 1 | Ranked chunks | Quick targeted snippets |
| `basic` | 1 | NLP summary | General-purpose (default) |
| `advanced` | 2 | Ranked chunks | Specific facts, highest precision |

- Use `basic` for broad discovery (recon, threat intel sweep)
- Use `advanced` + `chunks_per_source: 3` when you need the exact field (CVSS vector, affected version)
- Avoid `auto_parameters: true` — it may silently upgrade to `advanced` (2 credits)

### `topic` parameter
- `general` — broad web (default)
- `news` — news sources only; includes `published_date` in results — use for "exploited in the wild" intel
- `finance` — financial sources

### Time filtering
- `time_range`: `day` / `week` / `month` / `year` — filter by recency
- `start_date` / `end_date`: `YYYY-MM-DD` — precise date range for advisory freshness checks

### `max_results`
- Default: 5 — sufficient for most CVE queries
- Use 10 only when you need broad coverage (recon sweep)
- Higher values degrade average result quality and consume more context tokens

### Post-processing results
- Filter by `score > 0.7` before passing URLs to Firecrawl — discard low-relevance results
- Use `title` field for quick keyword scan before fetching full content

---

## Research Workflows

### CVE Deep Dive

Run steps 1–3 in parallel, then follow up on found URLs:

**Step 1 — NVD structured data** (Firecrawl extract — fastest for structured fields)
```
tool: mcp_firecrawl_fir_firecrawl_extract
urls: ["https://nvd.nist.gov/vuln/detail/CVE-YYYY-NNNNN"]
schema: {
  "cvss_score": string,
  "cvss_vector": string,
  "cwe": string,
  "affected_versions": [string],
  "references": [string]
}
```

**Step 2 — PoC search** (3 Tavily queries in parallel)
```
query 1: "CVE-YYYY-NNNNN" exploit PoC
  include_domains: ["github.com"]
  search_depth: basic, max_results: 5

query 2: CVE-YYYY-NNNNN exploit
  include_domains: ["sploitus.com", "packetstormsecurity.com"]
  search_depth: basic, max_results: 5

query 3: CVE-YYYY-NNNNN exploited ransomware APT campaign
  topic: news, time_range: year, max_results: 5
```

**Step 3 — ExploitDB** (Playwright — required, JS-rendered DataTable)
```javascript
async (page) => {
  await page.goto('https://www.exploit-db.com/search?cve=YYYY-NNNNN',
    { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForFunction(() => {
    const rows = document.querySelectorAll('#exploits-table tbody tr');
    return rows.length > 0 && !rows[0].textContent.includes('Processing');
  }, { timeout: 15000 }).catch(() => null);
  return await page.locator('#exploits-table tbody tr').allInnerTexts();
}
```

**Step 4 — GitHub PoC repos** (Firecrawl scrape, for each repo found in step 2)
```
tool: mcp_firecrawl_fir_firecrawl_scrape
formats: ["markdown"]
onlyMainContent: true
```

**Step 5 — CISA KEV check + vendor advisory** (parallel)
```
Firecrawl extract: https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-YYYY-NNNNN
  schema: { "in_kev": bool, "due_date": string, "required_action": string }

Firecrawl scrape: [vendor advisory URL from NVD references]
  onlyMainContent: true
```

---

### Target Reconnaissance

Run all queries in parallel (one topic per query):

```
query 1: [product] [version] vulnerability 2025
  search_depth: basic, max_results: 5

query 2: [product] CVE critical severity
  include_domains: ["nvd.nist.gov", "cve.mitre.org"]
  search_depth: basic, max_results: 5

query 3: [product] exploit PoC
  include_domains: ["github.com", "exploit-db.com", "sploitus.com"]
  search_depth: basic, max_results: 5

query 4: [product] security advisory patch
  include_domains: ["[vendor.com]"]
  time_range: year, search_depth: basic, max_results: 5
```

Use Tavily map to enumerate a vendor portal before crawling:
```
tool: mcp_io_github_tav_tavily_map
url: https://[vendor.com]/security
max_depth: 2, max_breadth: 10
select_paths: ["/advisory", "/security", "/cve", "/vulns"]
```

---

### ATT&CK Technique Lookup

```
tool: mcp_firecrawl_fir_firecrawl_scrape
url: https://attack.mitre.org/techniques/T[ID]/
onlyMainContent: true

# Cross-check with Tavily for real-world procedure examples:
query: T[ID] [technique name] red team procedure example
search_depth: advanced, chunks_per_source: 3, max_results: 5
```

---

## Output Template

```
## Target Summary
[Asset, scope, engagement type]

## Vulnerability Matrix
| CVE | CVSS | PoC | In CISA KEV | Priority |
|-----|------|-----|-------------|----------|

## CVE Deep Dives

### CVE-YYYY-NNNNN — [Short name]
- **CVSS**: X.X (CVSS:3.1/AV:.../AC:.../PR:.../UI:.../S:.../C:.../I:.../A:...)
- **CWE**: CWE-[ID] — [name]
- **Affected**: [product] [versions from CPE]
- **PoC**: [URL or "not public"]
- **Patch / Advisory**: [URL]
- **CISA KEV**: Yes/No — due date if applicable
- **Exploited ITW**: Yes/No — [source + date]
- **Red team notes**: [access conditions, auth required, mitigations to bypass, chaining potential]

## Attack Chain
[Phase → Technique T[ID] → CVE → method]

## Mitigations and Detection
[Patch, config, log source / SIEM rule per phase]

## Sources
[1] URL — source — date — score
```

---

## X/Twitter Intelligence

X/Twitter is a primary real-time source for:
- CVE PoC drops and 0day disclosures
- Malware samples, C2 IOCs, ransomware variants
- Red team tooling releases (new BOFs, evasion techniques)
- Threat actor activity and campaign announcements
- Security researcher commentary and advisories

### xcancel — zero-auth Twitter search proxy

xcancel.com proxies Twitter's advanced search without any authentication. Use Playwright (page is JS-rendered).

**Basic search:**
```
https://xcancel.com/search?f=tweets&q=CVE-2024-NNNNN+exploit
```

**Full options — all parameters:**
```
https://xcancel.com/search?f=tweets
  &q=windows+exploit          # URL-encoded search query
  &since=2025-01-01           # date range start (YYYY-MM-DD)
  &until=2026-02-18           # date range end (YYYY-MM-DD)
  &min_faves=5                # minimum likes — filters noise
  # --- include filters (f-) ---
  &f-nativeretweets=on        # include native retweets
  &f-media=on                 # include posts with media
  &f-videos=on                # include posts with video
  &f-news=on                  # include news links
  &f-native_video=on          # include native (uploaded) video
  &f-replies=on               # include replies
  &f-links=on                 # include external links
  &f-images=on                # include image posts
  &f-quote=on                 # include quote tweets
  &f-spaces=on                # include Spaces
  # --- exclude filters (e-) ---
  &e-nativeretweets=on        # exclude retweets
  &e-replies=on               # exclude replies (thread noise)
```

**Typical offensive research query (no retweets, no replies, date-filtered):**
```
https://xcancel.com/search?f=tweets&q=CVE-2024-NNNNN+PoC&e-nativeretweets=on&e-replies=on&since=2024-01-01&until=2026-02-18&min_faves=2
```

**Playwright recipe for xcancel:**
```javascript
async (page) => {
  const query = encodeURIComponent('CVE-2024-NNNNN exploit PoC');
  await page.goto(
    `https://xcancel.com/search?f=tweets&q=${query}&e-nativeretweets=on&e-replies=on&since=2024-01-01&min_faves=2`,
    { waitUntil: 'networkidle', timeout: 30000 }
  );
  await page.waitForSelector('.timeline-item', { timeout: 15000 }).catch(() => null);
  const tweets = await page.locator('.timeline-item').allInnerTexts();
  return tweets.slice(0, 20); // cap at 20 results
}
```

### FxTwitter API — zero-auth JSON for post/thread content

FxTwitter exposes a public read-only API with no authentication, no rate-limit registration, and clean JSON output. Use Firecrawl scrape to fetch.

**Fetch a post or thread (includes full text, media, metrics, replies):**
```
https://api.fxtwitter.com/status/{POST_ID}
```

**Fetch user info:**
```
https://api.fxtwitter.com/{username}
```

**Example — fetch post and extract structured fields:**
```
tool: mcp_firecrawl_fir_firecrawl_extract
urls: ["https://api.fxtwitter.com/status/1890765432198765432"]
prompt: "Extract tweet text, author, date, media URLs, and reply tweets if present."
schema: {
  "text": "string",
  "author": "string",
  "date": "string",
  "media": ["string"],
  "replies": [{ "author": "string", "text": "string" }]
}
```

**Usage pattern — when to use FxTwitter API:**
1. Tavily or xcancel surfaces an interesting post URL
2. Extract the post ID from the URL: `twitter.com/user/status/{ID}` or `x.com/user/status/{ID}`
3. Fetch `https://api.fxtwitter.com/status/{ID}` to get the full thread with metadata

### Python option — twitter_search.py (scripts/twitter_search.py)

Batch/scripted search using `twikit 2.x`.

> **⚠ Requires a real X account.** Guest/anonymous mode is blocked by Cloudflare since 2023.
> Tavily (`site:twitter.com OR site:x.com`) is the **zero-auth alternative** and works without any account.

```bash
pip install twikit

# First run: login and save session cookies (cookies_file auto-handled by twikit)
python scripts/twitter_search.py "CVE-2024-12345 PoC exploit" \
    --auth-info-1 your_username --auth-info-2 you@example.com \
    --password yourpassword --cookies-file cookies.json

# Subsequent runs: cookies exist → no re-login needed
python scripts/twitter_search.py "windows 0day" --cookies-file cookies.json \
    --since 2025-01-01 --until 2026-02-18 \
    --min-likes 5 --count 20 --pages 3 --json -o results.json

# Latest tweets from a specific researcher
python scripts/twitter_search.py "nmap red team" --cookies-file cookies.json \
    --mode Latest --from-user taviso

# User profile
python scripts/twitter_search.py --user malwareunicorn --cookies-file cookies.json
```

Key flags: `--auth-info-1`, `--auth-info-2`, `--password`, `--totp-secret`, `--cookies-file`, `--mode Latest|Top|Media`, `--count N` (max 20), `--pages N` (pagination), `--since/--until YYYY-MM-DD`, `--min-likes N`, `--from-user`, `--lang CODE`, `--json`, `-o FILE`.

Output includes `fxtwitter_url` for each result — fetch it with Firecrawl extract to get the full thread.

**When to use twikit vs Tavily:**
- **No account** → use Tavily with `site:twitter.com OR site:x.com`
- **Account available + need volume/pagination/filters** → use `twitter_search.py`

---

## Telegram Intelligence

Telegram is a primary distribution channel for:
- CVE PoC drops (often before any public advisory)
- Malware samples, stealer logs, ransomware source leaks
- Red team tool releases (C2s, BOFs, loaders, evasion)
- Threat actor chatter, initial access broker ads, data breach announcements
- Content removed from GitHub or X within hours of publication

### Zero-auth access methods (no account needed)

**Method 1 — tg.i-c-a.su (best):** Returns full JSON with messages, media URLs, views, reactions.
```
tool: mcp_firecrawl_fir_firecrawl_scrape
url: https://tg.i-c-a.su/json/{channel}
onlyMainContent: false

# Paginate backwards with ?before={message_id}
https://tg.i-c-a.su/json/news4hack?before=500

# RSS feed for feed-reader-style polling
https://tg.i-c-a.su/rss/{channel}
```

**Method 2 — t.me/s/ preview:** Last ~30 posts. Use Playwright (JS-rendered).
```javascript
async (page) => {
  await page.goto('https://t.me/s/news4hack', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('.tgme_widget_message', { timeout: 15000 }).catch(() => null);
  const posts = await page.locator('.tgme_widget_message').allInnerTexts();
  return posts.slice(0, 20);
}
```

**Method 3 — Tavily search** (indexed snippets, no scraping):
```
query: CVE-2025 PoC exploit site:t.me
search_depth: fast, max_results: 10
```

### Curated offensive security channels

**Tier S — use first**

| Channel | Link | Members | Focus |
|---|---|---|---|
| @news4hack (Pentester) | `t.me/news4hack` | ~2.8K | CVE + PoC GitHub links daily, red team, AD attacks, web RCE/LPE |
| @cveNotify | `t.me/cveNotify` | ~17.7K | Real-time CVE notifications — fastest CVE feed |
| @learnexploit (0Day.Today) | `t.me/learnexploit` | ~21K | Public exploits, 0-day, PoC web/server, hacking tools — richest PoC source |

**Tier A — strong signal**

| Channel | Link | Focus |
|---|---|---|
| @PentestingNews | `t.me/PentestingNews` | Pentesting, red team, OSINT, malware analysis, RE (~20K) |
| @BlueRedTeam | `t.me/BlueRedTeam` | Red team tools, CVE PoC, intranet attacks (~5.2K) |
| @androidMalware | `t.me/androidMalware` | Android/iOS exploits, mobile CVEs, spyware analysis (~43K) |
| @bugbountyresources | `t.me/bugbountyresources` | Writeups, new vulns, bug bounty tips (~10K) |
| @githubredteam | `t.me/githubredteam` | Chinese red team GitHub repos monitor — fresh PoCs, often before English coverage |
| @sochub_ar | `t.me/sochub_ar` | SOCHUB CVE channel — advisory-level CVE feed, structured |

**Tier B — niche / underground signal**

| Channel | Link | Focus | Notes |
|---|---|---|---|
| @vxunderground | `t.me/vxunderground` | Malware samples, papers, ransomware source leaks, APT intel | Legitimate research; primary malware archive |
| @ckearsenal (御魂军火库) | `t.me/ckearsenal` | Chinese underground: PoC, exploits, C2 templates, malware analysis | High noise, high signal — filter carefully |
| @cybersecurityresources | `t.me/cybersecurityresources` | Web security, pentest notes, bug hunting (~7K) | Broad but active |

### Telegram channel research workflow

```
# 1. Check a channel's recent content (zero-auth, instant JSON)
tool: mcp_firecrawl_fir_firecrawl_scrape
url: https://tg.i-c-a.su/json/cveNotify
onlyMainContent: false

# 2. Found a relevant post? Get its full content via t.me/s/ permalink
tool: mcp_firecrawl_fir_firecrawl_scrape
url: https://t.me/s/cveNotify/{message_id}
onlyMainContent: true

# 3. Post links to GitHub PoC? → Firecrawl scrape the repo
tool: mcp_firecrawl_fir_firecrawl_scrape
url: https://github.com/{user}/{repo}
onlyMainContent: true

# 4. Broad keyword search across all indexed Telegram content
tool: mcp_io_github_tav_tavily_search
query: CVE-2025-NNNNN PoC exploit site:t.me
search_depth: fast, max_results: 10
```

---

## Operational Notes

- **Traffic**: Firecrawl and Playwright generate real HTTP traffic. On live engagements, use only Tavily (indexed/cached results) to avoid direct target contact.
- **Rate limits**: Firecrawl crawl: `limit ≤ 10`, `maxDiscoveryDepth ≤ 2`.
- **Recency**: Tavily results may be weeks old for fresh CVEs — always verify CVSS/KEV directly from NVD and CISA via Firecrawl extract.
- **Score filtering**: Discard Tavily results with `score < 0.5` before fetching full content with Firecrawl.

## References

- [references/mcp-tools.md](references/mcp-tools.md) — full parameter reference for Tavily, Firecrawl, Playwright with verified recipes
- [references/sources.md](references/sources.md) — curated security intelligence sources with domain lists ready for `include_domains`
- [references/attack-chain-templates.md](references/attack-chain-templates.md) — ATT&CK-aligned attack chain templates
