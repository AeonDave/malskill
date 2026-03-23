# Learnings

Prevention rules captured during real work. Each entry must be a concise rule, not an incident report.

**Brevity**: Summary ≤1 sentence. Details ≤3 sentences. Suggested Action = 1 imperative sentence. Total ≤30 lines.

**Categories**: correction | insight | knowledge_gap | best_practice
**Areas**: workflow | repo-config | docs | tooling | programming | testing | knowledge | research | offensive-tools | bof
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|---|---|
| `pending` | Captured but not yet resolved or promoted |
| `in_progress` | Actively being worked on |
| `resolved` | The issue is fixed or the knowledge has been integrated |
| `wont_fix` | Intentionally left unresolved; explain why in a resolution block |
| `promoted` | Distilled into project guidance or persistent memory |
| `promoted_to_skill` | Extracted into a reusable standalone skill |

## Skill Extraction Fields

When a learning becomes a skill, add:

```md
**Status**: promoted_to_skill
**Skill-Path**: knowledge/skill-name
```

## Review Rule

Review this file before major follow-up work in the same area. Prefer updating existing recurring entries over creating duplicates.
