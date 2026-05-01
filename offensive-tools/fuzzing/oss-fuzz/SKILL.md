---
name: oss-fuzz
description: "Google-hosted continuous fuzzing service for open-source projects. Use for long-running, scalable fuzz campaigns, sanitizer-backed triage, and continuous bug reporting with reproducible local workflows."
license: Apache-2.0
compatibility: "Service model for eligible OSS projects; local workflows via oss-fuzz repo + ClusterFuzz variants."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# oss-fuzz

Continuous fuzzing platform that runs supported engines (`libFuzzer`, `AFL++`, `Honggfuzz`, `Centipede`) at scale.

## When to Use

- You maintain an open-source project and need persistent fuzz coverage.
- You want automated sanitizer-based crash reporting and regression tracking.
- You need multi-language support beyond ad-hoc local campaigns.

## Core Flow

1. Add project integration config to OSS-Fuzz repo.
2. Define build/fuzz targets and seed corpora.
3. Validate locally with OSS-Fuzz tooling.
4. Submit and monitor issue stream.

## Local Validation Flow

```bash
python3 infra/helper.py build_image <project>
python3 infra/helper.py build_fuzzers --sanitizer address <project>
python3 infra/helper.py check_build <project>
python3 infra/helper.py run_fuzzer --corpus-dir=<tmp-corpus> <project> <fuzz_target>
```

Run additional sanitizer/engine combinations when integration quality is uncertain.

## Reproduction Flow (Bug Fix Loop)

```bash
python3 infra/helper.py reproduce <project> <fuzz_target> <testcase_path>
```

If the bug is not reproducible immediately:

- pull latest images,
- match sanitizer and architecture from report,
- retry with exact target binary and runtime flags.

## Practical Tricks

- Keep seed corpus and dictionaries small but meaningful; large noisy corpora can slow signal.
- Prefer statically linked fuzz binaries in build scripts for runtime compatibility.
- Use Fuzz Introspector reports to detect low-reach fuzz targets and prioritize harness work.

## Common Pitfalls

- Skipping local `check_build` before PR submission.
- Treating one sanitizer pass as complete validation.
- Ignoring architecture-specific issues (some findings reproduce only on `i386` or `x86_64`).

## Notes

- Best for continuous defect discovery, not one-off local triage.
- For closed-source/internal projects, use ClusterFuzz/ClusterFuzzLite style alternatives.
- Build artifacts copied to `$OUT` should remain reasonably small to avoid slow transfer/unzip cycles.

## Resources

- https://google.github.io/oss-fuzz/
- https://github.com/google/oss-fuzz
- https://google.github.io/oss-fuzz/getting-started/new-project-guide/
- https://google.github.io/oss-fuzz/advanced-topics/reproducing/
- https://google.github.io/clusterfuzzlite/
