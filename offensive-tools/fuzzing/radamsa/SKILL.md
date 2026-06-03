---
name: radamsa
description: "Auth/lab ref: General-purpose mutation engine for generating malformed test inputs."
license: MIT
compatibility: "Cross-platform builds; canonical source is GitLab."
metadata:
  author: GitHub Copilot
  version: "1.1"
---

# radamsa

Mutation-focused fuzzer/generator: excellent as an input transformer in pipelines.

## Quick Start

```bash
# Example mutation from file -> stdout
radamsa seed.bin > mutated.bin

# Batch generate samples
radamsa -n 100 -o out-%n.bin seeds/*
```

## Operator Flow

1. Collect representative seed samples (multiple real-world variants).
2. Generate mutations in deterministic mode when triaging (`--seed`).
3. Pipe outputs into target/harness and monitor crash/timeout/resource metrics.
4. Preserve crashing case + seed metadata.
5. Replay with identical seed/options before root-cause analysis.

## Best Pattern

- Use Radamsa as a feeder into:
  - web fuzzers,
  - API clients,
  - parser harnesses,
  - protocol replay tools.
- Keep reproducibility via controlled seeds when triaging (`--seed` patterns).

## Practical Tricks

- Use `%n` output patterns with `-o` to preserve one-file-per-testcase workflows.
- Prefer many diverse seeds over one huge synthetic seed.
- For network workflows, pair with replay harnesses or server/client output modes supported by Radamsa.
- Start broad first, then constrain mutator options only if throughput or relevance requires it.

## Common Pitfalls

- Treating Radamsa as coverage-guided: it is mutation-focused, not coverage-native.
- Ignoring seed quality; weak seeds produce weak campaigns.
- Running unreproducible random campaigns without seed tracking.

## Notes

- GitHub mirror is stale; upstream moved to GitLab.
- Strong complement to coverage-guided engines (AFL++/libFuzzer/honggfuzz).

## Resources

- https://gitlab.com/akihe/radamsa
- https://github.com/aoh/radamsa
- https://gitlab.com/akihe/radamsa/-/blob/develop/README.md
