# Zero Day Hunter Workflow

## When to use this skill

Use this skill when the user wants a **local source-code hunting workflow** for likely zero-day candidates rather than a classic signature scanner.

Best fits:

- parser-heavy C or C++ projects
- services that ingest attacker-controlled files or packets
- repositories where manual review needs a faster shortlist
- code audit sessions that need structured Markdown and JSON outputs

Before file-by-file review, consider a short external context step for projects whose security logic may be hidden in framework wiring, middleware, decorators, route registration, or product-specific architecture docs.

## Context enrichment strategy

Use Tavily only to gather a **small context pack**, not to make vulnerability claims.

Good uses:

- clarify what the project or component does
- identify likely trust boundaries
- understand framework-level auth or routing patterns
- find public docs or advisories that explain intended behavior

Bad uses:

- treating a public article as proof of a local bug
- stuffing prompts with many similar search results
- replacing local grep, call tracing, or source inspection

If external context is needed, build it first, then pass it into the main scanner as additional context.

## Triage discipline

A candidate is interesting when all three are plausible:

1. **Bug reality** — the bug pattern appears to exist in code, not only in theory
2. **Reachability** — untrusted input can plausibly exercise it
3. **Security impact** — crash, corruption, privilege abuse, auth bypass, injection, or data exposure is realistic

If one of those is weak, label the finding accordingly.

## File selection strategy

Start with likely hot files:

- protocol parsers
- request handlers
- decompression or archive readers
- image, media, and document parsers
- authn/authz gates
- plugin or extension loaders
- bridge layers between safe and unsafe code

Deprioritize large generated sources, vendor trees, fixtures, and examples unless the user explicitly wants them scanned.

## Review checklist

For each candidate, verify:

- the exact variable or field that carries attacker input
- the buffer, allocation, or sink that receives it
- the concrete bound or guard, if any
- whether the guard is sufficient for the actual destination size
- whether callers sanitize the value before it arrives
- whether the code path is externally reachable

## Confidence guidance

Use higher confidence only when:

- the sink is explicit
- the source is named
- the guard was checked locally
- the impact is concrete
- any external context aligns with the local code rather than substituting for it

Reduce confidence when:

- a defense might exist but is not verified
- the path depends on unclear callers
- the issue is cross-file and only partially visible
- the model output is ambiguous or malformed

## Output hygiene

Prefer short, evidence-first writeups:

- one paragraph on why the issue matters
- one paragraph on the exact evidence checked
- one paragraph on what remains unverified

Do not oversell. The user needs a trustworthy shortlist, not marketing.
