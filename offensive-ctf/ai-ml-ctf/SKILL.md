---
name: ai-ml-ctf
description: "Challenge-solving methodology for AI and machine-learning challenge solving. Integrates web-exploit-technique, vuln-search-technique, reversing-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use when working on AI and machine-learning challenge solving tasks involving model files, checkpoints, embeddings, LoRA adapters, classifiers, or model APIs."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# AI/ML CTF

Goal: solve AI and machine-learning challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- model files, checkpoints, embeddings, LoRA adapters, classifiers, or model APIs
- adversarial examples, model inversion, extraction, poisoning, membership inference, or prompt-injection tasks
- LLM tool-use, RAG, context, or guardrail bypass puzzles in authorized challenge environments

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `web-exploit-technique`
- `vuln-search-technique`
- `reversing-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `coding/python-patterns`
- `coding/python-testing`
- `ai/langchain-py`
- `offensive-tools/web/jwt-tool`
- `offensive-tools/network/mitmproxy`
- `offensive-tools/rev/frida`
- `offensive-tools/rev/ghidra`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Classify artifact first: model checkpoint, serialized pipeline, REST endpoint, LLM application, or feature-extraction code.
- Use differential queries and local reproduction before assuming a model weakness.
- For LLM tasks, separate prompt-layer bypass from tool/RAG injection and validate with controlled probes.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve source coverage: every imported file is mapped in `references/source-coverage.md` and available in `references/`.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/adversarial-ml.md](references/adversarial-ml.md) — preserved, debrandized imported technique material.
- [references/llm-attacks.md](references/llm-attacks.md) — preserved, debrandized imported technique material.
- [references/model-attacks.md](references/model-attacks.md) — preserved, debrandized imported technique material.
