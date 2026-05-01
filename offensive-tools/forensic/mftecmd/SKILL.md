---
name: mftecmd
description: "NTFS metadata triage with MFTECmd for $MFT/$J/$I30/$Boot artifacts. Use when reconstructing file timelines, finding deleted/hidden files, checking entry-number-based questions, and extracting deterministic metadata from Windows disk artifacts for incident reconstruction."
license: Apache-2.0
compatibility: "Windows primary (.NET); output consumable cross-platform"
metadata:
  author: AeonDave
  version: "1.1"
---

# MFTECmd

Structured extraction and timeline analysis of NTFS metadata artifacts.

## When to use

- You received an `$MFT` (or NTFS metadata set) and need forensic timeline answers.
- You must identify deleted, hidden, copied, or modified files quickly.
- You need reproducible metadata export for filtering in Timeline Explorer/CSV tools.

## Core workflow

1. Parse artifact into structured output (CSV/JSON).
2. Normalize timezone assumptions before interpretation.
3. Filter for key flags and record metadata:
   - in-use vs deleted
   - hidden/system flags
   - copied/renamed indicators
   - entry/record number pivots
4. Compare creation vs modification times for suspicious edits.
5. Build concise chronology and annotate confidence.

## Analyst pivots

- By `EntryNumber` for objective-driven tasks.
- By filename/extension for target-object hunts.
- By timestamp deltas for post-creation tampering.
- By flags for hidden/deleted artifacts.

## Practical tips

- Export first, investigate second: deterministic outputs reduce mistakes.
- Treat timestamp precision consistently (same timezone/display granularity).
- Keep system files excluded only when case requirements explicitly request it.
- Cross-check critical findings with other artifacts when available (logs, prefetch, registry).

## Common pitfalls

- Confusing renamed/copied artifacts with newly created originals.
- Treating a single timestamp in isolation as full chronology.
- Ignoring metadata context (directory entries, flags, and record linkage).

## Output expectations

- Artifact summary (years/periods of activity, notable paths).
- Findings table with record IDs, filename, key timestamps, relevant flags.
- Timeline segment of suspicious or investigation-relevant file operations.
