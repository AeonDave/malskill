# Model Tiering & Cost Routing

How to control cost in an OpenCode team, given that the model is fixed per agent.

## The constraint (read first)

OpenCode resolves a subagent's model from its **pre-existing agent definition**. The `task` tool's parameters are `description`, `prompt`, `subagent_type` — **no `model`**. So a primary cannot choose a model per dispatch based on task difficulty at runtime.

Consequence: **cost routing = routing to the agent whose pinned model fits the job.** You design tiers at config time; the supervisor "selects a model" only indirectly, by choosing which agent to dispatch.

## The three tiers

| Tier | Who | Model policy |
|---|---|---|
| Brain | the supervisor | Strongest available. Often best to **leave `model` unset** so it inherits the model the user picks with `/models` — run the brain on whatever top model is selected. |
| Specialist | domain subagents | A capable mid model with strong tool-calling. These do the real reasoning + tool use; do not downgrade to free models. |
| Utility | helper subagents | Free or very cheap models for token-heavy, low-judgement work. |

Routing rules the supervisor should follow:
- Push trivial/bulk work (summaries, translation, log/JSON/XML parsing, public doc lookup, boilerplate) **down** to a utility agent.
- Keep domain reasoning with specialists and planning/synthesis with the brain.
- Tighter packet = fewer tokens; one well-scoped worker beats many vague ones.

## Always-working models: inheritance as the native "fallback"

OpenCode has **no native model-fallback list** (you cannot write `model: [a, b, c]`; it is an open feature request). The supported way to guarantee a subagent always has a working model is **inheritance**: omit the `model` field and the subagent runs on the model of the primary that invoked it.

This turns the supervisor's model into a single dial for the whole team:

- Leave the **specialists' `model` unset** → they inherit the supervisor. Whatever model you select on the supervisor with `/models` (one you have quota on), every specialist follows. A metered model running out then never silently fails a dispatch — switch the supervisor and the team follows, even mid-session (new dispatches use the new model).
- Trade-off: specialist quality tracks the supervisor's model. Run the supervisor on a strong model when you have quota; on a free/cheap one when you don't — the team keeps working either way.
- To dedicate a stronger (or just different) model to **one** specialist, re-add a `model:` line to that single agent; it then stops inheriting. Use this only where the cost/quality delta is worth a pinned, separately-billed model — and remember a metered pin can exhaust and fail.
- Keep **utility** agents pinned to free/cheap models regardless: they should stay cheap and not track an expensive supervisor model.

Symptom that you need this: a dispatched subagent returns empty/failed with a quota or "exceeded" error while the supervisor still works — its pinned model ran out. Switch that agent to inherit (remove `model`).

## OpenCode Zen models (`opencode/<id>`)

Zen is OpenCode's curated gateway. Model id format in config is `opencode/<id>`. Catalogs change — verify with `opencode models` or `/models`. As of writing, representative entries:

- **Free tier** (great for utility agents): `big-pickle`, `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`. Availability is time-limited.
- **Cheap paid, zero-retention** (good fallbacks): `gpt-5-nano` (~$0.05/M in), `deepseek-v4-flash` (~$0.14/M), `gpt-5.4-nano` (~$0.20/M), `claude-haiku-4-5` (~$1.00/M).
- **Capable mid** (specialists): e.g. `claude-sonnet-4-6`, `gpt-5.4`.
- **Top reasoning** (brain): e.g. `claude-opus-4-x`, `gpt-5.5`.

Other providers work too — id is always `provider/model-id` (e.g. `github-copilot/gpt-5.4`, `anthropic/claude-...`). Keep a team on one provider when you want flat-rate/subscription billing to cover the specialists.

## Privacy caveat for free models (important)

Free Zen models **may log or train on submitted data**. Never route sensitive engagement data (credentials, private keys, tokens, PII, client identifiers, raw memory/disk/PCAP/exploit artifacts) to a free-tier utility agent. Mitigations:
- Have the supervisor redact/generalize before delegating to a free agent.
- For sensitive parsing, route to a **paid zero-retention** model (e.g. `opencode/deepseek-v4-flash`) or to a specialist, not the free utility.
- Put this rule in the supervisor prompt and in each free utility's prompt so it is enforced behaviorally.

## Choosing per agent

1. Brain: leave unset (inherit `/models`) unless you want it fixed.
2. Specialists: pick one capable model; only split into `x` / `x-heavy` variants if you genuinely have a mix of trivial and hard work in that domain and the cost delta justifies a second agent.
3. Utilities: free models; keep a cheap paid fallback noted in case a free model is deprecated.

## Roadmap: dynamic model selection (not shipped)

Track these if you want true per-task model choice:
- **#6651** — `model_tier` (quick/standard/advanced enum) on the Task tool, with config-mapped tiers. PR open, awaiting maintainer review; maintainers prefer the tier abstraction over a raw model id (training-cutoff, model-proliferation, and validation concerns).
- **#26536 / #17595** — a raw `model` parameter on the Task tool; closed as not-planned.

If `model_tier` ships, you can collapse `x` / `x-heavy` duplicates into a single agent with `model_tiers` and let the supervisor pass a tier per dispatch. Until then, the multiple-agents-per-tier routing in this skill is the supported way.
