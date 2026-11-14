---
name: litellm
description: "LiteLLM — unified LLM gateway/proxy: one OpenAI-shaped API over 100+ providers with virtual keys, budgets, routing, and per-team spend tracking. Use both as lab utility (provider abstraction) and as an engagement target (its proxy surface has a CVE history) — with strict supply-chain verification."
license: MIT
compatibility: "Python 3.9+; pip/litellm proxy (v1.108.x LTS current). Node not required. ⚠️ SUPPLY-CHAIN: malicious v1.107.0 pushed to PyPI/Docker on 2026-10-21 — pin and verify before install."
metadata:
  author: AeonDave
  version: "1.0"
---

# LiteLLM

Unified LLM gateway: one OpenAI-shaped API over every provider (OpenAI, Azure, Anthropic, Bedrock, Vertex, ollama…), with the **Proxy Server** adding virtual keys, per-key budgets, routing/fallback, and spend tracking. Dual relevance for security work: standard lab utility for provider abstraction, and a recurring **engagement target** — its proxy surface has a documented CVE history and a recent supply-chain incident.

## Known-bad release — pin before installing

`litellm==1.107.0` on PyPI/Docker is **malicious** (release-pipeline compromise, Oct 2026): do not install; treat any host that pulled it as compromised (the payload targeted runtime secrets — rotate them). Required practice for every install: pin the exact LTS version, verify the hash against the GitHub release attestation, and apply the general rule from `dependency-discipline` — a correctly-signed release is not a trusted release.

## Core workflow

```bash
# SDK: one API, any provider
from litellm import completion
r = completion(model="anthropic/claude-sonnet-4-5",
               messages=[{"role":"user","content":"hi"}])   # api_base override → ollama etc.

# Proxy: config-driven gateway
cat > config.yaml <<'YAML'
model_list:
  - model_name: gpt-4o-mini
    litellm_params: { model: openai/gpt-4o-mini, api_key: os.environ/OPENAI_API_KEY }
  - model_name: local-llama
    litellm_params: { model: ollama/llama3.3, api_base: http://localhost:11434 }
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
YAML
litellm --config config.yaml --port 4000

# Virtual keys with budgets (issued via /key/generate or admin UI)
curl -X POST localhost:4000/key/generate -H "Authorization: Bearer <master>" \
  -d '{"models":["local-llama"],"max_budget":10}'
```

## Security-relevant surface (when it is the target)

- **CVE history on the proxy**: SSRF via model params, auth-bypass classes on admin endpoints, prompt-injection through proxy logs — enumerate current CVEs against the deployed version before testing.
- **Master key + virtual keys**: the master key mints keys; find a leaked virtual key and you inherit its budget/model scope — check key scoping configuration.
- **Callback/logging hooks**: request bodies (often sensitive) flow to configured log/callback endpoints — an SSRF or misconfigured callback is a credential-exfil channel.
- Hardening baseline: master key only from env, `general_settings.alerting` on, disable unused routes, never expose the proxy without the auth layer.

## Best practice

- Use **LTS tags** for deployments (mainline moves fast, LTS gets backports); verify against the GitHub release, not PyPI alone.
- In labs, prefer pointing tools at `ollama` directly when there is only one provider — LiteLLM pays off with multi-provider routing/fallback, not single-model setups.
- Budgets are enforcement: set `max_budget` per virtual key so a runaway agent loop cannot burn the account.

## Gotchas

- Config YAML supports env interpolation (`os.environ/VAR`) — secrets in the file itself end up in backups and git.
- Provider strings are namespaced (`openai/`, `anthropic/`, `ollama/`, `azure/`) — the wrong prefix silently falls back to defaults with confusing errors.
- Router fallbacks can mask provider outages during testing — log `litellm_call_id` to know which backend actually served a request.

## References

- Upstream: [BerriAI/litellm](https://github.com/BerriAI/litellm) — v1.108.x LTS; hash-verify installs
- Consumers: `ollama` (backend), `promptfoo`/`garak`/`pyrit` (point at the proxy as a provider)
