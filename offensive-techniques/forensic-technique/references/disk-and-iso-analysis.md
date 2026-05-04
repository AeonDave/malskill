# Disk and ISO analysis

## Purpose

Guide practical analysis flow for E01/DD/RAW disk images and ISO media while keeping work hypothesis-driven.

## A. Disk image flow (E01/DD/RAW)

1. Validate hash and document mount/access mode.
2. Map partition and file-system layout.
3. Triage high-yield paths first:
   - User profiles, startup/persistence locations
   - Event/log stores
   - Browser and download history
   - Script/task/scheduler artifacts
4. Build a preliminary timeline early.
5. Recover deleted artifacts only for timeline gaps or specific hypotheses.
6. Confirm key findings through cross-artifact checks.

### Common high-value artifacts

- Account and session artifacts (logons, profile activity)
- Execution indicators (Prefetch, LNK, Jump Lists, UserAssist, AmCache, ShimCache, SRUM, startup entries, task schedulers)
- Command and script history
- Browser artifacts (history, cache, downloads)
- Security-relevant logs and audit traces

## B. ISO analysis flow

1. Validate hash and mount read-only.
2. Inventory structure and compare against expected vendor layout.
3. Identify executable/script payloads and installer logic.
4. Check autorun/config metadata, embedded resources, shortcut chains, Office/PDF payloads, and external template references.
5. Scan extracted content with signature/rule-based triage.
6. Correlate suspected payloads with endpoint execution evidence.

## C. Decision rules

- If timeline and known artifacts already answer scope questions, postpone deep carving.
- If deleted artifact recovery changes sequence interpretation, mark confidence downgrade until corroborated.
- If ISO content appears benign but endpoint shows suspicious execution, prioritize endpoint-memory correlation.

## D. Output

- Short chronology of user/system actions.
- List of suspicious artifacts with path, timestamp, hash, and reason.
- Explicit uncertainty notes for artifacts that require additional validation.
