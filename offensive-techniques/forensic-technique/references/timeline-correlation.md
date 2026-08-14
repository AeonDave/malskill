# Timeline correlation

## Purpose

Merge disk, memory, and network events into one coherent chronology with explicit confidence scoring.

## 1) Normalize time first

- Convert all source timestamps to one canonical timezone (prefer UTC).
- Record known clock skews for each source.
- Keep raw timestamp and normalized timestamp side-by-side.
- Preserve the timezone evidence used for conversion. For an offline Windows host, resolve the active control set through `SYSTEM\Select\Current`, then inspect `Control\TimeZoneInformation` (`TimeZoneKeyName`, `Bias`, and `ActiveTimeBias`). Windows bias is minutes added to local time to obtain UTC, so `-120` means UTC+02:00. For Linux text logs, prefer an explicit numeric offset or the collected host timezone over the analyst workstation's locale.

## 2) Build source-local timelines

- Disk: execution, persistence, user activity, file events.
- Memory: active processes, sockets, loaded regions.
- Network: session starts/stops, protocol pivots, object transfers.

### Match event semantics before matching seconds

Artifact timestamps often describe different lifecycle boundaries:

- Prefetch last-run records program launch, not process termination.
- A USN update to an executable's `.pf` file records Prefetch maintenance, not the executable's exit.
- Script-block, service-install, or file-creation time may precede the activity the script or binary initiated.

When the requested boundary is missing on one host, correlate the peer side of the same session. For example, pair a client SSH launch or kill action with the server's `sshd` session-open/session-close record using user, source, destination, and session ordering. Normalize each host independently before comparing times.

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

## 7) Bounded timestamp oracles

Use a task or validation oracle only after two independent artifacts converge on the same event and the remaining uncertainty is timestamp granularity:

1. Choose the evidence-backed second and document the raw subsecond value and timezone conversion.
2. Generate a small deterministic window, normally no more than a few seconds on either side.
3. Submit candidates at a controlled rate and stop on the first explicit acceptance signal; HTTP success or format matching alone is not an oracle.
4. If the window fails, revisit event semantics and timezone evidence instead of widening it blindly.
