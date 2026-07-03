---
name: known-problem-hint-research
description: "Targeted post-triage online research for a known technical problem signature, not broad discovery. Use after the agent has already analyzed the artifact, ranked hypotheses, and hit a wall, to find the missing hint in papers, blogs, articles, public writeups, source discussions, specifications, commits, issues, changelogs, advisories, PoCs, or implementation notes. Useful for cryptography, protocol debugging, reversing, AI/ML behavior, web/API behavior, exploit constraints, version-specific bugs, build/runtime errors, and standards mismatches where one external clue unlocks the next local test."
license: MIT
compatibility: "AgentSkills-compatible agents with web search/fetch access; uses fetch_content, Tavily when available, and Jina Reader/Search endpoints."
metadata:
  author: AeonDave
  version: "1.0"
---

# Known Problem Hint Research

Goal: find the **one missing external hint** for a problem the agent has already triaged locally.

This is not broad deep research. It is a narrow, evidence-led spike: paper, blog, article, public writeup, issue, or source discussion that gives the next concrete local test.

## Activation gate

Use this skill only after local work has produced a specific problem signature:

- artifact, primitive, or subsystem is identified
- constraints and observable symptoms are known
- at least two plausible local hypotheses were tested or rejected
- a success oracle is defined: recovered key, plaintext, proof, exploit condition, decoded output, or reproduced behavior

Do not use it at the beginning of a task, for generic learning, or to search a whole topic. If the problem is not fingerprinted yet, return to local triage or the relevant domain methodology first.

## Input bundle to prepare

Before searching, write a compact fingerprint:

```text
Problem shape: crypto primitive / parser / protocol / model / binary / API / build error / runtime behavior / vulnerability class / spec mismatch
Observed anomaly: exact structural clue, error, equation, parameter relation, or trace
Known constraints: sizes, versions, bounds, or oracle behavior
Local attempts: what was tried and why it failed
Success oracle: what would prove the hint works
Forbidden broad terms: generic topic words to avoid
```

The fingerprint is the guardrail that keeps the search sharp.

## Search ladder

### 1. Generate 3 to 5 precise queries

Derive queries from the fingerprint, not from the whole user prompt.

Good query ingredients:

- exact attack family or suspected theorem
- distinctive parameter relationship
- short error message or implementation phrase
- source-type term such as `paper`, `implementation`, `issue`, `commit`, `patch`, `spec`, `writeup`, `blog`, or `discussion`

Bad query ingredients:

- broad category names alone
- full task titles or project branding without the technical clue
- vague phrases like `how to solve crypto problem`
- every parameter pasted blindly into search

### 2. Discover candidate URLs

Use available discovery tools in this order:

1. Tavily search/research when available, with one narrow query at a time.
2. Jina Search through `fetch_content` on `https://s.jina.ai/{url-encoded-query}`, preferably with a site filter from `references/source-filters.md`.
3. Direct site-native search or normal web search only for gaps or when the above fail.

Do not accept Tavily's synthesis as final evidence. Treat it as URL discovery and claim triage, then fetch primary pages.

### 3. Fetch only promising pages

For each candidate URL, use the smallest reliable fetch path:

1. Jina Reader: `fetch_content` on `https://r.jina.ai/{full-url-with-scheme}`.
2. Direct `fetch_content` for raw text, JSON, PDFs, API pages, or simple sites.
3. Tavily extraction when available and the page needs structured extraction.
4. Browser automation only if the source is highly relevant and other fetches fail.

Stop after 5 to 8 high-signal pages unless a page cites a clearly decisive source.

### 4. One-hop recursion only

Follow outbound links only when they are directly relevant:

- paper cited by a blog
- code repo linked by a writeup
- discussion explaining a parameter condition
- original advisory, spec, or implementation note

Do not crawl a site. This skill is a spear, not a fishing net.

## Source priority

Prefer sources in this order:

1. Peer-reviewed or preprint papers with exact theorem/attack match
2. Original implementation, upstream issue, commit, or documentation
3. Detailed technical blog/article with reproducible method
4. Public solution notes or lab writeups that explain the transferable trick without unsupported hand-waving
5. Forum/Q&A discussion with concrete equations, code, or citations

Source age matters less than applicability for old math, but version-specific implementation behavior must be current.

## Hint packet output

Return a short packet, not a literature review:

```markdown
## Hint packet

- **Likely missing idea**: one sentence
- **Why it fits**: map source clue to local fingerprint
- **Source trail**: 2-5 URLs with source type and confidence
- **Next local test**: exact experiment, script, equation, or command to try
- **Stop condition**: what result confirms or kills this hint
- **What not to chase**: sources/ideas that looked similar but do not fit
```

If no strong source appears, say so and return to local triage. Do not keep searching just because the wall is annoying.

## Quality rules

- Every proposed hint must cite at least one fetched source URL.
- Separate "source says" from "agent infers".
- Do not outsource reasoning: use external material to choose the next local test, then validate locally.
- Prefer technical fingerprints over exact task titles to avoid spoiler-only searches.
- If a public writeup is used, extract the transferable technique, not site-specific narrative.
- Do not claim a known solution until the local success oracle passes.

## Domain add-ons

Load `references/source-filters.md` when the next question is **where** to search: papers, standards, issue trackers, source-code discussions, security blogs, Q&A, or public writeups.

Load `references/exploit-hint-recipes.md` when the fingerprint is exploit- or vulnerability-shaped and version matters: affected product/version, fixed release, changelog, public patch diff, advisory, bug description, PoC, or reproduction constraint.

Load `references/crypto-query-recipes.md` only when the fingerprint is cryptographic or math-heavy and the local primitive is already classified, such as:

- suspicious RSA parameter relation but no selected attack
- ECC nonce/curve/order clue that resembles a named paper
- PRNG outputs that look like a known truncated-state recovery pattern
- lattice/Coppersmith setup that needs the right bound or construction
- oracle behavior that matches a known padding/timing/signature case

## Resources

- `references/source-filters.md` — targeted source families, site filters, and Jina/Tavily usage patterns for known-problem hint hunting.
- `references/exploit-hint-recipes.md` — version-first exploit hint workflow covering changelogs, public diffs, advisories, PoCs, and reproduction constraints.
- `references/crypto-query-recipes.md` — targeted query templates and source filters for crypto/math-heavy hint hunting.
