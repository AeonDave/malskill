# External Context Enrichment

Use this reference when the agent needs to improve local code review with a small amount of **external project context** before scanning.

## Why enrich context first

LLM-based review is strongest when the bug and the defense are visible in one file or one small region. It becomes noisier when:

- authorization logic lives in middleware or decorators
- protections are implemented in framework glue
- the codebase depends on project-specific conventions
- the target repo uses uncommon architecture or generated routing

A short external context pack helps the agent ask better questions before local review starts.

## What to ask Tavily for

Keep the search narrow. Good targets:

- project or product name plus framework
- repository name plus protocol or file format handled
- recent advisories or security notes for the target project
- architecture clues from public docs, README files, or vendor pages

Good examples:

- `project-name architecture auth middleware`
- `project-name parser protocol format`
- `project-name security advisory authorization`
- `framework-name middleware access control patterns`

## What to keep

Prefer the top 3 to 5 results that answer one of these questions:

1. What does the project or component do?
2. Which trust boundaries are likely relevant?
3. Which framework or middleware layers may hide important checks?
4. Are there public docs that describe access control, parsing, or deployment assumptions?

Keep:

- title
- URL
- one short reason the source matters
- one short excerpt or summary

## What not to do

- Do not treat public writeups as proof that the local code is vulnerable.
- Do not replace local grep or source review with web snippets.
- Do not overload prompts with ten nearly identical search results.
- Do not overfit to one advisory when scanning unrelated code.

## How to use the context pack

Use the external context to:

- bias attention toward likely entry points and hidden security layers
- improve prompts for framework-specific checks
- reduce false positives caused by missing project intent
- generate better local grep queries

Then verify every claim against local source code.

## Confidence rules

External context can raise confidence only when it improves a local hypothesis. It must never be the sole reason a finding is reported.
