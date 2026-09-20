---
name: deep-research-generic
description: "Research a question across primary sources. Use when competing claims or multiple subquestions need traceable evidence and a bounded research plan."
license: MIT
metadata:
  author: AeonDave
  version: "2.0"
---

# Deep Research — Generic

File-backed, multi-pass research workflow for investigations that need multiple sources or context beyond one response. Save useful pages and synthesize them step-by-step; for a small self-contained question, keep the notes and output proportionate.

> **Core principle**: Use the file system as extended memory when the research is multi-page or context-limited. Save material worth keeping and synthesize it from the recorded evidence.

---

## Methodology

### Step 1 — Scope & Plan

Before any search:

1. Define the exact research question or thesis
2. Break the question into the smallest useful set of sub-questions, each with a priority (high/medium/low)
3. For multi-page or context-limited work, create the working directory:

```
.research/{topic-slug}/
├── _plan.md            # Sub-questions, priorities, URL queue, gap tracker
├── pages/              # One .md file per fetched page
└── output.md           # Final synthesized research document
```

4. For that workflow, write `_plan.md` with sub-questions and an empty URL queue section.

Ask only the clarifying questions needed to resolve scope or a materially ambiguous requirement. If the request is clear, proceed immediately.

For a small self-contained question, use a direct cited response and skip the file-backed passes; use Steps 2–7 when multiple sources or context limits justify them.

### Step 2 — Initial Search Sweep

For each sub-question, run parallel searches to discover URLs:

- Use the available search provider(s), one focused query per sub-question where practical.
- Use Tavily only when its MCP tools are available; follow that tool's current schema and limits.
- Do not assume a provider, endpoint, score field, or synthesis behavior exists in the active host.

From results:
- Record every promising URL in `_plan.md` under the URL queue
- Note: source, relevance rationale (and a provider score only if available), and which sub-question it serves
- Filter by relevance and source quality; use a provider score only when that provider documents one.

### Step 3 — Deep Fetch (page by page)

Process each queued URL individually:

**3a. Fetch** using the tool hierarchy (stop at first success):

| Priority | Tool | When |
|---|---|---|
| 1 | An available direct page fetch | APIs, raw JSON, PDFs, and ordinary pages |
| 2 | An available extraction or reader tool | When it returns citable content more reliably |
| 3 | Browser automation | JS-rendered pages when other available fetches are incomplete |

Use a reader or extraction proxy only when it is available and its behavior is known. Do not claim that a proxy strips all boilerplate or that one provider automatically falls back to another.

**Escalation**: try the least expensive available fetch, then a direct or browser fetch when the result is empty or incomplete.

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
- A deliberately chosen depth or page budget is reached
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

### Fetching

```
Use the active host's page-fetch or extraction tool and record the method used.
```

Capabilities vary by host; verify URL, PDF, repository, and transcript support before relying on them.

### Search

Use the active host's search tool. Treat returned summaries and citations as leads until the linked source is fetched and checked.

Use the active search tool's documented query, result-count, and recency parameters; do not copy a signature from this skill into a host that exposes a different API.

### Tavily (when MCP available)

| Tool | Use |
|---|---|
| `tavily_search` | Keyword search; `search_depth: basic/advanced/ultra-fast` |
| `tavily_extract` | Content extraction from known URLs |
| `tavily_crawl` | Multi-page crawl (expensive — use last) |
| `tavily_map` | Enumerate URLs before crawling |

Follow Tavily's current documented parameter limits. Keep queries focused and use domain filters when supported; do not impose an undocumented score threshold.

### Playwright (fallback for JS-heavy pages)

Use browser automation when the available fetch or extraction tools return empty or incomplete content:
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
- Check age when the claim is time-sensitive; age alone does not invalidate stable facts.
- Respect robots.txt on public-domain research; record the fetch method used per page
