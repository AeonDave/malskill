---
name: readme-md-creator
description: "Create, audit, or update a README for a repository, package, or document folder. Use when readers need accurate orientation, usage, or navigation."
license: MIT
compatibility: "Markdown; adapt features to the destination renderer"
metadata:
  author: AeonDave
  version: "1.2"
---

# README MD Creator

Create or update `README.md` files that help a new reader answer three questions fast:

1. What is this project, package, or collection?
2. How do I use or navigate it?
3. Where do I go next?

Optimize for scannability, correctness, and restraint.

## Workflow

### 1. Inspect the actual subject before drafting

Before writing anything:

- Read the relevant existing `README.md` if it exists.
- Inspect the actual project, package, or folder and its relevant entry points, manifests, scripts, or documents.
- Identify the likely primary audience: user, developer, contributor, operator, or mixed.
- Identify the publication destination, renderer, and language from the request and project conventions; adapt presentation to the reader and host.
- Extract only verified commands, paths, technologies, and links.
- For a document collection, explain its purpose, contents, and reading path; include installation or execution only when applicable and verified.
- If important details already live in dedicated files such as `docs/`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, or `CHANGELOG.md`, link to them instead of duplicating them.

Do not invent commands, features, badges, architecture, deployment targets, or screenshots.

### 2. Update or refine an existing README

When the target already has a `README.md`, treat the existing content as the starting point:

- Preserve any verified content that is already clear and useful.
- Improve structure, wording, or order before replacing entire sections.
- Remove duplication, stale instructions, and generic filler.
- Keep stable anchors and familiar section names when possible unless the current structure is actively harmful.
- Delete sections that duplicate dedicated files (`CONTRIBUTING.md`, `LICENSE`, `CHANGELOG.md`).
- If the existing README is mostly good, make targeted fixes instead of a full rewrite.

Skip this step when creating a README from scratch.

### 3. Build the header first

A good header usually contains:

- project name
- optional logo or icon if present in the repo
- one-sentence description
- a small set of useful badges only if they carry signal
- optional quick navigation links if the README is long enough to justify them

Keep the header compact. The reader should reach the first meaningful content quickly.

### 4. Choose the smallest useful outline

Use only the sections that help the reader act. Prefer the smallest useful set; section count is a result, not a quota.

High-value sections, in typical order:

1. Header (title + summary + optional badges)
2. Overview or Why
3. Features
4. Architecture or Project structure
5. Getting started / Installation
6. Usage
7. Configuration or Troubleshooting
8. Related docs / Resources

Omit sections that add noise. Do not add `LICENSE`, `CONTRIBUTING`, `CHANGELOG`, or similar sections when dedicated files already exist; link to them only when useful.

If the README is getting long, trim it and push detail into dedicated docs.

### 5. Write for scanning, not for applause

Write in the requested language or the project's established language. Keep sections short, headings descriptive, content specific, and presentation visually coherent with the project.

Prefer:

- short opening paragraph
- bullets for features, prerequisites, and choices
- numbered steps for setup flows
- small code blocks only for copy-paste-ready commands
- relative links for local files when supported by the destination

Avoid:

- long walls of prose
- repeating the same value proposition in the header, overview, and features
- giant badge farms, marketing filler, and to-do dumps
- changelog entries and exhaustive inventories of features, files, or commands

Write features as concrete outcomes, not technology lists:

- Good: "Proxy unmatched requests to a live backend"
- Bad: "Built with TypeScript and uses modern architecture"

Write getting-started steps as imperative copy-paste commands:

- Good: `npm install && npm start`
- Bad: "You can install the project by running the install command"

### 6. Structure by project type

Tailor the README to its subject.

#### Libraries and SDKs

Prioritize: what problem it solves, installation, smallest working example, common usage patterns, compatibility constraints.

#### CLIs and developer tools

Prioritize: purpose, install methods, command synopsis, common examples. Option references only if short; otherwise link elsewhere.

#### Apps and services

Prioritize: what the app does, architecture only if it helps understanding, prerequisites, local setup, how to run, configuration, troubleshooting.

#### Monorepos or sample collections

Prioritize: workspace purpose, high-level directory map, how to choose or run a package/sample, links to per-package docs.

#### Document folders

Prioritize: collection purpose and audience, how to select or read the key documents, and links to them.

### 7. Add diagrams only when justified

Add architecture only when the system has multiple meaningful parts, non-obvious flow, or integration boundaries that are easier to grasp visually.

Decision order:

1. No diagram if the architecture is trivial.
2. Choose a compact diagram or image that fits the destination and clarifies the flow. Use a text diagram when portability or plain-text reading matters; use renderer-supported diagrams or an accessible image when they communicate better.

ASCII diagrams must be narrow (~80–100 chars), focused on one flow, accompanied by a short explanation, and based on verified components.

Do not add decorative ASCII art or massive pseudo-enterprise diagrams.

If you need examples or decision rules, load [`./references/ascii-architecture.md`](./references/ascii-architecture.md).

### 8. Match the destination

Use Markdown supported by the target renderer. For GitHub Markdown files, a [Mermaid diagram](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams), useful screenshot or logo, and brief alerts can improve comprehension when relevant. For plain-text readers or other hosts, use portable syntax or a readable fallback. Check rendering and links in the intended destination when practical.

Allowed and useful: headings, bullets and numbered lists, fenced code blocks with language tags, relative links, tables only when they improve scanning.

For GitHub alerts / callouts:

- use at most one or two in a README
- use them only for critical setup constraints, risks, or important alternatives
- do not stack alerts back-to-back or nest them

### 9. Validate against reader intent

Before finishing, check:

- Does the first screen explain the subject and its purpose?
- Can a new reader find the fastest path to use or navigate it?
- Are all commands, filenames, and paths real?
- Is each section distinct and non-redundant?
- Is the README still reasonably short for the project size?
- Are there any sections better replaced by a link?
- Is the language clear, direct, and appropriate for the audience?
- If architecture is included, does it materially help understanding?
- If this was an update, did you preserve the useful parts and improve the weak parts instead of blindly rewriting everything?

## Drafting Rules

- Prefer one clear sentence over two clever ones.
- Mention environment variables only when actually required.
- If configuration is extensive, show the minimum and link to deeper docs.
- If multiple workflows exist, present the recommended one first.
- If Windows, macOS, and Linux differ, separate the differences cleanly.
- Use alt text for images.
- Avoid emojis unless the repository tone clearly supports them; even then, keep usage sparse.

## Resources

### references/

- [`./references/section-patterns.md`](./references/section-patterns.md) — section selection rules and compact README patterns by project type.
- [`./references/ascii-architecture.md`](./references/ascii-architecture.md) — when to include ASCII architecture, when not to, and compact diagram patterns.

### assets/

- `assets/readme-template.md` — lean starter template for a new `README.md`; replace every placeholder with repo-specific facts before saving.
