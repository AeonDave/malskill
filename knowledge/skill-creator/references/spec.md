# AgentSkills Specification Reference

Quick reference for the SKILL.md format. Source: https://agentskills.io/specification

## Frontmatter Fields

| Field | Required | Rules |
|---|---|---|
| `name` | Yes | 1–64 chars; lowercase letters, digits, hyphens only; no leading/trailing/consecutive hyphens; must match folder name |
| `description` | Yes | 1–1024 chars; describes what the skill does and when to use it; no angle brackets |
| `license` | No | License name or path to a bundled license file |
| `compatibility` | No | 1–500 chars; environment requirements (OS, packages, network) |
| `metadata` | No | Arbitrary string key-value map for extra properties |
| `allowed-tools` | No | Space-delimited list of pre-approved tools (experimental) |

No other fields are permitted in frontmatter.

## Name Rules

```
Valid:   pdf-processing, data-analysis, code-review, gh-address-comments
Invalid: PDF-Processing  (uppercase)
         -pdf            (leading hyphen)
         pdf--processing (consecutive hyphens)
         pdf_processing  (underscores not allowed)
```

## Description Rules

- Must cover both *what* the skill does and *when* to activate it
- Use specific keywords: task names, file extensions, activation phrases
- Keep it under 1 024 characters
- Single-line or block scalar (`>`) both valid

```yaml
# Good
description: "Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction."

# Poor
description: "Helps with PDFs."
```

## Optional Fields Examples

```yaml
---
name: pdf-processing
description: "Extract text, fill forms, merge and split PDF files. Use when the user asks about PDFs, forms, or document conversion."
license: Apache-2.0
compatibility: Requires Python 3.10+, pdfplumber, pypdf
metadata:
  author: example-org
  version: "1.2"
allowed-tools: Bash(python:*) Read
---
```

## Progressive Disclosure

```
Stage 1 — Startup:   name + description (~100 tokens, always loaded)
Stage 2 — Trigger:   Full SKILL.md body  (< 5 000 tokens recommended)
Stage 3 — On demand: scripts/, references/, assets/ (unlimited, loaded when needed)
```

Keep `SKILL.md` under **500 lines**. Reference files are loaded individually, so keep each focused.

## File Reference Syntax

Use relative paths from the skill root inside SKILL.md:

```markdown
See [references/REFERENCE.md](references/REFERENCE.md) for details.
Run the extraction script: `scripts/extract.py`
```

Keep references one level deep. Avoid chains (A → B → C).

## Validation

```bash
# Official CLI
skills-ref validate ./my-skill

# This skill's built-in validator
python scripts/quick_validate.py ./my-skill
```

## Packaging

The `.skill` file is a standard zip archive with a `.skill` extension. The folder structure inside the zip preserves the skill directory name.

```
my-skill.skill (zip)
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    └── references/
```
