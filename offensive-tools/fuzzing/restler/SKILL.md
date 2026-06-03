---
name: restler
description: "Auth/lab ref: Stateful REST API fuzzer from OpenAPI specs. For testing complex API dependency chains, producer-consumer request sequencing, and replayable bug-bucket workflows for API reliability/security testing."
license: MIT
compatibility: "Windows/Linux (64-bit primary), Python +.NET build/runtime."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# restler

RESTler explores deeper API states by inferring request dependencies from OpenAPI definitions.

## Workflow (Recommended Order)

1. **Compile**: OpenAPI -> RESTler grammar.
2. **Test (smoke)**: verify setup and required dictionary values.
3. **Fuzz-lean**: quick bug hunting baseline.
4. **Fuzz**: deep BFS-style state exploration.

## Quick Start

```bash
# Build (local)
python build-restler.py --dest_dir <restler_bin>

# Typical campaign starts with compile + test before fuzz modes
restler.exe fuzz-lean --grammar_file <grammar.py> --dictionary_file <dict.json>
restler.exe fuzz --grammar_file <grammar.py> --dictionary_file <dict.json> --time_budget 1
```

## Operator Flow

1. Validate schema quality and authentication path first.
2. Run `test`/smoke style workflow to confirm dependencies and dictionary values.
3. Run `fuzz-lean` for quick risk discovery.
4. Run `fuzz` for deeper sequence exploration with settings file tuning.
5. Reproduce via replay logs and bug buckets before assigning fixes.

## Practical Notes

- Always fix setup gaps discovered in `test` mode before deep fuzzing.
- Deep fuzzing can cause service instability/outages on weak implementations.
- Use replay logs and bug buckets for deterministic re-validation.

## High-Value Settings

- `fuzzing_mode` (`bfs`, `bfs-cheap`, `random-walk`, `directed-smoke-test`)
- `max_sequence_length`, `max_combinations`
- include/exclude endpoint filters (`include_requests`, `exclude_requests`, `path_regex`)
- retry & timing controls (`custom_retry_settings`, `producer_timing_delay`)
- trace database (`use_trace_database`) for structured replay workflows

## Replay & Triage Pattern

1. Start from `bug_buckets.txt` summary.
2. Open specific bucket replay log and verify request sequence.
3. Replay with same auth/host settings.
4. Confirm reproducibility and collect minimal sequence evidence.
5. Patch server + rerun replay to verify closure.

## Common Pitfalls

- Skipping auth refresh handling leads to noisy false negatives.
- Fuzzing full API surface without scope controls can burn time-budget quickly.
- Forgetting manual cleanup after replay-created resources.

## Resources

- https://github.com/microsoft/restler-fuzzer
- https://github.com/microsoft/rest-api-fuzz-testing
- https://raw.githubusercontent.com/microsoft/restler-fuzzer/main/docs/user-guide/Fuzzing.md
- https://raw.githubusercontent.com/microsoft/restler-fuzzer/main/docs/user-guide/SettingsFile.md
- https://raw.githubusercontent.com/microsoft/restler-fuzzer/main/docs/user-guide/BugBuckets.md
- https://raw.githubusercontent.com/microsoft/restler-fuzzer/main/docs/user-guide/Replay.md
