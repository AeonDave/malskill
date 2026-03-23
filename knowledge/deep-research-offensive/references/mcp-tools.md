# MCP Web Tools — Precise Usage Reference

Full parameter reference and call patterns for the web research tools available in this environment.
Verified against official documentation and live-tested.

---

## Jina Reader (primary — always available)

Converts any web page to clean markdown. No authentication, no MCP dependency. Accessed via `fetch_webpage`.

### Read a page

```
fetch_webpage → https://r.jina.ai/{target-url-with-scheme}
```

Example: `fetch_webpage` on `https://r.jina.ai/https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX`

**What it does:**
- Strips ads, navigation, popups, cookie banners
- Returns main content as clean markdown with headings, lists, links, code blocks
- Handles complex layouts, documentation sites, news articles, blog posts
- Preserves outbound links (critical for recursive research)

**When to use:** Default for all pages. Try Jina Reader first, escalate only if it fails.

**Limitations:**
- Heavy JS-rendered SPAs may return incomplete content → escalate to Playwright
- Some paywalled sites may return only preview content

### Search the web

```
fetch_webpage → https://s.jina.ai/{search-query}
```

Example: `fetch_webpage` on `https://s.jina.ai/CVE-2024-XXXXX exploit PoC github`

**What it does:**
- Searches the web and returns results as structured markdown
- Includes titles, URLs, and snippets for each result
- Always available — no MCP dependency, no API key

**When to use:** When Tavily is unavailable, or as a complementary search engine.

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
| `include_raw_content` | bool/string | false | Full page content inline; prefer 2-step search→Jina Reader instead |
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
5. Post-filter: discard results with `score < 0.5` before fetching full content
6. Do NOT use `include_raw_content: true` for bulk queries — use Jina Reader on promising URLs instead (cleaner, more reliable)

### Other Tavily tools

#### `mcp_io_github_tav_tavily_extract`

Extract content from one or more URLs. Use when Jina Reader is unavailable or for structured extraction.

#### `mcp_io_github_tav_tavily_crawl`

Multi-page crawl of a site. Most expensive — use only for vendor advisory portals. Keep limit low.

#### `mcp_io_github_tav_tavily_map`

Enumerates all URLs of a site. Use before crawling an unknown vendor portal.

```
url: "https://vendor.com/security"
max_depth: 2
max_breadth: 10
select_paths: ["/advisory", "/security", "/cve", "/bulletins"]
```

---

## Playwright — `mcp_microsoft_pla_browser_run_code`

Required for: JavaScript-rendered tables (ExploitDB search), SPAs, login-gated content, xcancel Twitter search.

### Use only when
- Jina Reader returns empty or incomplete content
- Content requires browser-level JS execution (DataTables, React SPAs)
- Social media proxies (xcancel) that are JS-rendered

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

---

## Fetch Escalation Decision Tree

```
Page URL identified
  │
  ├─ Try Jina Reader (fetch_webpage → https://r.jina.ai/{url})
  │   → Content OK? → Save to intermediate file
  │
  ├─ Jina returned empty/broken?
  │   → Try fetch_webpage on the URL directly
  │
  ├─ Still insufficient?
  │   → Try Tavily extract (if available)
  │
  └─ Still empty / JS-rendered content?
      → Use Playwright with waitUntil:'networkidle'
```

**Run independent fetches in parallel** — different URLs have no dependency.

---

## X/Twitter — xcancel + FxTwitter API

### xcancel — zero-auth Twitter search proxy (Playwright)

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

### FxTwitter API — zero-auth JSON

No API key, no registration. Returns clean JSON with full post text, media, author metrics, and thread replies.

**Endpoints:**
```
# Post or thread (full text, media, metrics, replies)
https://api.fxtwitter.com/status/{POST_ID}

# User profile
https://api.fxtwitter.com/{username}
```

**Fetch with Jina Reader** (preferred — always available):
```
fetch_webpage → https://r.jina.ai/https://api.fxtwitter.com/status/{POST_ID}
```

**Fetch with Tavily extract** (if available, for structured data):
```
tool: tavily_extract
url: https://api.fxtwitter.com/status/{POST_ID}
```

**Typical workflow:**
1. xcancel Playwright search → get post URLs from results
2. Extract post ID from URL: `x.com/user/status/{ID}` or `twitter.com/user/status/{ID}`
3. Jina Reader on `https://api.fxtwitter.com/status/{ID}` → full context, media, thread

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

## Telegram — zero-auth access methods

### Method 1 — tg.i-c-a.su (best, full JSON)

Returns full JSON with messages, media URLs, views, reactions.

```
# Fetch with Jina Reader
fetch_webpage → https://r.jina.ai/https://tg.i-c-a.su/json/{channel}

# Or direct fetch
fetch_webpage → https://tg.i-c-a.su/json/{channel}

# Paginate backwards
https://tg.i-c-a.su/json/{channel}?before={message_id}

# RSS feed
https://tg.i-c-a.su/rss/{channel}
```

### Method 2 — t.me/s/ preview (Playwright)

Last ~30 posts from public channels. JS-rendered.

```javascript
async (page) => {
  await page.goto('https://t.me/s/news4hack', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('.tgme_widget_message', { timeout: 15000 }).catch(() => null);
  return (await page.locator('.tgme_widget_message').allInnerTexts()).slice(0, 20);
}
```

### Method 3 — Tavily search (indexed snippets)

```
query: CVE-2025 PoC exploit site:t.me
search_depth: fast, max_results: 10
```
