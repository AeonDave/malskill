---
name: ollama
description: "Ollama — pull, run, and serve open models through its native or OpenAI-compatible API. Use for local security-lab agent backends, garak/PyRIT targets, attacker models, and offline analysis with local execution verified."
license: MIT
compatibility: "Linux/macOS/Windows; pin the installed Ollama version and supported model/backend. Native API on :11434/api and OpenAI-compatible API on :11434/v1; GPU support depends on platform/backend."
metadata:
  author: AeonDave
  version: "1.1"
---

# Ollama

Use a locally executed model for security-lab agent backends, evaluation targets, and offline analysis. A localhost endpoint alone does not establish local-only execution: Ollama also supports cloud models and features. For local-only work, set `OLLAMA_NO_CLOUD=1`, restart the managed service, verify the effective setting and selected local model, and check client-side logging/forwarding. See the [official local-only configuration](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).

## Core workflow

```bash
# Install (Linux) / brew / winget
curl -fsSL https://ollama.com/install.sh | sh

# Pull and run a model
ollama pull llama3.3            # or qwen2.5-coder, mistral-small, deepseek-r1
ollama run llama3.3 "explain this binary layout"

# Serve (default: listens on 127.0.0.1:11434)
ollama serve

# OpenAI-compatible endpoint — drop-in for garak/PyRIT/promptfoo/LangChain
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.3","messages":[{"role":"user","content":"hi"}]}'

# Model management
ollama list                     # local models
ollama ps                       # loaded models + VRAM
ollama rm model                 # free disk
ollama show llama3.3            # architecture, context length, quantization
```

## Lab patterns

| Pattern | Recipe |
|---|---|
| **garak target** | `garak --model_type openai --model_name llama3.3 --generator_option_file cfg` pointing `base_url` at `http://localhost:11434/v1/` — full probe catalog with zero token cost |
| **PyRIT attacker model** | Point the RedTeamingOrchestrator's attacker/scorer at the local `/v1` endpoint — adaptive campaigns in airgapped labs |
| **Agent backend** | LangChain `ChatOllama` / OpenAI-compat base_url — agent development without cloud spend or data egress |
| **Custom model** | `Modelfile` (`FROM llama3.3` + `SYSTEM "..."` + params) → `ollama create` — bake system prompts/personas into reusable local models |

## Best practice

- **Size the complete workload**: weights, KV/state, temporary buffers, and concurrent requests share memory. Inspect `ollama ps` and measure the effective placement; CPU offload and quantization have workload-specific speed/quality costs.
- **Context window**: inspect the installed runtime's effective context and the model limit; configure `num_ctx` through the supported native options or Modelfile. Include template and output tokens, and test for rejection/truncation.
- Keep `OLLAMA_HOST=127.0.0.1` (default): the API has **no authentication** — never bind it to 0.0.0.0 on a networked host.
- For reproducible lab runs, record the resolved model digest, Modelfile/template, runtime version, and launch settings. A descriptive tag is not an immutable artifact identity.

## Measure native execution

The final native API chunk (`done: true`) reports `load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, and `eval_duration`; durations are nanoseconds. With positive durations, compute engine prompt rate as `prompt_eval_count * 1e9 / prompt_eval_duration` and engine generation rate as `eval_count * 1e9 / eval_duration`. Keep cache state and counts explicit; a missing/zero duration is not infinite throughput.

These [native usage metrics](https://docs.ollama.com/api/usage) do not include the same boundary as client TTFT or end-to-end latency. For cold/warm runs, controlled comparisons, concurrency, memory, and quality gates, load [inference-optimization](../inference-optimization/SKILL.md).

## Gotchas

- The OpenAI-compat endpoint is **close but not identical**: tool-calling/streaming quirks vary by model — test the exact call shape your tooling makes before a long run.
- Quantization can change task quality and runtime kernels. Compare candidate formats on the actual security task and memory/latency constraints instead of choosing by bit count alone.
- First token latency after idle: models unload after a TTL; a burst of timeouts is usually the model reloading, not a failure.
- Vision/multimodal models need the specific vision-capable tags and the API image format — check per model.

## References

- Upstream: [ollama](https://github.com/ollama/ollama); [runtime FAQ](https://docs.ollama.com/faq); [native API metrics](https://docs.ollama.com/api/usage)
- Consumers in repo: `garak`, `pyrit`, `promptfoo` (providers), `langchain-py` (ChatOllama)
