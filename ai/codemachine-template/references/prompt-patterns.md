# Prompt File Patterns

## Base Structure

```markdown
---
name: "Agent Display Name"
description: "One-line purpose of this prompt"
---

## STEP GOAL
What this agent must accomplish in this step.

## MANDATORY EXECUTION RULES
- Rule 1
- Rule 2

## CONTEXT BOUNDARIES
What information this agent has access to and should NOT access.

## Sequence of Instructions
1. Step one
2. Step two
3. Write directive

## SUCCESS METRICS
- Condition 1
- Condition 2

## FAILURE METRICS
- Condition 1 → action
```

## Directive Output

Every agent MUST write `.codemachine/memory/directive.json`. Chat messages alone do NOT advance the workflow.

```json
{ "action": "complete", "reason": "Task description" }
```

Only `action` and `reason` are recognized. No other fields.

### All directive actions

```json
{ "action": "complete",    "reason": "All steps done" }
{ "action": "continue",    "reason": "Advance to next" }
{ "action": "loop",        "reason": "Tests failed" }
{ "action": "checkpoint",  "reason": "Needs user review" }
{ "action": "trigger",     "reason": "Spawn specific agent" }
{ "action": "error",       "reason": "Unrecoverable failure" }
{ "action": "stop",        "reason": "Workflow complete" }
```

Shared directive reference prompt fragment (`shared/directive-output.md`):

```markdown
## Directive Output
Write `.codemachine/memory/directive.json`:
- `"action": "complete"` — task done, advance
- `"action": "loop"` — issues found, loop back
- `"action": "checkpoint"` — escalate to user
- `"action": "error"` — unrecoverable failure

Only write the file. Chat confirmation is ignored.
```

## Controller Agent Prompts (XML-style)

Controller agents use XML sections for structured behavior:

```markdown
---
name: "Product Owner Controller"
description: "Drives pre-workflow conversation and autonomous approvals"
---

<activation>
You activate when the user initiates the workflow. Your session persists throughout.
</activation>

<persona>
You are a senior product owner. Ask clarifying questions before approving each phase.
</persona>

<operational-modes>
## INTERACTIVE MODE (before workflow starts)
Engage in discovery conversation. When ready, approve workflow start.

## AUTONOMOUS MODE (workflow running)
Monitor step proposals via MCP. Approve or reject with reasoning.
</operational-modes>

<calibration-schema>
For each project, determine:
- scale: small | medium | large
- mode: new_project | existing_app | refactor
</calibration-schema>
```

## Track-Aware Prompts

Read `.codemachine/template.json` to detect selected track and conditions:

```markdown
## Track Detection
Read `.codemachine/template.json` and check `selectedTrack`.

**If selectedTrack == "new_project":**
- Scaffold from scratch
- Ask about tech stack preferences

**If selectedTrack == "existing_app":**
- Run `find . -name "*.ts" | head -50` to understand existing structure
- Adapt plan to existing patterns
```

## Artifact Conventions

### Standard artifact locations
```
.codemachine/artifacts/
├── requirements.md
├── technical_spec.md
└── specs/
    ├── 00_project_calibration.md
    ├── 01_requirements.md
    ├── 02_architecture.md
    ├── 03_openapi.yaml
    └── features/
        └── {feature-name}.feature.md

.codemachine/memory/
├── directive.json          ← ONLY agents write here
└── fix_instructions.md     ← written by loop modules for next iteration
```

### Artifact read pattern in prompts

```markdown
## Required Inputs
1. Read `.codemachine/artifacts/requirements.md` — user requirements
2. Read `.codemachine/artifacts/technical_spec.md` — architecture decisions

## Execution
[Implementation steps using above artifacts]

## Output
Write `.codemachine/artifacts/implementation_report.md`:
- Files created/modified
- Test results
- Issues encountered

Write directive:
`{ "action": "complete", "reason": "Implementation complete: X files written" }`
```

## Sub-Agent Orchestrator Pattern

```markdown
## Sub-Agent Execution

Run sub-agents in the correct order:

```bash
# Data layer first (sequential)
codemachine run "spec-dev-data[tail:30] 'Build data models'"

# API and UI in parallel (independent)  
codemachine run "spec-dev-api[tail:50] & spec-dev-ui[tail:50]"

# Tests last (needs everything above)
codemachine run "spec-dev-tests[tail:50]"
```

If any sub-agent fails, retry once. On second failure, write:
`{ "action": "error", "reason": "Sub-agent spec-dev-api failed twice: [error]" }`
```

## Chained Prompt Pattern

For agents with `chainedPromptsPath`, each step file follows the same structure but appends to previous artifacts:

```markdown
---
name: "Analyst - Step 2: User Personas"
description: "Discovers user types and journeys (chained step)"
---

## Context
Previous step established core features in `.codemachine/artifacts/specs/01_requirements.md`.

## This Step's Goal
Add User Personas section to requirements.

## Instructions
1. Ask: "Who are the main users of this system?"
2. For each persona: name, role, goals, pain points, typical journey
3. Append "## User Personas" to `01_requirements.md`
4. Write directive: `{ "action": "continue", "reason": "Personas documented" }`
```

## Loop Module Pattern

```markdown
---
name: "Quality Gate"
description: "Validates all checks; loops back if issues found"
---

## Validation Checklist
1. `npx tsc --noEmit` — TypeScript errors?
2. `npm test` — test failures?
3. `npm run build` — build errors?

## Decision
**All pass:** `{ "action": "complete", "reason": "All validation passed" }`

**Issues found (attempt < max):**
Write `.codemachine/memory/fix_instructions.md` with specific issues.
Write `{ "action": "loop", "reason": "X issues found: [list]" }`

**Max iterations reached:** `{ "action": "checkpoint", "reason": "Persistent failures need review" }`
```
