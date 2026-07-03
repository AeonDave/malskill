# File-format fuzzing methodology

## Objective

Drive parser logic deep enough to trigger memory corruption, parser confusion, and unsafe state transitions.

## Practical workflow

1. **Define the real parsing boundary**
	- Fuzz the component that performs semantic decoding, not only container pre-checks.

2. **Create a layered corpus**
	- Layer A: tiny valid files that pass the earliest gates.
	- Layer B: diverse valid files exercising optional chunks/sections.
	- Layer C: malformed edge cases (truncated, nested, oversized, inconsistent metadata).

3. **Constrain and then expand mutations**
	- Start with size and structure limits to keep high exec/s.
	- Expand size/depth after initial stability and coverage are verified.

4. **Use dictionaries and structure hints**
	- Add magic values, chunk tags, and delimiter tokens.
	- Prefer targeted token enrichment over random large dictionary growth.
	- For deeply structured formats (protobuf, ASN.1, complex TLV/AST), switch to structure-aware mutation (custom mutator, libprotobuf-mutator, grammar-based generators) instead of stacking dictionaries.

5. **Run dual profiles**
	- Throughput profile for exploration.
	- Sanitizer profile for bug validation and bucket quality.

## Scenario mapping

- **Image/video codecs**: prioritize chunk/frame boundary mutations and metadata-length mismatch.
- **Archive/parsing stacks**: stress nested containers and recursive extraction paths.
- **Document formats**: test optional object trees and cross-reference inconsistencies.
- **Custom binary protocols as files**: combine dictionary tokens with state-field corruption.

## Handling common blockers

- **Checksums/signatures block progress**
  - In fuzz builds, isolate or bypass non-security integrity gates where safe.
- **Too many early rejects**
  - Improve valid seed diversity before increasing mutation aggression.
- **Coverage plateaus**
  - Add focused seeds for untouched parser features; avoid only adding runtime.

## Triage orientation

- Group by parser stage (header parse, object decode, decompression, rendering path).
- Minimize one representative per bucket before deep debugging.
- Keep a regression corpus of fixed bugs to prevent reintroduction.

## Anti-patterns

- Fuzzing only corrupt inputs with no valid baseline.
- Using huge corpora without minimization.
- Treating every crash as unique before stack bucketing.
