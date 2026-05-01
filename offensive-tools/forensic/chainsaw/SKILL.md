---
name: chainsaw
description: "Fast DFIR triage for Windows forensic artifacts (EVTX, MFT, registry, ESE/SRUM) with Sigma and built-in detection logic. Use when analyzing exported Windows event logs, performing first-response hunting, detecting log tampering gaps, or producing CSV/JSON findings quickly without full SIEM infrastructure."
license: GPL-3.0
compatibility: "Windows/Linux/macOS; standalone binary from GitHub releases"
metadata:
  author: AeonDave
  version: "1.1"
---

# Chainsaw

Rapid first-response hunting across Windows artifacts with Sigma + Chainsaw rules.

## When to use

- You have exported `.evtx` logs and need fast threat triage.
- You need ScriptBlock/Defender/service/task detection without SIEM.
- You want timeline-oriented findings in CSV/JSON for incident notes.
- You suspect selective EVTX tampering and need record/time gap checks.

## Core workflow

1. Validate artifact scope (which channels and time range are present).
2. Run `hunt` with Sigma + mapping and optionally Chainsaw rules.
3. Export to CSV/JSON and pivot on key EventIDs.
4. If tampering is suspected, run `analyse gaps`.
5. Correlate detections with process, registry, and network evidence.

## High-value modes

- `hunt` → detection logic over event logs
- `search` → targeted string/regex/tau queries
- `analyse shimcache` → execution timeline + optional amcache enrich
- `analyse srum` → network/application usage artifacts
- `analyse gaps` → potential selective log deletion indicators
- `dump` → raw structured extraction from supported artifacts

## Practical analyst tips

- Prefer bounded time windows (`--from`/`--to`) for cleaner triage.
- Use `--full` only after narrowing candidates (reduces noise).
- Keep Sigma repository current; rule freshness impacts detection quality.
- Mark whether a finding is direct event evidence or rule-based inference.
- Always preserve the original logs and operate on copies.

## Common pitfalls

- Treating rule hits as final verdict without context.
- Mixing local and UTC timestamps during timeline reconstruction.
- Running broad hunts across huge log sets without narrowing scope first.
- Ignoring capture/log retention gaps when concluding absence of activity.

## Output expectations

- Detection table with timestamp, host, rule, event id, key fields.
- List of high-confidence suspicious commands/actions.
- Optional tampering assessment (`analyse gaps`) with confidence notes.
- Correlation pointers for downstream timeline reconstruction.
