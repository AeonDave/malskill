---
name: deep-research-offensive
description: "File-backed offensive security research with recursive link-following, multi-tool fetching (Jina Reader, Tavily, Playwright), and step-by-step synthesis. Use when researching CVEs, vulnerabilities, exploits, attack chains, PoC code, OSINT targets, red team planning, or threat intelligence. Saves each useful page to intermediate files, follows linked sources recursively, and produces a comprehensive research document not limited by context size."
license: MIT
metadata:
  author: AeonDave
  version: "2.0"
---

# Deep Research — Offensive Security

File-backed offensive research workflow. Each useful page is fetched, cleaned, and saved to an intermediate file. Linked pages (PoC repos, advisories, exploit code, threat intel articles) are recursively followed. All intermediate files are synthesized step-by-step into a comprehensive research document.

> **Scope**: Use only for targets with explicit written authorization.
> **Core principle**: Use the file system as extended memory. Save every useful page, then synthesize from files — never rely on context alone.

---

## Methodology

### Step 1 — Scope & Plan

1. Define the research objective (CVE analysis, target recon, technique research, threat intel)
2. Break into 3–7 sub-questions, e.g.:
   - Vulnerability details (CVSS, CWE, affected versions)
   - PoC availability (GitHub, ExploitDB, PacketStorm)
   - Active exploitation evidence (CISA KEV, APT campaigns, ITW reports)
   - Attack chain mapping (ATT&CK techniques, chaining potential)
   - Mitigations and detection (patches, SIEM rules, EDR telemetry)
3. Create the working directory:

```
.research/{topic-slug}/
├── _plan.md            # Sub-questions, priorities, URL queue, gap tracker
├── pages/              # One .md file per fetched page
└── output.md           # Final synthesized research document
```

4. Write `_plan.md` with sub-questions, priorities, and empty URL queue

### Step 2 — Initial Search Sweep

Run parallel searches across offensive sources for each sub-question:

**Tavily** (if available):
```
# CVE-specific
query: "CVE-YYYY-NNNNN" exploit PoC
include_domains: ["github.com", "exploit-db.com", "sploitus.com"]
search_depth: basic, max_results: 5

# Threat intel
query: CVE-YYYY-NNNNN exploited ransomware APT
topic: news, time_range: year, max_results: 5
```

**Jina Search** (always available):
```
fetch_webpage → https://s.jina.ai/CVE-YYYY-NNNNN exploit PoC github
```

**Social media** (for real-time intel): use xcancel/Playwright and Telegram — see [references/mcp-tools.md](references/mcp-tools.md).

From results: queue all promising URLs in `_plan.md` with source and relevance.

### Step 3 — Deep Fetch (page by page)

Process each queued URL:

**3a. Fetch** — stop at first success:

| Priority | Tool | When |
|---|---|---|
| 1 | **Jina Reader** | Default — cleanest markdown output |
| 2 | **`fetch_webpage`** (direct) | APIs, NVD JSON, raw text |
| 3 | **Tavily extract** | Structured data (CVSS, CPE, versions) |
| 4 | **Playwright** | ExploitDB tables, JS-rendered SPAs, xcancel |

**Jina Reader**: `fetch_webpage` on `https://r.jina.ai/{full-url-with-scheme}`
**Jina Search**: `fetch_webpage` on `https://s.jina.ai/{search-query}`

**3b. Evaluate**: relevant to sub-question + contains citable data? If not → mark `skipped`.

**3c. Save** to `pages/{NNN}_{slug}.md`:

```markdown
# {Page Title}

- **Source**: {URL}
- **Fetched**: {date}
- **Serves**: {sub-question}
- **Relevance**: high/medium/low
- **Type**: advisory / PoC / exploit / writeup / threat-intel / vendor-patch

## Content

{Cleaned content: CVSS data, exploit details, code snippets,
affected versions, indicators, techniques. Remove boilerplate.
Preserve all technical detail.}

## Outbound Links

- {URL1} — {PoC repo / vendor advisory / related CVE / etc.}
- {URL2} — {description}
```

**3d. Extract and queue links**: GitHub repos, vendor advisories, linked CVEs, blog references → add to `_plan.md`.

### Step 4 — Recursive Link Discovery

Repeat Step 3 for newly queued links. Stop when:
- No new relevant links
- Depth limit reached (default: 3 levels)
- Diminishing returns

Update `_plan.md`: mark each URL as `fetched`, `skipped`, or `queued`.

### Step 5 — Gap Analysis

1. Review each sub-question against intermediate files
2. Identify: missing PoC, no CVSS data, no active exploitation evidence, missing patches
3. For critical gaps → run targeted searches (Step 2) with narrower queries
4. Check social media for gaps (Twitter → xcancel, Telegram → see references)

### Step 6 — Step-by-Step Synthesis

Build `output.md` incrementally from intermediate files:

1. **Process one dimension at a time** — read only relevant files per dimension
2. For each dimension: read files → write analysis → add citations `[N]`
3. After all dimensions: executive summary, vulnerability matrix, attack chain, sources list

> Each section reads only its files. Research depth is limited by data found, not context window.

### Step 7 — Final Output

Use this structure (adapt for engagement type):

```markdown
## Target Summary
[Asset, scope, engagement type]

## Vulnerability Matrix
| CVE | CVSS | PoC | CISA KEV | Priority |
|-----|------|-----|----------|----------|

## CVE Deep Dives

### CVE-YYYY-NNNNN — [Short name]
- **CVSS**: X.X (vector)
- **CWE**: CWE-[ID]
- **Affected**: [product] [versions]
- **PoC**: [URL or "not public"]
- **Patch**: [URL]
- **CISA KEV**: Yes/No
- **Exploited ITW**: Yes/No — [source]
- **Red team notes**: [access conditions, chaining potential]

## Attack Chain
[Phase → Technique T[ID] → CVE → method]

## Mitigations and Detection
[Patch, config, SIEM rule per phase]

## Sources
[1] URL — source — date
```

---

## CVE Deep Dive Workflow

For single-CVE research, run steps 1–3 in parallel, then follow links:

**Step 1 — NVD data**: Jina Reader on `https://nvd.nist.gov/vuln/detail/CVE-YYYY-NNNNN` → save to `pages/001_nvd.md`

**Step 2 — PoC search** (3 parallel queries):
- GitHub: `"CVE-YYYY-NNNNN" exploit PoC` (include_domains: github.com)
- Exploit DBs: `CVE-YYYY-NNNNN exploit` (sploitus.com, packetstormsecurity.com)
- ITW: `CVE-YYYY-NNNNN exploited ransomware APT` (topic: news)

**Step 3 — ExploitDB** (JS-rendered, requires Playwright):
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

**Step 4 — Deep fetch each found URL** → save each PoC repo, advisory, writeup to `pages/`.

**Step 5 — CISA KEV + vendor advisory** (parallel): fetch and save both.

**Step 6 — Recursive**: follow links from saved pages (related CVEs, vendor patches, blog writeups).

**Step 7 — Synthesize**: read all pages/ files → build `output.md` section by section.

---

## Target Reconnaissance Workflow

Run all queries in parallel:
```
query 1: [product] [version] vulnerability 2025
query 2: [product] CVE critical (include_domains: nvd.nist.gov, cve.mitre.org)
query 3: [product] exploit PoC (include_domains: github.com, sploitus.com)
query 4: [product] security advisory (include_domains: [vendor.com], time_range: year)
```

Save each result page → follow links → synthesize.

---

## Social Media Intelligence

Twitter and Telegram are real-time sources for PoC drops, 0-day disclosures, and threat actor activity.

**Twitter** (xcancel — zero-auth, Playwright):
```
https://xcancel.com/search?f=tweets&q=CVE-YYYY-NNNNN+PoC&e-nativeretweets=on&e-replies=on&since=2024-01-01&min_faves=2
```

**FxTwitter API** (zero-auth JSON for full post content):
```
fetch_webpage → https://api.fxtwitter.com/status/{POST_ID}
```

**Telegram** (zero-auth JSON):
```
fetch_webpage → https://tg.i-c-a.su/json/{channel}
```

Curated channels: @cveNotify, @learnexploit, @news4hack, @vxunderground — full list in [references/sources.md](references/sources.md).

For detailed recipes, parameters, and Playwright scripts → [references/mcp-tools.md](references/mcp-tools.md).

---

## Operational Notes

- **Traffic**: Jina Reader and Playwright generate real HTTP traffic. On live engagements, use only Tavily (cached results) to avoid direct target contact.
- **Score filtering**: discard Tavily results with `score < 0.5` before deep-fetching.
- **Recency**: Tavily may lag for fresh CVEs — verify CVSS/KEV directly from NVD and CISA.
- **Jina Reader** handles most pages but may fail on heavy JS SPAs → escalate to Playwright.

## References

- [references/mcp-tools.md](references/mcp-tools.md) — full parameter reference for Jina, Tavily, Playwright, xcancel, FxTwitter, Telegram with verified recipes
- [references/sources.md](references/sources.md) — curated offensive security sources with domain lists
- [references/attack-chain-templates.md](references/attack-chain-templates.md) — ATT&CK-aligned attack chain templates
