# Evidence preservation workflow

## Purpose

Standardize acquisition and preservation decisions so findings remain reproducible and defensible.

## 1) Intake and scoping

- Record source, handler, timestamp, and declared evidence type.
- Assign unique evidence ID before touching contents.
- Define immediate objective (containment, triage, legal hold, deep investigation).

## 2) Integrity and custody baseline

- Compute at least one strong hash at intake.
- Record acquisition/mount method and write-protection state.
- Record every evidence transfer (who, when, why, condition).
- Store originals read-only; analyze on working copies only.

## 3) Collection strategy by volatility

- Volatile first: memory and active network state.
- Rotating logs second.
- Full images and long-tail artifacts after initial stabilization.

## 4) Minimal-change handling rules

- Prefer read-only mount and detached analysis hosts.
- Avoid executing unknown binaries directly from evidence media.
- Avoid enrichment steps that mutate source timestamps/metadata.

## 5) Verification checkpoints

- Re-hash working copies after transfer and before reporting.
- Confirm time source and timezone assumptions at first analysis step.
- Flag any integrity gap immediately and isolate affected evidence.

## 6) Deliverables for downstream analysis

- Evidence manifest (ID, type, hash, source, owner).
- Custody log.
- Acquisition notes (tools, versions, options).
- Initial triage summary and priority queue.
