---
name: handoff
description: "Write a portable handoff document so another agent can continue the current work. Use only when the work must move to a new harness, directory, repo, operator, or a forked parallel session; invoke on explicit request, not autonomously."
license: MIT
compatibility: "Agent-neutral; writes one markdown file to the OS temp directory."
metadata:
  author: AeonDave
  version: "1.0"
---

# Handoff

Compact the current session into one portable document a fresh agent can act on. The value is portability, not better compression.

## Warranted only when work travels

Produce a handoff only when the work must reach a context that cannot see this session:

- A different harness or agent that lacks this session's history.
- A different directory or repository.
- Another operator who needs something readable.
- A side task forked mid-phase: this session stays live while a second agent runs the fork in parallel and returns its result.

If nothing travels — same harness, same workspace, you continue — use the host's native compaction, resume, or a subagent. A handoff does not summarise better. Invoke it on explicit request, not on your own. Treat any passed note as the next session's objective and tailor the document to it.

## What the document carries

- The live thread: what is in flight, the decided direction and why, and the next concrete action.
- A "suggested skills" section naming the skills the next agent should load for the stated objective.
- Pointers, not copies: reference specs, plans, ADRs, issues, commits, diffs, scan outputs, and evidence files by path or URL. Do not paste content that already lives in an artifact; two copies drift.
- For authorized security work, the engagement scope and rules of engagement, in-scope targets, where credentials and loot are stored, and the current foothold or state — so the next agent stays within authorization.

## What stays out

- Redact secrets, tokens, keys, credentials, captured loot, and PII. Name where they live under the engagement's handling rules; never write the values into a transit document.
- Anything already settled in an artifact. Reference it instead of restating it.

## Accuracy before transfer

The next agent trusts the document and will not re-verify it, so a belief written as fact becomes a false premise. Mark unverified beliefs as assumptions; do not assert "X is done" or "Y is not built" unless this session confirmed it. Keep the document a small fraction of the conversation.

## Storage and delivery

- Write to the OS temp directory (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows), not the workspace. Report the absolute path back.
- Temp is not durable: if the next session is cross-harness or not starting soon, copy the file and anything it points at somewhere durable.
- Hand off by pointing the fresh session at the path ("read this file, then continue"), not by pasting the summary into a shell argument, which silently mangles backticks and `$(...)`.

Use `loop-control-and-pivots` for handing off a long-running job within a session, and `memory-hygiene` for durable project facts that belong in standing context rather than a one-task handoff.

