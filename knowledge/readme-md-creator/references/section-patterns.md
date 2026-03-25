# Section Patterns for README.md

Use these patterns to keep README scope tight.

## Selection rules

Choose sections based on what the reader must do next.

Include a section only if at least one is true:

- it helps a new reader understand the project quickly
- it enables setup, usage, debugging, or navigation
- it prevents a likely mistake
- it links to deeper docs without duplicating them

Exclude or replace a section when:

- the content belongs in dedicated docs
- the section repeats information already stated clearly
- the section exists only because "README templates usually have it"

## Compact defaults by project type

### Library

Recommended order:

1. Title + summary
2. Why this exists
3. Installation
4. Minimal example
5. Common usage
6. Compatibility / constraints
7. More docs

### CLI tool

Recommended order:

1. Title + summary
2. What it does
3. Installation
4. Quick examples
5. Command syntax or key options
6. Troubleshooting
7. More docs

### Application or service

Recommended order:

1. Title + summary
2. Overview
3. Features
4. Architecture or structure
5. Prerequisites
6. Getting started
7. Usage
8. Configuration
9. Troubleshooting / docs

### Monorepo or sample collection

Recommended order:

1. Title + summary
2. What is in this repository
3. Workspace map
4. How to get started
5. How to choose a package or sample
6. Links to package-level docs

## Header patterns

A header can include:

- project name
- one-sentence description
- optional logo/icon
- 0–5 high-signal badges
- optional jump links when the README is long

Avoid:

- badge overload
- multiple slogans
- large intro paragraphs before any practical information

## Feature section rules

Write features as outcomes, not technologies.

Prefer:

- "Run local checks before deployment"
- "Proxy unmatched requests to a live backend"

Avoid:

- "Built with TypeScript"
- "Uses modern architecture"

Technology belongs in overview, architecture, or prerequisites only when it helps the reader.

## Getting started rules

- Put the happy path first.
- Use numbered steps.
- Make commands copy-paste-ready.
- Separate prerequisites from steps.
- If several setup methods exist, label the recommended one.
- If the long form is needed, keep the quickstart short and link out.

## Usage rules

- Start with the smallest useful example.
- Follow with 2–5 common examples.
- Group advanced or edge-case examples under subheadings.
- Keep examples real and consistent with the actual interface.

## Tables

Use tables only when they improve comparison or scanning, for example:

- sample lists
- supported platforms
- configuration matrices
- short option summaries

Do not use tables for long prose.

## Anti-patterns

- repeating overview text in features
- documenting every folder in the repo
- pasting every CLI option into the README when `--help` or docs already exist
- putting contributor process in the middle of user setup
- burying the quickstart below large marketing text
