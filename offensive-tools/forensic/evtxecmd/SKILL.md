---
name: evtxecmd
description: "Windows EVTX parsing and timeline extraction with EvtxECmd. Use when investigating PowerShell activity, process execution traces, account events, and security-control tampering from exported event logs, with deterministic CSV/JSON output for incident reconstruction."
license: Apache-2.0
compatibility: "Windows primary (.NET); output consumable cross-platform"
metadata:
  author: AeonDave
  version: "1.0"
---

# EvtxECmd

Deterministic extraction of Windows event logs for objective-driven incident analysis.

## When to use

- You need structured parsing of `.evtx` logs at scale.
- You need precise ScriptBlock/process/account/security event timelines.
- You want reproducible CSV/JSON exports for timeline reconstruction.
- You need fast offline analysis without SIEM dependency.

## Core workflow

1. Identify high-value log channels relevant to the objective.
2. Parse EVTX files into structured output.
3. Pivot by event IDs, providers, host, user, and time window.
4. Normalize timezone assumptions before cross-source correlation.
5. Promote findings only when evidence pointers are explicit.

## High-value event classes

- PowerShell ScriptBlock logging
- Process creation and command-line telemetry
- Logon and account-management events
- Service/task creation and persistence-related changes
- Security-control tampering indicators (Defender, logging, policy)

## Practical analyst tips

- Keep raw EVTX immutable and parse from working copies.
- Use narrow time windows first, then expand as needed.
- Keep a channel inventory to avoid false “no evidence” conclusions.
- Treat parser output as evidence index; validate critical claims in source records.

## Common pitfalls

- Mixing local and UTC timestamps during merge.
- Relying on one channel while missing related provider logs.
- Equating presence of suspicious strings with confirmed execution.
- Ignoring record gaps or truncation when assessing coverage.

## Output expectations

- Structured event dataset (CSV/JSON) with provider, event id, timestamp, host, user.
- Event clusters aligned to investigative objectives.
- Evidence pointers (channel + record id + timestamp) for each key conclusion.
