# Skill Triggering Tests

Use this reference when a skill may not activate from natural user prompts or may activate too broadly.

## What to test

Create small prompt fixtures:

- **Direct request**: user names the skill or concept.
- **Natural task**: user asks for work that should trigger the skill without naming it.
- **Near miss**: adjacent task that shares terminology but should not trigger.
- **Pressure prompt**: user asks to skip formalities, go fast, or “just do it”.

## Fixture shape

```markdown
Prompt: realistic user request
Expected skill: skill-name or none
Reason: triggering phrase, symptom, file type, or boundary
```

Use natural prompts with varied phrasing, detail, formality, and indirect intent. Include realistic paths or domain details when relevant. Avoid trivial negative cases with no overlap.

## Manual pass criteria

- The skill activates before action when it should.
- The skill does not activate on near misses.
- The agent reads the body instead of only following the description shortcut.
- The resulting behavior follows the skill, not just mentions it.

## Description tuning

If the skill under-triggers, clarify the missing intent or task context. If it over-triggers, add the smallest meaningful boundary. Do not stuff the description with synonyms or copy exact phrases from failed fixtures.

Avoid workflow summaries in descriptions when they tempt the agent to skip reading the skill body. The description should route the agent; the body should run the process.

Rerun the affected fixture matrix after changing the description, body, or target runtime. For substantial description optimization, repeat prompts to account for nondeterminism and keep a fixed held-out set for selecting the best revision.
