---
name: reading-budget-discipline
description: "Limit context consumption when inspecting large files, tool output, logs, or collections of artifacts. Use when a targeted search or bounded extraction can answer the question without loading everything."
license: MIT
compatibility: "AgentSkills-compatible reading/context guidance for coding, research, forensics, and security work."
metadata:
  author: AeonDave
  version: "1.2"
---

# Reading Budget Discipline

Read enough to establish the fact and its relevant context. Keep bulk data in its source artifact.

## Choose the smallest useful read

- When locating a fact, use scoped search first, then read the matching window and any context needed to interpret it.
- For an unfamiliar large artifact, inspect metadata, headings, or a small preview before choosing sections. Read a short relevant file in full when splitting it would cost more calls.
- Bound the combined output of parallel searches or tool calls, not just each call separately. Return selected fields or excerpts instead of dumping every result.
- If output is truncated, retrieve the missing relevant portion. Do not rerun the entire oversized read.
- Retain source paths, offsets, versions, and caveats with the extracted facts so another reader can check them.

## Logs and changing artifacts

Use the tool's output cursor or the last known byte offset for appended logs. Account for truncation, rotation, or replacement before reusing an offset. Save verbose output to an artifact and inspect the relevant portion.

When reads are repeated only to check completion, apply [running-work guidance](../loop-control-and-pivots/SKILL.md#waiting-for-running-work). A small returned payload does not make repeated model calls free.

## Delegated reading

Use an isolated reader for a large independent review when delegation is available, authorized, and removes work from the parent. Follow the user's model choice. Ask for a concise answer, decisive evidence locations, coverage, and unresolved issues.

Account for handoff and verification cost. Do not delegate a trivial lookup or repeat the reader's entire investigation; inspect the evidence needed to accept its conclusions.

## Return useful context

Lead with the answer, then the supporting facts and material limitations. Omit a second summary that repeats the first. Link to raw artifacts instead of pasting them to keep them handy; include sufficient context to avoid misleading excerpts.
