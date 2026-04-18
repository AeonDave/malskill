---
name: zero-day-hunter
description: "LLM-assisted workflow for hunting likely zero-day candidates in source code repositories. Use when asked to scan a file or repo for externally reachable vulnerabilities, prioritize suspicious files, generate per-file security context, and skeptically review candidate findings with local code search. Best suited for C and C++ projects but also useful for Go, Rust, Python, Java, JavaScript, TypeScript, PHP, and C#. Includes Python helpers for file discovery, scan orchestration, evidence gathering, and Markdown/JSON result output."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Zero Day Hunter

Use this skill to produce a practical shortlist of **zero-day candidates** in a local codebase. The goal is to help the user prioritize manual review, not to claim a vulnerability is real without verification.

Use a short external context pass before scanning when local code alone is likely to hide important assumptions behind middleware, framework glue, deployment architecture, or project-specific conventions.

## Safety and expectations

- Treat every result as a **candidate**, not a confirmed zero-day.
- Prefer findings that are reachable from untrusted input and have plausible security impact.
- Be skeptical of internal-only helpers, debug-only code, test fixtures, and theoretical edge cases.
- When a defense is mentioned, verify it with local code search instead of assuming it works.

## Recommended workflow

### 1. Scope the target

Start with the smallest useful scope:

- a single file when the user already suspects a component
- a subdirectory when the project is large
- the repository root only when broad hunting is explicitly requested

Prioritize code that parses attacker-controlled input, implements protocol handlers, deserializers, authentication logic, file format parsing, archive handling, crypto glue, or memory-unsafe interfaces.

### 2. Enrich project context first when needed

Use Tavily-backed context enrichment before scanning when any of these are true:

- the project uses a web framework with implicit middleware or decorators
- authorization or routing is likely spread across multiple files
- the code handles a niche protocol, parser, archive, or plugin ecosystem
- the repository name or product docs can clarify intended behavior

Use `scripts/build_external_context.py` to create a small Markdown or JSON context pack from public sources. Keep only the top few relevant results and treat them as hypothesis fuel, not proof.

### 3. Run the scanner

Use `scripts/scan_zero_day.py` for the first pass.

Suggested behavior:

- scan only source-like files
- skip binary or oversized files
- produce a context summary before vulnerability hunting
- inject external context when it clarifies framework behavior or trust boundaries
- request structured findings in JSON
- optionally run a skeptical review pass with grep-backed evidence

If API credentials are missing, load them from environment variables or the workspace `.env` file.

Use `--external-context-file` when a Tavily-generated context pack is available.

### 4. Review survivors

Promote a finding only if the evidence shows all of the following:

- the bug pattern is concretely present
- attacker-controlled input can reach it
- impact is meaningful
- no verified defense blocks exploitation

Use `scripts/source_grep.py` to resolve constants, call paths, bounds checks, or type validation logic during review.

### 5. Report cleanly

For each survivor, report:

- file path
- candidate title and severity
- vulnerable function or code region
- why it looks reachable
- what evidence was checked locally
- what still needs manual confirmation

Keep the output honest. "Likely", "plausible", and "needs manual verification" are features, not bugs.

## Heuristics that usually pay off

Prioritize these classes first:

- unchecked copies into fixed buffers
- integer overflow or sign confusion feeding lengths or allocations
- null dereference reachable from malformed input in parser or request paths
- type confusion on tagged unions or variant-like objects
- path traversal and archive extraction trust issues
- unsafe deserialization or dynamic code loading
- authorization gaps on externally reachable handlers
- command injection or shell interpolation with user-controlled fields

Deprioritize:

- purely stylistic issues
- dead code with no caller path
- missing checks on internal-only invariants with strong callers
- race conditions without security impact
- generic “use after free maybe” claims without a plausible lifetime path

## Practical operating notes

- For very large repositories, scan a hot subset first and expand only when needed.
- C and C++ results generally benefit most from grep-backed review.
- For safer languages, bias toward trust-boundary bugs rather than memory corruption.
- If the model returns malformed JSON, salvage what is usable but mark confidence lower.
- If external context conflicts with local code, trust the local code and record the mismatch.
- Save both machine-readable and analyst-friendly output.

## Resources

### scripts/

- `scripts/build_external_context.py` — queries Tavily for a compact external context pack covering project purpose, likely trust boundaries, framework behavior, and public security clues.
- `scripts/scan_zero_day.py` — main scanner: discovers files, generates context, hunts candidates, optionally performs skeptical review, and writes Markdown/JSON output.
- `scripts/source_grep.py` — lightweight literal or regex code search helper for verifying constants, callers, checks, and data-flow clues.

### references/

- `references/workflow.md` — deeper workflow for target selection, triage discipline, and output interpretation.
- `references/bug-classes.md` — quick bug-class guide and false-positive filters by language and code pattern.
- `references/context-enrichment.md` — when and how to use Tavily-style external context without replacing local code review.
