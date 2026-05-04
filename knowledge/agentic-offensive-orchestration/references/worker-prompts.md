# Worker Prompt Patterns

Use this reference when dispatching implementation, research, exploit-triage, or skill-curation workers.

## Worker packet

Include exactly what the worker needs:

- **Objective**: one task, not a project.
- **Full task text**: paste the task; do not require reading a plan file unless file reading is the task.
- **Context**: where this fits, constraints, relevant artifacts, and allowed paths/actions.
- **Before starting**: ask about unclear requirements, dependencies, assumptions, or unsafe steps.
- **Verification**: commands/artifacts the worker must produce or inspect.
- **Report format**: status, changes, evidence, files, concerns.

## Status contract

| Status | Meaning | Controller action |
|---|---|---|
| done | completed and verified | review artifacts before accepting |
| done with concerns | completed but doubts remain | inspect concerns before review |
| needs context | blocked by missing information | provide context or narrow scope |
| blocked | cannot complete safely/correctly | change model, split task, or escalate |

Do not force a blocked worker to retry unchanged. Something in scope, context, capability, or plan must change.

## Self-review prompts

Ask each worker to check before reporting:

- Did I implement exactly the task and no unrelated extras?
- Did I preserve scope, authorization, and destructive-action limits?
- Did I verify behavior with primary evidence?
- Are files still focused and interfaces clear?
- What would make this result misleading if the controller trusted it blindly?

## Offensive cautions

- Workers must not expand targets or credentials beyond the packet.
- Workers should report uncertainty instead of “trying one more thing” on live targets.
- Generated payloads, captures, dumps, and secrets stay out of tracked source unless explicitly requested.
