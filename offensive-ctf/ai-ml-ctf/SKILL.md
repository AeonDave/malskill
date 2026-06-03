---
name: ai-ml-ctf
description: "Lab/CTF: AI/ML challenges; model artifacts, checkpoints, embeddings, LoRA, classifiers, model APIs, RAG/tool-use, adversarial ML."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# AI/ML CTF

Goal: solve AI and machine-learning CTF tasks with artifact-first triage, controlled experiments, and reproducible evidence.

## When this skill applies

- model files, checkpoints, embeddings, LoRA adapters, classifiers, serialized pipelines, feature extractors, or model APIs
- adversarial examples, model inversion, extraction, poisoning, membership inference, or prompt-injection tasks
- LLM tool-use, RAG, context, or guardrail bypass puzzles in authorized challenge environments

## Operating model

1. Classify the dominant lane: model artifact, training data, feature pipeline, inference API, LLM app, RAG/tool flow, or embedded model.
2. Define the oracle: target class, recovered secret, membership decision, extracted weights, prompt leak, tool action, or checker response.
3. Load the closest methodology before selecting tools.
4. Load only the reference matching the lane; do not run every attack family by habit.
5. Build a controlled local reproduction or differential query harness before claiming a model weakness.
6. Record parameters, seeds, prompts, inputs, outputs, confidence, and exact validation proof.

## Technique integration

Primary methodology to load:

- `web-exploit-technique`
- `llm-technique`
- `vuln-search-technique`
- `reversing-technique`
- `python-patterns`
- `python-testing`

Use these as decision engines. This skill adds challenge-oriented triage, experiment design, and reference routing for AI/ML tasks.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `python-patterns`
- `python-testing`
- `langchain-py`
- `pytorch`
- `keras`
- `scikit-learn`
- `vec2text`
- `jwt-tool`
- `mitmproxy`
- `frida`
- `ghidra`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Evidence patterns

- Favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every attack family by habit.
- End with a replayable proof: recovered secret, local verification, model output delta, extracted artifact, or correlated evidence chain.

## Category-specific quick pivots

- Classify artifact first: model checkpoint, serialized pipeline, REST endpoint, LLM application, or feature-extraction code.
- Use differential queries and local reproduction before assuming a model weakness.
- For LLM tasks, separate prompt-layer bypass from tool/RAG injection and validate with controlled probes.
- For checkpoints, inspect format, framework, architecture, tensor names, metadata, and unsafe deserialization risk before loading.
- For adversarial examples, pin preprocessing, normalization, epsilon/constraint, target class, and success metric.
- For extraction/inversion, record query budget, input basis, confidence/logit access, and surrogate validation.
- For LoRA/adapter tasks, inspect adapter config, rank, alpha, target modules, merge math, and prompt/template assumptions.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Keep challenge/platform/competition names out of notes and generated reports.
- Never load untrusted pickle/joblib checkpoints in the main environment; inspect metadata or load in a throwaway sandbox when required.
- Distinguish stochastic variance from a real exploit by repeating with fixed seeds or multiple trials.

## Resources

- [references/adversarial-ml.md](references/adversarial-ml.md) — adversarial examples, patch attacks, evasion, poisoning, and backdoor detection workflows.
- [references/llm-attacks.md](references/llm-attacks.md) — prompt injection, jailbreaks, token smuggling, context manipulation, tool-use, and RAG/task-flow attacks.
- [references/model-attacks.md](references/model-attacks.md) — model inversion, extraction, membership inference, LoRA merging, checkpoint arithmetic, and encoder collisions.
