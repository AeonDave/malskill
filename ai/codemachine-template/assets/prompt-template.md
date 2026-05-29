---
name: "Agent Name"
description: "One-line description of this agent's role and responsibility"
---

## STEP GOAL
What this agent must accomplish. Be specific and measurable.

## MANDATORY EXECUTION RULES
- Read all required inputs before doing anything else
- Check for existing files before overwriting
- Write directive.json as the FINAL action (chat messages do not advance the workflow)

## Required Inputs
1. Read `.codemachine/artifacts/requirements.md`
2. Read `.codemachine/artifacts/technical_spec.md`

Or via placeholders (if registered in placeholders.js):
{{requirements}}
{{tech_spec}}

## Sequence of Instructions
1. [First action]
2. [Second action]
3. [Continue steps]
4. Write output to `.codemachine/artifacts/output.md`
5. Write directive

## Output Artifact
File: `.codemachine/artifacts/output.md`

Contents:
- [Section 1]
- [Section 2]

## Directive
After completing all steps, write `.codemachine/memory/directive.json`:

**On success:**
```json
{ "action": "complete", "reason": "Brief description of what was done" }
```

**On validation failure (if this is a loop module):**
Write `.codemachine/memory/fix_instructions.md` with specific issues, then:
```json
{ "action": "loop", "reason": "X issues found" }
```

**On unrecoverable error:**
```json
{ "action": "error", "reason": "What failed and why" }
```

## SUCCESS METRICS
- [ ] Output artifact written to correct path
- [ ] All required sections present
- [ ] Directive written

## FAILURE METRICS
- Missing input files → write `{ "action": "error", "reason": "Input not found: [path]" }`
- Build/test failure → attempt fix once, then loop or checkpoint
