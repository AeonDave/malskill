---
name: garak
description: "garak — NVIDIA LLM vulnerability scanner: runs the widest catalog of known LLM attacks (prompt injection, jailbreak, data leak, hallucination, toxicity, encoding bypasses) against any model via HF/OpenAI-compatible/REST generators and produces scored HTML reports. Use for authorized LLM red-team scans."
license: MIT
compatibility: "Python 3.11+; Linux/macOS (Windows via WSL). v0.17.x current. API-based generators need keys; HuggingFace generators need GPU or patience."
metadata:
  author: AeonDave
  version: "1.0"
---

# garak

LLM vulnerability scanner modeled after vulnerability scanners like Metasploit/Nmap: a catalog of **probes** (attack families) run against a **generator** (the model endpoint), each attempt scored by a **detector**, results aggregated into a report. Model-agnostic — if it speaks text, garak can probe it.

## When to use

- Authorized red-team scan of an LLM endpoint or local model
- Baseline the attack surface of a model before/after guardrail changes
- Systematic coverage: garak's probe catalog is the widest public one — use it where manual testing would miss families

## Core workflow

```bash
# Install
pip install garak

# HuggingFace local model (current flags: --target_type/--target_name; --model_* are deprecated aliases)
garak --target_type huggingface --target_name gpt2 --probes encoding

# OpenAI-compatible endpoint (ollama, vLLM, LiteLLM proxy, OpenAI itself)
garak --model_type openai --model_name <model-id> \
      --generator_option_file openai.config --probes promptinject

# Scan everything (expensive — see best practice)
garak --model_type openai --model_name gpt-4o-mini --probes all

# Narrow to a family + report analysis
garak --model_type openai --model_name gpt-4o-mini \
      --probes dan,promptinject,leakreplay
```

Reports land in `garak_runs/` — HTML report (v0.14+ redesigned) + JSONL per attempt.

## Probe families (the vocabulary)

- `promptinject` — Agency Enterprise PromptInject compliance
- `dan` — DAN jailbreak variants (Do Anything Now)
- `xss` — model-generated cross-site-scripting / data exfiltration
- `leakreplay` — training-data replay / verbatim leakage
- `encoding` — injection via encodings (base64, rot13, morse)
- `malwaregen` — malicious code generation attempts
- `snowball` — snowballed hallucination (wrong answers to questions too hard to process)
- `continuation`, `lmrc`, `packagehallucination`, `divergence`, `atkgen` (adaptive red-team attack generation), `goodside` (Riley Goodside attacks), `badchars` (imperceptible Unicode perturbations), `glitch` (glitch-token instability)

List live probes: `garak --list_probes`. Config via YAML (v0.14+ also JSON) — `--config garak_config.yaml` for generator/probe/detector composition. Note: `--probes` is a deprecated alias for the unified `--spec` selector.

## Best practice

- **Never start with `--probes all` on paid APIs**: the full catalog is thousands of generations. Select families per engagement goal, or run `all` against a local target (ollama/vLLM) first to scope, then targeted runs against the real endpoint.
- Set `--generations N` (generations per prompt, default 5) consciously — quality of findings vs token cost.
- Analyze the HTML report's **_defect rate_ per probe**; follow up misses manually (garak finds the entry point, the follow-up is your tradecraft).
- Pair with `PyRIT` for multi-turn orchestrated attacks (garak probes are mostly single-shot); pair with `promptfoo` for CI-regression of fixes.
- Authorized targets only: garak burns tokens and sends hostile payloads — pointing it at a third-party API you don't own is abuse.

## Gotchas

- Python 3.11+ floor; Windows unsupported natively (WSL).
- HuggingFace generators download model weights — disk/time cost; prefer endpoint generators for remote targets.
- Detectors matter as much as probes: some probes rely on string matching, others on a judge model — read the report's detector column before declaring a defense effective.
- Custom probes: subclass `garak.probes.base.Probe` in a plugin path (`--plugin_dir`) — keep engagement-specific probes out of the site-packages install.

## References

- Upstream: [NVIDIA/garak](https://github.com/NVIDIA/garak) (v0.17.x line; reports redesigned in v0.14)
- Companions in this repo: `pyrit` (orchestrated multi-turn), `promptfoo` (eval/CI), `ollama` (local targets), technique-side: `offensive-ctf/ai-ml-ctf/references/llm-attacks.md`
