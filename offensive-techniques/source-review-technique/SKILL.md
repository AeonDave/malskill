---
name: source-review-technique
description: Hybrid AI/Deterministic SAST methodology for discovering zero-day vulnerabilities in source code. Orchestrates structural search with AI-driven data flow and sink validation.
---

# source-review-technique

**Goal**: Discover zero-day vulnerabilities in source code by combining deterministic structural search with LLM-assisted data flow analysis.

## When this technique applies

- A target's source code is available (open source, leaked, or decompiled/decompressed).
- You need to track tainted inputs to sensitive sinks (SAST).
- Pure regex/search is too noisy, but full manual review is too slow.

## The Hybrid Workflow

Modern SAST effectively bridges static tools with LLMs. The LLM acts as the triage and data-flow validator, while tools like `semgrep` or `grep` map the initial graph.

### 1. Sink and Source Mapping (Deterministic)

Do not ask the LLM to "find bugs" across thousands of lines at once. It will hallucinate.
1. **Identify Sources**: HTTP requests, CLI args, file reads, database returns, IPC.
2. **Identify Sinks**: `exec`, `system`, `query`, `eval`, `deserialize`, `UnsafeCell`, memory allocators.
3. **Map**: Use `ripgrep`/`semgrep`/`opengrep` (or the IDE's code-usage search when available) to enumerate every invocation of the sinks.

### 2. Taint Evaluation (LLM-Assisted)

For each high-value sink found:
1. Traverse backward to find where the arguments originated.
2. Verify if the arguments are controllable by an attacker (the Source).
3. If the path crosses file boundaries (inter-procedural), explicitly read those files.
4. **Context enrichment**: Search locally for validators, sanitizers, or middleware.

### 3. Verification & Evidence

- Do not report a vulnerability unless you can trace a continuous line from Source to Sink.
- Document the exact file, line number, and variables involved at each step.
- Identify what conditions must be bypassed to reach the sink.

## Quality Gates

- **No generic bug reports**: If the finding is "Xss vulnerability because `print` is used", reject it unless you can prove the input is strictly user-controlled and unescaped.
- **Dependency boundaries**: If the sink is in a third-party framework, check how the target application actually invokes that framework instance.
- **Evidence format**: Produce a markdown file detailing the exact Attack Path, required preconditions, and the affected code snippet blocks. 

## References

- [references/bug-classes.md](references/bug-classes.md) — Targeted sink patterns for common architectures (e.g. Deserialization, Path Traversal, Memory Corruption).
