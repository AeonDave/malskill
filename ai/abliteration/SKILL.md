---
name: abliteration
description: "Training-free modification of open-weight LLMs by editing the residual stream: abliteration (refusal-direction ablation) to remove refusals, inference-time activation steering, permanent weight orthogonalization, and automated optimizers (e.g. Heretic). Use to uncensor or behavior-edit a local model you can run, without retraining, and to evaluate capability preservation."
license: MIT
compatibility: "Python 3.10+; transformers + torch. Weight edits need full-precision (not 4/8-bit) weights to write back; direction extraction can run quantized. GPU recommended. Optional: TransformerLens, Optuna, mergekit."
metadata:
  author: AeonDave
  version: "1.0"
  category: ai
---

# abliteration

Refusal (and other aligned behaviors) in transformer LLMs is mediated by low-dimensional directions in the residual stream (Arditi et al. 2024, across 13 chat models up to 72B). Editing those directions changes behavior **without training** — no dataset, no gradient steps, cheap compute, and permanent weights. This is the training-free counterpart to [`model-finetuning`](../model-finetuning/SKILL.md). Authorized/lab use only: it deliberately strips safety alignment from a model.

## The core technique

**1. Extract the direction (difference-in-means).** Run the model on a set of "harmful" and a set of "harmless" instruction prompts; cache the last-token residual-stream activations per layer. For each layer, the candidate direction is the normalized mean difference:

```
r_layer = normalize( mean(harmful_residuals[layer]) - mean(harmless_residuals[layer]) )
```

Sweep candidate layers (best signal is usually mid to late-middle) and pick the one that most reduces refusals while keeping output fluent.

**2. Apply it**, in one of two modes:

| Mode | Operation | Property |
|---|---|---|
| Inference-time steering | subtract the projection at each layer: `h' = h - (h·r̂) r̂` | reversible, in-memory hook; no file change; useful for measurement |
| Weight orthogonalization | for every matrix writing to the residual stream (attention `o_proj`, MLP `down_proj`, embeddings): `W' = W - r̂ r̂ᵀ W` | permanent; produces an abliterated checkpoint; needs full-precision weights |

Orthogonalization makes the model unable to *write* the direction at all; steering just cancels it at runtime.

## Applying it with tooling

The method above is small enough to implement directly against a `transformers` model, but reuse an existing implementation for coverage and parameter search:

- **Manual / single-pass**: Maxime Labonne's abliteration notebook (canonical walkthrough), `FailSpy/abliterator` (TransformerLens hooks — limited to architectures TransformerLens supports), `NousResearch/llm-abliteration` (`sharded_ablate.py`, no TransformerLens, `--projected`/`--normpreserve`, quantized measurement but full-weight ablation), `ErisForge`.
- **Automated optimization**: tools wrap directional ablation in a hyperparameter search instead of hand-picking the layer/strength. Example — **Heretic** (`p-e-w/heretic`, AGPL-3.0): `pip install -U heretic-llm` then `heretic <hf-model-id>`. It orthogonalizes attention out-projection and MLP down-projection with a per-layer ablation-weight kernel and a float (interpolated) direction index, and uses an Optuna TPE search to **co-minimize refusal rate and KL divergence from the original model** — automating the fluency/compliance tradeoff humans tuned by hand.

## Beyond censorship

The same residual-direction edit steers other contrastive behaviors, not only refusals: define the two prompt sets around the trait you want to push or suppress (e.g. verbosity, sycophancy, "slop", emotional tone). Heretic ships configs for several of these; the general lever is the contrastive prompt pair, not the specific trait.

## Evaluate — reduced refusals ≠ preserved capability

A model that stops refusing may also have degraded. Always measure three things on the edited model, not just the refusal rate:

- **Refusal rate** on held-out harmful prompts (did it work).
- **KL divergence** from the original on harmless prompts (how much behavior drifted; 0 = identical).
- **Task benchmarks** (MMLU, GSM8K). Mathematical reasoning degrades most under abliteration — an independent comparison (Young, arXiv:2512.13655, 2025) measured GSM8K shifts from +1.51 to −18.81 points across tools, with single-pass tools sometimes preserving math better than optimized ones.

If capability loss is unacceptable, **merge** the abliterated model with the base using `mergekit` to recover quality while keeping most of the refusal reduction.

## Related training-free edits

- **Knowledge editing** (locate-then-edit) changes *facts* rather than refusal behavior: `ROME` rewrites a single MLP layer to alter one factual association; `MEMIT` mass-edits many facts across MLP layers. Both run via `EasyEdit`. Offensive relevance: implant targeted false facts or trigger associations into open weights.
- **Unlearning** removes knowledge/capabilities with training (NPO/RMU) — the training-based counterpart to this training-free edit: see [`model-finetuning`](../model-finetuning/SKILL.md).
- **Model merging** recombines an edited model with others in weight space — e.g. merge the abliterated model with its base to recover capability while keeping most of the refusal reduction. See [`model-merging`](../model-merging/SKILL.md).

## Gotchas

- Refusal is not always a single clean direction; concept-cone / multi-direction variants exist, and a mid-layer choice that kills refusals on one prompt set can miss another — validate on diverse prompts.
- Edit full-precision weights; a 4/8-bit model is fine for *measuring* the direction but you cannot cleanly write orthogonalized weights back into quantized tensors.
- An abliterated model is a modified artifact — record the base model, tool, version, and parameters so the edit is reproducible and auditable.

## References

- Method: Arditi et al. 2024, *Refusal in LLMs is mediated by a single direction*; eval caveat: Young, [arXiv:2512.13655](https://arxiv.org/abs/2512.13655)
- Tools: [Heretic](https://github.com/p-e-w/heretic) · [FailSpy/abliterator](https://github.com/FailSpy/abliterator) · [NousResearch/llm-abliteration](https://github.com/NousResearch/llm-abliteration) · [mergekit](https://github.com/arcee-ai/mergekit)
- Companions: [`transformers`](../transformers/SKILL.md), [`model-finetuning`](../model-finetuning/SKILL.md), [`model-merging`](../model-merging/SKILL.md), [`ollama`](../ollama/SKILL.md) (serve the result); offensive context: [`llm-technique`](../../offensive-techniques/llm-technique/SKILL.md)
