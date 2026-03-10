# MCP Web Tools — Precise Usage Reference

Full parameter reference and call patterns for the web research MCP tools available in this environment.
Verified against official documentation and live-tested.

---

## Tavily — `mcp_io_github_tav_tavily_search`

### Full parameter reference

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `query` | string | required | Max 400 chars. One topic per query. |
| `search_depth` | enum | `basic` | `ultra-fast` / `fast` / `basic` / `advanced` |
| `chunks_per_source` | int 1–3 | — | Only available when `search_depth: advanced` |
| `max_results` | int 0–20 | 5 | More ≠ better quality; higher uses more context tokens |
| `topic` | enum | `general` | `general` / `news` / `finance` |
| `time_range` | enum | — | `day` / `week` / `month` / `year` |
| `start_date` | string | — | `YYYY-MM-DD` — precise date range lower bound |
| `end_date` | string | — | `YYYY-MM-DD` — precise date range upper bound |
| `include_domains` | string[] | — | Restrict to specific domains (max 300; keep short) |
| `exclude_domains` | string[] | — | Block domains (max 150) |
| `country` | string | — | Boost results from specific country (general topic only) |
| `include_answer` | bool/string | false | `basic` / `advanced` / `true` — LLM-generated answer (costs tokens) |
| `include_raw_content` | bool/string | false | Full page content inline; prefer 2-step search→scrape instead |
| `include_images` | bool | false | Add image URLs to results |
| `auto_parameters` | bool | false | Tavily auto-tunes params; may silently upgrade to `advanced` (2 credits) |

### Credit cost
| `search_depth` | Credits |
|---|---|
| `ultra-fast` | 1 |
| `fast` | 1 |
| `basic` | 1 |
| `advanced` | 2 |

Do not use `auto_parameters: true` in cost-sensitive contexts.

### Result fields
Each result: `title`, `url`, `content` (snippet), `score` (0–1), `published_date` (news topic only).

### Recommended patterns

```
# General research — broad sweep
search_depth: basic
max_results: 5
topic: general

# Current events / breaking advisories
search_depth: basic
topic: news
time_range: week

# Precise fact retrieval (CVSS, specific version, API field)
search_depth: advanced
chunks_per_source: 3
max_results: 5

# Domain-restricted research
search_depth: basic
include_domains: ["nvd.nist.gov", "cisa.gov", "github.com"]
max_results: 5
```

### Query best practices

1. Keep queries under 400 characters
2. One topic per query — break complex research into parallel sub-queries
3. Use `include_domains` instead of `site:` in the query string
4. For broad recon: run multiple focused queries in parallel instead of one long query
5. Post-filter: discard results with `score < 0.7` before fetching full content
6. Do NOT use `include_raw_content: true` for bulk queries — use Firecrawl scrape on promising URLs instead (cleaner, cheaper)

### Other Tavily tools

#### `mcp_io_github_tav_tavily_map`

Enumerates all URLs of a site. Use before crawling an unknown vendor portal.

```
url: "https://vendor.com/security"
max_depth: 2
max_breadth: 10
select_paths: ["/advisory", "/security", "/cve", "/bulletins"]
```

---

## Firecrawl Scrape — `mcp_firecrawl_fir_firecrawl_scrape`

Single-page content extraction. Best for advisory pages, NVD details, GitHub READMEs.

### Key parameters

| Parameter | Use |
|---|---|
| `url` | Target URL |
| `formats: ["markdown"]` | Clean readable content |
| `onlyMainContent: true` | Strip navigation/ads/footer |
| `waitFor: 5000` | MS to wait for JS rendering (try before Playwright) |

### Example

```
url: "https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX"
formats: ["markdown"]
onlyMainContent: true
```

---

## Firecrawl Extract — `mcp_firecrawl_fir_firecrawl_extract`

LLM-powered structured field extraction from one or more URLs. Returns typed JSON.

Best for: CVSS score, vector, CWE, affected versions, references — from NVD or advisory pages.

### Example

```
urls: ["https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX"]
prompt: "Extract CVE details including CVSS score, CVSS vector, CWE, affected products and versions, and all reference URLs."
schema: {
  "cvss_score": "string",
  "cvss_vector": "string",
  "cwe": "string",
  "affected_versions": ["string"],
  "references": ["string"]
}
```

**Note**: Uses more credits than scrape. Use when you need structured data; use scrape when you need full readable content.

---

## Firecrawl Crawl — `mcp_firecrawl_fir_firecrawl_crawl`

Multi-page recursive crawl of a site. Most expensive — use only for vendor advisory portals.

### Conservative parameters (always set these)

```
url: "https://vendor.com/security/advisories"
limit: 10               # hard cap on pages
maxDiscoveryDepth: 2    # depth from root URL
allowExternalLinks: false
```

---

## Playwright — `mcp_microsoft_pla_browser_run_code`

Required for: JavaScript-rendered tables (ExploitDB search), SPAs, login-gated content.

### Use only when
- Firecrawl scrape returns "Processing..." or empty tables
- Content requires browser-level JS execution

### Verified recipes

#### ExploitDB CVE search (JS DataTable — requires Playwright)
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

#### GitHub repository search
```javascript
async (page) => {
  await page.goto('https://github.com/search?q=CVE-YYYY-NNNNN+exploit&type=repositories&s=updated',
    { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('[data-testid="results-list"]', { timeout: 15000 });
  return await page.locator('[data-testid="results-list"]').innerText();
}
```

#### NVD CVE detail page (Firecrawl works fine here — Playwright fallback)
```javascript
async (page) => {
  await page.goto('https://nvd.nist.gov/vuln/detail/CVE-YYYY-NNNNN',
    { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('#vulnDetailTableView', { timeout: 10000 });
  return await page.locator('#vulnDetailTableView').innerText();
}
```

---

## X/Twitter — xcancel + FxTwitter API

### xcancel — zero-auth Twitter search proxy (`mcp_microsoft_pla_browser_run_code`)

xcancel.com mirrors Twitter's advanced search with no authentication. Page is JS-rendered — use Playwright.

**URL structure:**
```
https://xcancel.com/search?f=tweets&q={URL_ENCODED_QUERY}[&options]
```

**All query parameters:**

| Parameter | Values | Description |
|---|---|---|
| `f` | `tweets` | Content type (tweets only) |
| `q` | string | Search query (URL-encoded) |
| `since` | `YYYY-MM-DD` | Start date filter |
| `until` | `YYYY-MM-DD` | End date filter |
| `min_faves` | integer | Minimum likes — use 2–5 to filter noise |
| `f-nativeretweets` | `on` | **Include** native retweets |
| `f-media` | `on` | Include posts with any media |
| `f-videos` | `on` | Include posts with video |
| `f-news` | `on` | Include posts with news links |
| `f-native_video` | `on` | Include uploaded (native) video |
| `f-replies` | `on` | Include replies |
| `f-links` | `on` | Include posts with external links |
| `f-images` | `on` | Include image posts |
| `f-quote` | `on` | Include quote tweets |
| `f-spaces` | `on` | Include Spaces |
| `e-nativeretweets` | `on` | **Exclude** native retweets |
| `e-media` | `on` | Exclude media posts |
| `e-videos` | `on` | Exclude videos |
| `e-replies` | `on` | Exclude replies |
| (etc.) | `on` | Same pattern for all `f-` types |

**Recommended pattern for CVE/exploit research (clean, no noise):**
```
https://xcancel.com/search?f=tweets&q=CVE-YYYY-NNNNN+PoC
  &e-nativeretweets=on
  &e-replies=on
  &since=2024-01-01
  &min_faves=2
```

**Playwright recipe:**
```javascript
async (page) => {
  const query = encodeURIComponent('CVE-2024-NNNNN exploit PoC');
  await page.goto(
    `https://xcancel.com/search?f=tweets&q=${query}&e-nativeretweets=on&e-replies=on&since=2024-01-01&min_faves=2`,
    { waitUntil: 'networkidle', timeout: 30000 }
  );
  await page.waitForSelector('.timeline-item', { timeout: 15000 }).catch(() => null);
  return (await page.locator('.timeline-item').allInnerTexts()).slice(0, 20);
}
```

---

### FxTwitter API — zero-auth JSON (`mcp_firecrawl_fir_firecrawl_scrape` or `extract`)

No API key, no registration. Returns clean JSON with full post text, media, author metrics, and thread replies.

**Endpoints:**
```
# Post or thread (full text, media, metrics, replies)
https://api.fxtwitter.com/status/{POST_ID}

# User profile
https://api.fxtwitter.com/{username}
```

**Firecrawl extract — structured post data:**
```
tool: mcp_firecrawl_fir_firecrawl_extract
urls: ["https://api.fxtwitter.com/status/{POST_ID}"]
prompt: "Extract tweet text, author username, date, media URLs, like/retweet counts, and any reply tweets."
schema: {
  "text": "string",
  "author": "string",
  "date": "string",
  "likes": "number",
  "retweets": "number",
  "media": ["string"],
  "replies": [{ "author": "string", "text": "string" }]
}
```

**Typical workflow:**
1. xcancel Playwright search → get post URLs from results
2. Extract post ID from URL: `x.com/user/status/{ID}` or `twitter.com/user/status/{ID}`
3. Firecrawl extract `https://api.fxtwitter.com/status/{ID}` → full context, media, thread

---

### Python — twikit (bulk/scripted Twitter research)

For volume collection in authorized OSINT scripts.
**Requires a real X account** — guest mode is blocked by Cloudflare in twikit 2.x.

```python
from twikit import Client  # pip install twikit

client = Client(language='en-US')

# First run: login and save cookies (cookies_file auto-saved by twikit)
await client.login(
    auth_info_1='your_username',      # username, phone, or email
    auth_info_2='you@example.com',    # recommended: email as second factor
    password='yourpassword',
    totp_secret='BASE32SECRET',       # omit if no 2FA
    cookies_file='cookies.json',      # twikit saves/loads automatically
)

# Subsequent runs: load saved session without re-authenticating
client.load_cookies('cookies.json')

# Search (product: 'Latest' | 'Top' | 'Media', count max=20)
tweets = await client.search_tweet('CVE-2024-NNNNN PoC exploit', 'Latest', count=20)
for tweet in tweets:
    print(f"@{tweet.user.screen_name} [{tweet.created_at}]")
    print(tweet.text)  # or tweet.full_text (alias, str|None)

# Paginate with .next()
next_page = await tweets.next()

# User profile
user = await client.get_user_by_screen_name('taviso')
print(user.followers_count)
```

Use `scripts/twitter_search.py` for a full CLI wrapper with auth, pagination, filters, and JSON output.

---

## Escalation Decision Tree

```
Need to research a topic?
  → Tavily search (basic, max_results:5) — always start here

Found a promising URL, need full content?
  → Firecrawl scrape (onlyMainContent:true)
  → If empty/broken: add waitFor:5000
  → If still JS-blocked: Playwright with networkidle

Need specific structured fields from a known URL?
  → Firecrawl extract with JSON schema (skips reading noise)

Need to discover all pages of a vendor site?
  → Tavily map (max_depth:2, select_paths:[...])
  → Then Firecrawl scrape or crawl (limit:10) on relevant pages

Multiple independent searches?
  → Run ALL in parallel (different URLs or queries = no dependency)
```
