# Interpret Windows Survey Evidence

Load when comparing Ashura survey logs across Windows builds, checking diagnostic module inventories, or deciding whether a collected observation can become a build-specific rule.

## Read the numerical evidence

Load [the October 2026 CSV](../assets/windows-survey-v5-2026-10.csv) when comparing that historical cohort. It is the canonical home of its per-run values, raw-log locators, hashes, and missing evidence. Keep all rows, including repeated build/revision pairs; filter by architecture and collector schema before comparing values.

- **LDR entries:** the current process's bounded in-load-order traversal. Check entry plausibility and reported truncation separately. Use [peb-teb.md](peb-teb.md#read-only-ldr-plausibility-checks) for exactly what those checks establish.
- **Named exports:** `shadow exports` is the mapped `ntdll` export directory's `NumberOfNames`, not a count of functions invoked or exports fully validated.
- **Names inspected:** `shadow scanned` counts iterations until the selected `RtlGetVersion` name is found or the search terminates. It is a prefix search, not complete export parity or validation of every name/function.
- **Outcome counters:** counts describe records observed in the log. Check missing modules and `prefinal` evidence before treating zero observed errors as a complete set of checks. `unknown` is missing evidence, not zero.
- **Optional flags:** v5 emits `ldr truncated=1` only on truncation, not an explicit zero on a normal walk. The CSV keeps a missing flag `unknown`; use `ldr_outcome` and the entry evidence to assess the traversal.
- In the saved cohort, samples E and F identify different hosts. A difference between their process inventories does not isolate its cause. Matching OS build/revision and export counts do not establish matching image hashes.

Treat these rows as diagnostic observations of these runs. They do not extend architecture/OS compatibility, validate private structure layouts, or qualify another program's runtime behavior.

## Collection and interpretation gates

| Evidence | Check before using a row |
|---|---|
| Collector identity | Preserve version/schema and the executable SHA-256; bind it to a source revision and build command. The current source hash alone does not identify the executable used earlier. |
| OS revision | Keep `ubr_status` with `ubr`. In this collector, a failed registry read produces `ubr=0`; do not treat that as a confirmed revision zero. |
| Image identity | Retain the actual loaded and separately mapped image identities: file version, SHA-256, and PE/PDB identity where available. An OS build label is insufficient. |
| Collection closure | Require expected module outcomes, process exit 0, and final stdout `survey result: ok`. `prefinal` is emitted before final flush/close. Missing closure evidence stays unknown. |
| Check outcomes | Preserve `ok`, `skipped`, `error`, `fault`, and `not_run`. Errors/faults/unexecuted modules make the relevant checks incomplete; expected absence/skips are not positive observations. |
| Sampling | Record scan windows, entry/location caps, early termination, and concurrent process activity. Counts can exceed the number of stored locations. |
| Cross-version comparison | Re-read the schema implementation before merging versions; archived v1-v4 and v5 are separate cohorts until field semantics are normalized. |

For address fields in any probe, record whether the unit is a virtual address, image RVA, section-relative offset, or file offset. Ashura v5 uses `text_off` for section-relative positions in its TLS/gadget scans; archived v1-v4 fields named `rva`/`head_rva` in those scans were section-relative. Do not reinterpret old names as image RVAs or compare units implicitly.

A present export establishes presence only. Readable fields establish plausibility only. Byte-pattern counts do not establish instruction boundaries, execution semantics, or mitigation compatibility. Corroborate the particular claim rather than promoting the whole probe to a compatibility verdict.

Use [the shared OS/runtime evidence workflow](../../../offensive-techniques/reversing-technique/references/re-workflow.md#verify-osruntime-behavior) for matching source, symbols, and controlled traces.

## Summarize and refresh

From the malskill repository root, use [scripts/summarize_windows_survey.py](../../../scripts/summarize_windows_survey.py) for an offline diagnostic CSV:

```bash
python scripts/summarize_windows_survey.py /path/to/results > survey.csv
```

The helper accepts v5/schema 5 x64 logs, preserves individual runs, hashes raw bytes, and outputs whitelisted diagnostic fields. It does not run the collector. Missing final receipts, executable hashes, and image hashes remain `unknown`; a positive `prefinal` cannot fill them. Standard numeric collector basenames are retained; other basenames become `unknown`, with the raw SHA-256 still identifying the input's content. Keep a separate private file locator for sanitized names. Sample letters describe the current sorted input set; use hashes for identity across refreshes. Review unsupported/malformed inputs before importing another schema.

Inspected implementation: `tools/ashura_survey.c` (version 5) and `tools/README.md` in the AshuraLoader source tree, reviewed 2026-10-09. SHA-256 of the inspected **source file**: `e70408d40ea4ca217f3c7879b2740a63f6425cb4d12b67065ed7d98221f3d83f`. The supplied logs do not bind their collectors to this source hash; executable hashes and exact `ntdll` identities were not supplied. The older `docs/archive/windows-fleet-survey-2026-10.md` snapshot is a separate historical cohort.

Retain raw logs and collection receipts as separate evidence artifacts. Before refreshing a row, verify its raw-log hash, collector schema, image identities, and closure status. Append reruns instead of replacing same-build rows; keep host identifiers and absolute process addresses out of published summaries.
