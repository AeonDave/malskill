# Subagent Patterns

Use subagents for bounded research or implementation tasks where fresh context improves quality.

## Minimal prompt packet

Include:

- objective: one sentence
- mission mode and starting state: capability assessment, adversary emulation, objective-led operation, artifact triage, or skill/tool curation; scope only, credential/token, foothold/session, artifact, or objective-led chain
- inputs: paths, URLs, artifacts, command outputs, assumptions already verified
- boundaries: scope, ROE, destructive/noisy limits, data-handling rules, files that may be changed, time budget, kill-switch
- expected signal: what result would validate, disprove, or block the chain link
- output format: bullets, table, patch summary, or evidence packet
- stop rule: when to ask instead of guessing

## Parallelism rules

Parallelize only when:

- tasks do not mutate the same target or files
- outputs can be validated independently
- rate limits/noise are understood
- failure of one task does not invalidate another mid-run

Keep serial when:

- exploit steps depend on previous primitives
- one task may change target state
- root cause is unknown and broad parallel fixes would hide evidence
- two workers would race on the same branch or artifact
- starting state is uncertain and one classification result changes all downstream routing

## Output synthesis

Collect outputs into:

| Field | Required content |
|---|---|
| Fact | Evidence-backed observation |
| Evidence | Artifact, command, location, or citation |
| Confidence | confirmed, likely, plausible, unknown |
| Risk | scope, noise, destructiveness, false-positive risk |
| Next action | smallest safe verification or implementation step |

## Review checklist

- Did any worker exceed scope or assume authorization?
- Are claims backed by fresh evidence rather than reputation or tool output alone?
- Do workers contradict each other? If yes, preserve the conflict and resolve with targeted checks.
- Is final synthesis shorter and clearer than the raw worker outputs?
