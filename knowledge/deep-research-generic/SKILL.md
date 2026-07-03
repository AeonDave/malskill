---
name: deep-research-generic
description: "File-backed deep research with recursive link-following, multi-tool web fetching, and step-by-step synthesis. Use when the user asks to research, investigate, analyze, or summarize a topic in depth; when a thorough answer requires gathering and cross-referencing multiple sources; or when output must be comprehensive, cited, and not limited by context window size. For CVE/exploit/threat-intel research → use deep-research-offensive."
license: MIT
metadata:
  author: AeonDave
  version: "2.0"
---

# Deep Research — Generic

File-backed, multi-pass research workflow. Each useful page is fetched, cleaned, and saved to an intermediate file. Linked pages are recursively followed. All intermediate files are synthesized step-by-step into a single comprehensive research document.

> **Core principle**: Use the file system as extended memory. Never rely on context alone — save everything worth keeping, then synthesize from files.

---

## Methodology

### Step 1 — Scope & Plan

Before any search:

1. Define the exact research question or thesis
2. Break into 3–7 sub-questions (dimensions), each with a priority (high/medium/low)
3. Create the working directory:

```
.research/{topic-slug}/
├── _plan.md            # Sub-questions, priorities, URL queue, gap tracker
├── pages/              # One .md file per fetched page
└── output.md           # Final synthesized research document
```

4. Write `_plan.md` with sub-questions and an empty URL queue section

Ask at most two clarifying questions. If the request is clear, proceed immediately.

### Step 2 — Initial Search Sweep

For each sub-question, run parallel searches to discover URLs:

- **`web_search`** (primary): one query per sub-question; multi-provider, synthesized results with citations
- **Jina Search** (complementary): `fetch_content` on `https://s.jina.ai/{search-query}`
- **Tavily** (if MCP-available): `search_depth: basic`, `max_results: 5–10`

From results:
- Record every promising URL in `_plan.md` under the URL queue
- Note: source, relevance score, which sub-question it serves
- Filter: only queue URLs with relevance score > 0.5 (or clearly relevant titles)

### Step 3 — Deep Fetch (page by page)

Process each queued URL individually:

**3a. Fetch** using the tool hierarchy (stop at first success):

| Priority | Tool | When |
|---|---|---|
| 1 | **`fetch_content`** (Jina proxy) | `https://r.jina.ai/{url}` — strips boilerplate, cleanest markdown |
| 2 | **`fetch_content`** (direct) | APIs, raw JSON, PDFs, GitHub repos |
| 3 | **Tavily extract** | MCP-available; structured extraction |
| 4 | **Playwright** | JS-rendered SPAs, dynamic tables |

**Jina proxy**: `fetch_content` on `https://r.jina.ai/{full-url-with-scheme}`
Converts any page to clean markdown. Strips ads, nav, popups. Falls back to Gemini for bot-blocked pages.

**Escalation**: Jina proxy empty → `fetch_content` direct → Tavily extract → Playwright.

**3b. Evaluate**: Is the content relevant and citable? If not, mark URL as `skipped` in `_plan.md` and move on.

**3c. Save** to intermediate file `pages/{NNN}_{slug}.md`:

```markdown
# {Page Title}

- **Source**: {URL}
- **Fetched**: {date}
- **Serves**: {sub-question name}
- **Relevance**: high/medium/low

## Content

{Cleaned content: facts, data, quotes, code, citations.
Remove navigation, ads, boilerplate. Summarize verbose sections
but preserve all critical detail and data points.}

## Outbound Links

- {URL1} — {why it might be useful}
- {URL2} — {why it might be useful}
```

**3d. Extract links**: Identify all outbound links that could deepen the research. Add relevant new URLs to the queue in `_plan.md`.

### Step 4 — Recursive Link Discovery

Repeat Step 3 for newly queued links. Stop when:
- No new relevant links found
- Maximum depth reached (default: 3 levels from initial results)
- Diminishing returns — new pages repeat known information

Update `_plan.md` queue: mark each URL as `fetched`, `skipped`, or `queued`.

### Step 5 — Gap Analysis

After all fetch rounds:

1. Review each sub-question against the intermediate files
2. List which files provide evidence for each sub-question
3. Identify gaps: sub-questions with no or weak coverage
4. For critical gaps → run targeted searches (back to Step 2) for those gaps only
5. Update `_plan.md` with gap analysis

### Step 6 — Step-by-Step Synthesis

Build `output.md` incrementally from intermediate files:

1. **Process one dimension at a time** — do not load all files at once
2. For each dimension:
   a. Read the relevant intermediate files for that dimension
   b. Write the analysis section into `output.md` with inline citations `[N]`
   c. Move to the next dimension
3. After all dimensions:
   a. Write the executive summary (from the completed analysis)
   b. Write consensus and conflicts sections
   c. Compile the numbered sources list
   d. List gaps and follow-up questions

> **Key**: Each section reads only its relevant files. The research depth is limited only by the data found, not by context window size.

### Step 7 — Final Output

Structure of `output.md`:

```markdown
## Executive Summary
[2–3 sentences. Key conclusions + overall confidence.]

## Key Findings
- **{Finding}**: {1 sentence} — Confidence: High/Medium/Low [N]

## Detailed Analysis

### {Dimension 1}
{Analysis with inline citations [1][2].}

### {Dimension 2}
...

## Consensus
[What sources agree on.]

## Conflicts and Uncertainty
[Where sources disagree or data is missing.]

## Sources
[1] Author/Org, "Title", URL — date — Tier N
[2] ...

## Gaps and Follow-up Questions
[What this research does NOT answer.]
```

Present `output.md` to the user. Intermediate files remain available for follow-up.

---

## Fetch Tool Details

### fetch_content (primary — always available)

```
Jina proxy:  fetch_content(url="https://r.jina.ai/{target-url-with-scheme}")
Direct:      fetch_content(url="{target-url}")
```

Handles URLs, GitHub repos, PDFs (text extraction), and YouTube transcripts. Jina proxy strips boilerplate, returns clean markdown. Direct mode for APIs, raw text, and documents. Gemini fallback activates automatically for bot-blocked pages.

### web_search (primary search — always available)

Multi-provider search (OpenAI, Brave, Perplexity, Exa, Tavily, Gemini). Returns synthesized answer with source citations.

```python
web_search(queries=["sub-question 1", "sub-question 2"])  # parallel
web_search(query="...", recencyFilter="month")             # time-bounded
```

Use `numResults=10` for broad sweeps. Post-filter URLs for relevance before deep-fetching.

### Tavily (when MCP available)

| Tool | Use |
|---|---|
| `tavily_search` | Keyword search; `search_depth: basic/advanced/ultra-fast` |
| `tavily_extract` | Content extraction from known URLs |
| `tavily_crawl` | Multi-page crawl (expensive — use last) |
| `tavily_map` | Enumerate URLs before crawling |

Query rules: max 400 chars, one topic per query, `include_domains` instead of `site:`, `score > 0.5` filter. Use `search_depth: advanced` + `chunks_per_source: 3` for precise fact retrieval.

### Playwright (fallback for JS-heavy pages)

Use when fetch_content and Tavily return empty or incomplete content:
- JavaScript-rendered SPAs and dynamic tables
- Content requiring browser-level JS execution

---

## Source Credibility Tiers

| Tier | Examples | Credibility |
|---|---|---|
| 1 | Peer-reviewed journals, official statistics | High |
| 2 | Government/NGO reports, industry standards | High |
| 3 | Reputable news outlets, expert commentary | Medium |
| 4 | Blogs, forums, unverified claims | Low — verify independently |


---

## Quality Rules

- Every factual claim needs a citation with source URL
- Never fabricate a source — if unavailable, state "not found"
- Distinguish "no evidence" from "evidence of absence"
- Flag information older than 2 years as potentially outdated
- Respect robots.txt on public-domain research; record the fetch method used per page
