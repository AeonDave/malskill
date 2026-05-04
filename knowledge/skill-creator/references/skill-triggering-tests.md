# Skill Triggering Tests

Use this reference when a skill may not activate from natural user prompts or may activate too broadly.

## What to test

Create small prompt fixtures:

- **Direct request**: user names the skill or concept.
- **Natural task**: user asks for work that should trigger the skill without naming it.
- **Near miss**: adjacent task that should not trigger.
- **Pressure prompt**: user asks to skip formalities, go fast, or “just do it”.

## Fixture shape

```markdown
Prompt: realistic user request
Expected skill: skill-name or none
Reason: triggering phrase, symptom, file type, or boundary
```

## Manual pass criteria

- The skill activates before action when it should.
- The skill does not activate on near misses.
- The agent reads the body instead of only following the description shortcut.
- The resulting behavior follows the skill, not just mentions it.

## Description tuning

If the skill under-triggers, add concrete symptoms, task names, file types, and common user phrasing. If it over-triggers, add near-miss boundaries in the description or first section.

Avoid workflow summaries in descriptions when they tempt the agent to skip reading the skill body. The description should route the agent; the body should run the process.
