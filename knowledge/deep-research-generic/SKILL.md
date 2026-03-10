---
name: deep-research-generic
description: "Systematic multi-source research with citations, conflict analysis, and confidence scoring. Use when the user asks to research, investigate, analyze, or summarize a topic; when a thorough answer requires gathering and cross-referencing multiple sources; or when the output must include citations and a credibility assessment."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Deep Research — Generic

Systematic research workflow for any domain. Produces cited, structured analysis with explicit confidence levels.

## Process

Follow these steps in order. Skip only when a step is clearly inapplicable.

### 1. Clarify

Before searching, resolve ambiguity:
- What is the exact question or thesis?
- What depth and breadth are needed?
- What format does the requester expect?
- Are there constraints (date range, language, geography)?

Ask at most two clarifying questions at once. If the request is clear, proceed immediately.

### 2. Decompose

Break the topic into 3–7 sub-questions or dimensions. For each dimension:
- Name it explicitly
- State the key question it answers
- Estimate its priority (high / medium / low)

### 3. Source and Search

For each sub-question, gather evidence:
- Use available web search / retrieval tools
- Prefer primary sources: peer-reviewed papers, official reports, primary data
- Accept secondary sources (quality journalism, expert commentary) with explicit note
- Record URL, title, date, author/org for every source

**Source tiers (use in citations):**
| Tier | Examples | Default credibility |
|---|---|---|
| 1 | Peer-reviewed journals, official stats | High |
| 2 | Government/NGO reports, industry standards | High |
| 3 | Reputable news outlets, expert interviews | Medium |
| 4 | Blogs, forums, unverified claims | Low — verify independently |

### 4. Synthesize

After gathering:
- Identify patterns and recurring themes
- Note explicit consensus and explicit disagreement
- Assign a confidence level to each major finding: `High` / `Medium` / `Low`
- If sources contradict, state both positions and explain the conflict

### 5. Output

Use this structure (adapt sections as needed):

```
## Executive Summary
[2–3 sentences. Key conclusions + confidence.]

## Key Findings
- **[Finding]**: [1 sentence] — Confidence: High/Medium/Low [1]

## Detailed Analysis

### [Dimension 1]
[Analysis with inline citations.]

### [Dimension 2]
...

## Consensus
[What sources agree on.]

## Conflicts and Uncertainty
[Where sources disagree or data is missing. Be explicit.]

## Sources
[1] Author, "Title", Outlet, Date — Tier 1 / credibility note
[2] ...

## Gaps and Follow-up Questions
[What this research does NOT answer. Suggested next queries.]
```

## Web Search with MCP Tools

When web search tools are available, use these patterns:

### Tool selection
| Goal | Tool |
|---|---|
| Broad keyword search (any topic) | `mcp_io_github_tav_tavily_search` |
| Full page content from a known URL | `mcp_firecrawl_fir_firecrawl_scrape` |
| Structured data fields from a known URL | `mcp_firecrawl_fir_firecrawl_extract` |
| JS-rendered pages (empty results from scrape) | `mcp_microsoft_pla_browser_run_code` |

### Tavily query patterns

```
# Discovery sweep  \u2014 run all sub-questions in one parallel batch
search_depth: basic      # 1 credit; sufficient for general research
max_results: 5           # default; increase to 10 only for broad sweeps
topic: general           # default; use "news" for current events (adds published_date)
time_range: year         # restrict to recent content when recency matters
include_domains: [...]   # pin to authoritative sources (gov, edu, official org)

# Precise fact extraction  \u2014 when you need a specific data point
search_depth: advanced   # 2 credits; returns ranked content chunks
chunks_per_source: 3     # include up to 3 chunks per result (advanced only)
max_results: 5
```

**Rules:**
- Max 400 chars per query; if over, split into two queries
- One topic per query; run independent sub-questions in **parallel** (not sequence)
- Use `include_domains` instead of `site:` inside the query string
- Filter results by `score > 0.7` before fetching full content
- For full page content: search → find URL → Firecrawl scrape (two-step, better than `include_raw_content: true`)

## Quality Rules

- Every factual claim must have a citation
- Never fabricate a source — if unavailable, say "not found"
- Distinguish between "no evidence" and "evidence of absence"
- Flag information older than 2 years as potentially outdated
- Do not editorialize; present analysis, not advocacy

## Depth Levels

Adjust based on user intent:

| Level | Description | Length |
|---|---|---|
| Quick | 3–5 findings, minimal detail | 300–500 words |
| Standard | Full workflow above | 800–1500 words |
| Deep | Multiple rounds of search, sub-research per dimension | 2000+ words |

Default to **Standard** unless the user specifies otherwise or the topic is trivial.
