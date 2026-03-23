# Skill Template

Use this template when a learning is broad enough to become its own skill.

## Full Template

```md
---
name: skill-name
description: "What the skill does and when to activate it."
---

# Skill Name

One-paragraph statement of the problem this skill solves.

## When to use

- trigger one
- trigger two
- trigger three

## Quick Reference

| Situation | Action |
|---|---|
| trigger | action |

## Workflow

1. step one
2. step two
3. verify outcome

## Gotchas

- warning one
- warning two

## Resources

- `references/...` — when to load it
- `scripts/...` — what it automates
- `assets/...` — what can be copied or reused

## Source

- Learning ID: LRN-YYYYMMDD-XXX
- Extraction Date: YYYY-MM-DD
- Original Category: correction | insight | knowledge_gap | best_practice
```

## Minimal Template

```md
---
name: skill-name
description: "What the skill does and when to use it."
---

# Skill Name

One-sentence problem statement.

## Workflow

1. step one
2. step two

## Source

- Learning ID: LRN-YYYYMMDD-XXX
```

## Extraction Checklist

- the lesson is verified
- the resulting instructions are portable
- examples do not depend on missing chat context
- scripts, if any, have safe defaults
- the skill can stand on its own in a fresh session
