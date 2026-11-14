---
name: ollama
description: "Ollama — local LLM runtime: pull/run/openai-compatible serve of open models on localhost (no data leaves the host). Use as the offline lab LLM for agents, garak/PyRIT targets, red-team attacker models, and airgapped analysis workflows."
license: MIT
compatibility: "Linux/macOS/Windows (v0.40.x current); OpenAI-compatible API on :11434/v1; GPU optional (CUDA/Metal/Vulkan), CPU fallback works for small models."
metadata:
  author: AeonDave
  version: "1.0"
---

# Ollama

Local LLM runtime: one binary, one API, models pulled like containers. In security labs it is the **data-never-leaves-the-host** LLM: agent backends, garak/PyRIT targets and attacker models, and offline analysis all point at `localhost:11434` instead of paid cloud APIs.

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

- **Size to VRAM**: a model needs roughly its file size in VRAM; if it spills to CPU/RAM, generation slows 10-50×. `ollama ps` shows the load state — prefer quantized variants (Q4_K_M is the sweet spot) for lab work.
- **Context window**: default context is small (2k-8k per model); raise per-request with `num_ctx` or in the Modelfile — truncation silently degrades long-prompt tasks.
- Keep `OLLAMA_HOST=127.0.0.1` (default): the API has **no authentication** — never bind it to 0.0.0.0 on a networked host.
- For reproducible lab runs, pin model tags (`llama3.3:70b-instruct-q4_K_M`) — `latest` moves underneath you.

## Gotchas

- The OpenAI-compat endpoint is **close but not identical**: tool-calling/streaming quirks vary by model — test the exact call shape your tooling makes before a long run.
- Quantization loss is real: a Q4 model is noticeably weaker on nuanced tasks than FP16 — use the largest quant that fits VRAM.
- First token latency after idle: models unload after a TTL; a burst of timeouts is usually the model reloading, not a failure.
- Vision/multimodal models need the specific vision-capable tags and the API image format — check per model.

## References

- Upstream: [ollama](https://github.com/ollama/ollama) (v0.40.x line)
- Consumers in repo: `garak`, `pyrit`, `promptfoo` (providers), `langchain-py` (ChatOllama)
