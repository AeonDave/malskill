# Progressive Disclosure Patterns

Reference for structuring skills efficiently. Load this file when designing a skill's internal organization.

## Table of Contents

- [Pattern 1: High-level guide with references](#pattern-1-high-level-guide-with-references)
- [Pattern 2: Domain-specific organization](#pattern-2-domain-specific-organization)
- [Pattern 3: Multi-variant organization](#pattern-3-multi-variant-organization)
- [Pattern 4: Conditional details](#pattern-4-conditional-details)
- [Anti-patterns to avoid](#anti-patterns)

---

## Pattern 1: High-level guide with references

Use when the skill body would exceed 500 lines without splitting, or when some features are rarely needed.

```markdown
# PDF Processing

## Quick Start

Extract text with pdfplumber:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = "\n".join(p.extract_text() for p in pdf.pages)
```

## Operations

- **Text extraction**: Use `scripts/extract_text.py`
- **Form filling**: See [references/forms.md](references/forms.md)
- **Merging/splitting**: See [references/merge_split.md](references/merge_split.md)
- **Image conversion**: `scripts/convert_to_images.py`
```

The agent loads `forms.md` or `merge_split.md` only when the user's request requires them.

---

## Pattern 2: Domain-specific organization

Use when a skill covers multiple unrelated sub-domains (e.g., a company data skill covering finance, sales, product).

```
company-data/
├── SKILL.md          (overview + navigation guide)
└── references/
    ├── finance.md    (revenue, billing, cost metrics)
    ├── sales.md      (opportunities, pipeline, CRM)
    ├── product.md    (API usage, feature flags)
    └── marketing.md  (campaigns, attribution)
```

`SKILL.md` explains which file covers which domain. The agent loads only the relevant file.

**SKILL.md navigation section:**

```markdown
## Data Domains

Load the reference file that matches the user's question:

| Domain | File | Topics |
|---|---|---|
| Finance | [references/finance.md](references/finance.md) | Revenue, billing, P&L |
| Sales | [references/sales.md](references/sales.md) | Pipeline, CRM, deals |
| Product | [references/product.md](references/product.md) | API usage, features |
| Marketing | [references/marketing.md](references/marketing.md) | Campaigns, attribution |
```

---

## Pattern 3: Multi-variant organization

Use when the skill supports multiple frameworks, providers, or platforms that require different instructions.

```
cloud-deploy/
├── SKILL.md          (workflow + provider selection logic)
└── references/
    ├── aws.md        (AWS-specific patterns)
    ├── gcp.md        (GCP-specific patterns)
    └── azure.md      (Azure-specific patterns)
```

**SKILL.md selection logic:**

```markdown
## Provider Selection

Identify the target cloud from the user's request or project config:
- AWS → read [references/aws.md](references/aws.md)
- GCP → read [references/gcp.md](references/gcp.md)
- Azure → read [references/azure.md](references/azure.md)

If unspecified, ask the user before proceeding.
```

---

## Pattern 4: Conditional details

Use when most users need the simple path and only some need advanced features.

```markdown
## Document Editing

For simple text edits, modify content in-place using `scripts/edit_docx.py`.

For advanced scenarios:
- **Tracked changes / redlines**: See [references/redlining.md](references/redlining.md)
- **OOXML internals**: See [references/ooxml.md](references/ooxml.md)
- **Form fields**: See [references/forms.md](references/forms.md)
```

---

## Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Everything in SKILL.md | Bloats context even when not needed | Split into reference files |
| Deeply nested references | Reference chains create loading ambiguity | Keep all references one level from SKILL.md |
| Duplicate content | Same content in SKILL.md and a reference file | Single source of truth — pick one location |
| Generic TODO placeholders left in | Skill is not ready to use | Resolve all TODOs before packaging |
| Long reference files without a TOC | Agent cannot preview scope | Add a TOC at the top of any file >100 lines |
| README.md and CHANGELOG.md in the skill | Irrelevant to agent execution | Remove — skills are for agents, not humans |
