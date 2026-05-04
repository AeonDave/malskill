# Corpus management across campaigns

Use this when fuzzing the same target family over multiple runs, branches, versions, or harnesses.

## Objective

Treat corpus as a reusable asset, not temporary output. Good corpus management improves coverage while reducing duplicate work and flaky findings.

## 1) Corpus roles

| Corpus | Purpose |
|---|---|
| Seed corpus | Small diverse valid inputs to start exploration |
| Minimized corpus | Smallest set preserving coverage/state depth |
| Crash corpus | Reproducers grouped by bucket/signature |
| Regression corpus | Confirmed bug reproducers used after fixes |
| Negative corpus | Known invalid inputs that should be rejected safely |

## 2) Multi-campaign workflow

1. Start each campaign from minimized, valid seeds.
2. Keep campaign outputs separate by target version and harness.
3. Periodically merge only coverage-improving inputs back into shared corpus.
4. Deduplicate by content hash and coverage signature, not filename.
5. Promote confirmed reproducers into regression corpus with metadata.
6. Retire bloated inputs that add no coverage or only trigger harness errors.

## 3) Metadata to retain

For every promoted input keep:

- Target version/commit/build flags.
- Harness name and invocation path.
- Sanitizers/oracles enabled.
- Coverage or state-depth reason for retention.
- Crash bucket if applicable.
- Reproduction command and expected signal.

## 4) Cross-target caution

Do not blindly merge corpora between related parsers. Normalize and validate first:

- Different file format versions may poison the harness with irrelevant rejects.
- Network/API sequences may depend on server state and auth fixtures.
- Binary-only targets may produce coverage artifacts that do not transfer to source builds.

## 5) When not to fuzz

Pause or choose a different technique when:

- No stable harness or reset path exists.
- Crashes come from the harness, not target code.
- Inputs never reach meaningful parser/state depth.
- Coverage is flat and corpus/model improvements are exhausted.
- The bug class is better found by review: auth logic, simple config exposure, business rules.
- The target is safety-critical or destructive and no lab replica exists.

Fuzzing is a force multiplier after model quality is adequate; it is not a substitute for understanding reachability.
