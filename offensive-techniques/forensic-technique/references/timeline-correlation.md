# Timeline correlation

## Purpose

Merge disk, memory, and network events into one coherent chronology with explicit confidence scoring.

## 1) Normalize time first

- Convert all source timestamps to one canonical timezone (prefer UTC).
- Record known clock skews for each source.
- Keep raw timestamp and normalized timestamp side-by-side.

## 2) Build source-local timelines

- Disk: execution, persistence, user activity, file events.
- Memory: active processes, sockets, loaded regions.
- Network: session starts/stops, protocol pivots, object transfers.

## 3) Merge rules

- Merge by temporal proximity + shared entity (host/user/process/domain/path).
- Require at least one shared entity for correlation claims.
- If only timing overlaps exist, mark as weak correlation.

## 4) Confidence model

- High: direct match across 2+ independent sources.
- Medium: single-source direct evidence + strong contextual support.
- Low: plausible sequence without direct cross-source confirmation.

## 5) Contradiction handling

- Keep conflicting interpretations visible.
- Prefer artifact-backed sequence over assumption-backed sequence.
- Record what additional evidence would resolve ambiguity.

## 6) Reporting format

Each key event should include:
- normalized time,
- source artifact pointer,
- event description,
- confidence level,
- linked events.
