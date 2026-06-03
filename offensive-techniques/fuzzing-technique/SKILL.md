---
name: fuzzing-technique
description: "Auth/lab: fuzzing methodology; target model, oracle, harness quality, corpus, campaign triage for parsers, binaries, protocols, APIs."
license: MIT
compatibility: "Linux/Windows/macOS; source-available and binary-only targets; local and remote environments."
metadata:
  author: AeonDave
  version: "1.2"
  category: exploitation
  language: multi
---

# Fuzzing technique

Goal: help the agent run fuzzing as a **repeatable engineering process** that finds real bugs fast and produces actionable, low-noise triage.

## When this technique applies

- Input-processing code (file parsers, codecs, protocol handlers, deserializers).
- APIs with complex producer-consumer dependencies.
- Stateful services where request/packet ordering matters.
- Binary-only software where source instrumentation is unavailable.

## Boundary with offensive-tools

This skill defines **methodology, decision flow, and quality gates**.
Tool-specific flags, options, and command syntax belong in `offensive-tools/*`.

## Initial triage

Before starting a campaign, classify the target shape and decide what kind of model and oracle will produce meaningful failures.

- **Starting state**: are you testing source-available code, a binary-only target, a stateful network service, or an API/schema-driven system?
- **First questions**: what are the highest-value entry points, what bug signal counts as success, and can you build a deterministic harness or request model?
- **Immediate actions**: choose one narrow target path, define oracles, and prove replayability before scaling throughput.
- **Tool-family direction**: use in-process coverage-guided families (`libfuzzer`, `aflplusplus`, `honggfuzz`) for source targets, binary instrumentation families (`winafl` and similar) for closed binaries, `boofuzz` for stateful protocols, and `restler`/`schemathesis` for APIs.
- **Escalation rule**: improve model quality and seed quality before extending campaign duration.

## Agent operating model

The agent should keep this loop:

1. Build a target model.
2. Select oracle(s) that detect meaningful failures.
3. Build/verify harness or request model quality.
4. Engineer seed corpus and mutation guidance.
5. Run campaign with intentional diversity.
6. Triage, minimize, deduplicate, and replay.
7. Feed learning back into model/corpus/harness.

Do not scale campaign duration before determinism and replay are stable.

## Case-to-tool-family selection

Use the simplest family that gives coverage signal and reproducible failures.

1. **Source-available C/C++/Rust parser/library**
  - Start with in-process coverage-guided harness.
  - Typical families: coverage-guided engine + sanitizer workflow.
  - Why: fastest iteration, highest bug signal quality.

2. **Binary-only local target**
  - Use binary instrumentation/emulation mode.
  - Typical families: binary-only coverage workflows.
  - Why: no source required; slower than source-based, still coverage-guided.

3. **Stateful network protocol service**
  - Model protocol phases and transition constraints first.
  - Typical families: request-graph/stateful network fuzzing.
  - Why: easier control of handshake/state transitions and crash recovery.

4. **REST/OpenAPI service**
  - Use schema-aware + stateful dependency learning.
  - Typical families: contract-aware API fuzzing.
  - Why: automatically reaches valid states and explores success paths, not only 404/400 noise.

5. **Early feasibility phase when no model exists**
  - Use short smoke runs to rank entrypoints by signal.
  - Typical families: lightweight mutation-first probing.
  - Why: avoid over-investing in low-value targets.

## Tool families

| Family | Best fit | Skill |
|--------|----------|-------|
| `aflplusplus` | Coverage-guided C/C++/Rust source or LLVM-instrumented binary | `offensive-tools/fuzzing/aflplusplus/` |
| `libfuzzer` | In-process C/C++ harness (fast, sanitizer-friendly) | `offensive-tools/fuzzing/libfuzzer/` |
| `honggfuzz` | Coverage-guided; good for persistent-mode and multi-process | `offensive-tools/fuzzing/honggfuzz/` |
| `winafl` | Windows binary-only (DynamoRIO coverage) | `offensive-tools/fuzzing/winafl/` |
| `jazzer` | Coverage-guided Java/JVM fuzz testing | `offensive-tools/fuzzing/jazzer/` |
| `boofuzz` | Stateful network protocol fuzzing | `offensive-tools/fuzzing/boofuzz/` |
| `restler` | REST API stateful dependency learning + fuzzing | `offensive-tools/fuzzing/restler/` |
| `schemathesis` | Schema-driven REST/GraphQL fuzzing | `offensive-tools/fuzzing/schemathesis/` |
| `radamsa` | Mutation-only; quick smoke probing when no harness exists | `offensive-tools/fuzzing/radamsa/` |

## Campaign lifecycle

1. **Target modeling and scoping**
  - Enumerate entrypoints, trust boundaries, and state transitions.
  - Pick 1-3 high-value paths first.
  - Define campaign KPIs: coverage growth, state depth, unique bug buckets.

2. **Oracle selection**
  - Choose what constitutes a bug signal: crash, sanitizer violation, timeout, invariant mismatch, differential mismatch.
  - Keep oracles explicit to reduce false positives.

3. **Harness/request-model quality gate**
  - Deterministic behavior, explicit resource limits, and clean reset between iterations.
  - No harness-originated failures.

4. **Corpus and mutation guidance**
  - Start with diverse valid seeds, then add malformed/edge seeds.
  - Deduplicate/minimize corpus before long runs.
  - Add dictionaries/token hints when parsing constraints are strong.
  - Treat corpus as a reusable campaign asset: seed, minimized, crash, regression, and negative corpora have different roles.

5. **Execution strategy**
  - Use diversified parallel instances (exploration-biased + bug-confirmation-biased).
  - Keep one high-throughput profile and one high-signal profile.

6. **Plateau response**
  - If progress stalls: improve model/seed quality first, then mutate strategy.
  - For stateful APIs/protocols: unlock producer/handshake reliability before consumer depth.

7. **Triage, minimization, and replay**
  - Bucket by signature + state phase.
  - Minimize one representative input/sequence per bucket.
  - Confirm reproducibility and capture full reproduction metadata.

8. **Feedback loop and reporting**
  - Feed findings into regression corpus.
  - Re-run focused campaigns after fixes.
  - Separate confirmed vulnerabilities from flaky/non-reproducible anomalies.

## Quality gates before scaling duration

- Reproducer exists for each high-priority bucket.
- Harness/model survives warmup at high iteration count.
- Resource limits (`time`, `memory`) are stable on seed corpus.
- Campaign output distinguishes exploitability candidate vs generic failure.
- Fuzzing is still the right technique: input reaches meaningful parser/state depth and failures are target-originated, not harness-originated.

## Required deliverables from the agent

When using this skill, the agent should output:

1. Scope + target model.
2. Oracle set and why each oracle is used.
3. Campaign plan (smoke, scale, plateau strategy).
4. Triage summary with minimized reproducers.
5. Regression plan for verified findings.

## Practical scenarios

### Scenario A: Image parser with source

- Build a narrow harness around decode path.
- Start with small valid corpus + a few malformed headers.
- Run one throughput profile and one sanitizer-rich profile.
- If blocked by strict integrity gates, handle them in fuzz-only build mode and document it.

### Scenario B: CRUD cloud API

- Run quick schema pass to identify dominant failure class.
- Fix undocumented responses and producer request failures before deep fuzzing.
- Enable stateful operation chaining so created IDs feed follow-up operations.
- Use replay traces to validate fixes without rerunning the full campaign.

### Scenario C: Stateful binary protocol daemon

- Model handshake/auth/data phases as graph transitions.
- Add monitor chain for alive check, crash synopsis, and restart.
- Prefer emulated/in-process transport where possible; real network only when required.
- Store per-test logs for deterministic replay.

## Anti-patterns

- Treating technique skill as command cheat-sheet.
- Running long fuzzing on unstable/non-deterministic harnesses.
- Ignoring dependency failures that prevent state depth.
- Scaling throughput before replayability is proven.
- Continuing after corpus/model improvements are exhausted and coverage remains flat.
- Mixing tool usage details into technique-level guidance.

## References

- [references/harness-writing.md](references/harness-writing.md)
- [references/binary-fuzzing.md](references/binary-fuzzing.md)
- [references/file-format-fuzzing.md](references/file-format-fuzzing.md)
- [references/network-remote-fuzzing.md](references/network-remote-fuzzing.md)
- [references/web-api-fuzzing.md](references/web-api-fuzzing.md)
- [references/oracle-and-signal-design.md](references/oracle-and-signal-design.md)
- [references/campaign-orchestration.md](references/campaign-orchestration.md)
- [references/corpus-management.md](references/corpus-management.md)
- [references/crash-triage-and-reproducibility.md](references/crash-triage-and-reproducibility.md)
