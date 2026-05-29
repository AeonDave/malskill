# Worker Prompt Patterns

Use this reference when dispatching implementation, research, forensic, exploit-triage, or skill-curation workers.

## Worker packet

Include exactly what the worker needs:

- **Objective**: one task, not a project.
- **Mode and role**: target role or skill, such as researcher, forensic, exploit, web, reverse, CTF route, or reviewer.
- **Loaded skills**: exact role/skill names the worker should load. Workers do not preload the full roster.
- **Topology contract**: sync or async, independence reason, merge point, and retire condition.
- **Model tier**: cheap, standard, diverse standard, premium, or rescue, with reason.
- **Full task text**: paste the task; do not require reading a plan file unless file reading is the task.
- **Context**: where this fits, constraints, relevant artifacts, and allowed paths/actions.
- **Allowed tools/MCP**: exact permitted lanes, including whether Tavily/search/fetch/GitHub queries are allowed and what query terms are public-safe.
- **Prohibited actions**: live target contact, payload execution, credential validation, external submissions, shared-file edits, or destructive/noisy steps.
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
- Did I stop at my branch boundary instead of absorbing the supervisor's job?
- Did I keep MCP/search queries and external submissions inside the packet boundary?
- Are files still focused and interfaces clear?
- What would make this result misleading if the controller trusted it blindly?

## Offensive cautions

- Workers must not expand targets or credentials beyond the packet.
- Workers should report uncertainty instead of “trying one more thing” on live targets.
- Generated payloads, captures, dumps, and secrets stay out of tracked source unless explicitly requested.
- Workers stop after two evidence-based pivots that do not improve confidence; return the blocker, failed paths, and smallest resolving test.
- Research workers produce source ledgers. Forensic workers produce evidence inventories and transformation ledgers. Exploit workers produce repro/primitive evidence, not broad claims.
- Async workers must have predefined output and merge format. If the controller cannot progress while they run, the task should have been synchronous.
- Lab-builder workers reproduce exact versions/config only to answer one narrow question; they must report setup, result, and divergence from target evidence.
