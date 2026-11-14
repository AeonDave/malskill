---
name: interpretability
description: "Explain and locate why a model produces an output, without editing it: feature attribution for classic-ML/DL classifiers (SHAP, LIME, Captum) and mechanistic analysis of transformer LLMs (TransformerLens activation cache/hooks, logit lens, activation patching, sparse autoencoders). Use to audit a decision, find the feature a backdoor trigger relies on, or locate where a behavior/refusal lives in the weights."
license: MIT
compatibility: "Python 3.10+ (shap >=0.54 needs 3.12+). Attribution: shap, lime, captum. LLM internals: transformer-lens 4.x (TransformerBridge), nnsight, sae-lens. GPU helps for large-model activation work."
metadata:
  author: AeonDave
  version: "1.0"
  category: ai
---

# interpretability

Understand *why* a model behaves the way it does — read its internal signals and causally test them. This skill **explains and locates**; to *edit* the behavior you find use [`abliteration`](../abliteration/SKILL.md), and to scan an artifact for payloads use [`model-scanning`](../model-scanning/SKILL.md). Two toolchains, by model type.

## Feature attribution — classic ML and DL classifiers

Pick the explainer by model type; exact methods beat the model-agnostic fallback when available.

| Model | Explainer |
|---|---|
| Tree ensembles (XGBoost, LightGBM, CatBoost, sklearn trees) | `shap.TreeExplainer` (exact, fast; `GPUTreeExplainer` on GPU) |
| Linear | `shap.LinearExplainer` |
| PyTorch / TF deep nets | `shap.DeepExplainer` / `GradientExplainer`, or **Captum** (`IntegratedGradients`, `DeepLift`, `GradientShap`, `Saliency`, layer/neuron attribution) |
| Any black box | `shap.KernelExplainer` / `shap.Explainer` (auto-dispatch; also wraps HF NLP pipelines), or **LIME** |

```python
import shap
explainer = shap.TreeExplainer(model)       # XGBoost/LightGBM/sklearn tree
sv = explainer.shap_values(X)               # per-feature contributions; sums to prediction - expected_value
shap.summary_plot(sv, X)                     # global importance; shap.plots.waterfall for one row
```

Security use: audit a classifier's decision in an assessment; **find the feature a backdoor/trojan relies on** — attribution concentrates on the trigger when a poisoned input flips the label; surface spurious correlations the model learned.

## Mechanistic analysis — transformer LLMs

TransformerLens exposes every internal activation and lets you edit it mid-forward-pass.

```python
from transformer_lens.model_bridge import TransformerBridge   # TL 4.x path
bridge = TransformerBridge.boot_transformers("gpt2", device="cpu")
logits, cache = bridge.run_with_cache("The Eiffel Tower is in")
cache["blocks.5.hook_resid_post"]      # residual stream at layer 5
cache["blocks.8.attn.hook_pattern"]    # attention pattern at layer 8
```

`HookedTransformer.from_pretrained(...)` is the pre-4.0 API seen in most tutorials; it was **removed in TransformerLens 4.0** — use `TransformerBridge`, and call `bridge.enable_compatibility_mode()` for HookedTransformer numerics. Bound cache memory with `run_with_cache(..., names_filter=lambda n: "resid_pre" in n)`.

| Technique | Question | Evidence |
|---|---|---|
| **Logit lens** | what does the model predict at layer *l*? (project residual → unembed) | observation |
| **Activation patching** | is this activation a *cause* of the answer? (overwrite from a clean run) | intervention |
| **Path patching** | how does information flow head→head? | circuit |

Patch with `bridge.run_with_hooks(tokens, fwd_hooks=[(name, fn)])`: a logit change after overwriting one activation is causal evidence. **SAEs** (`sae-lens`, pre-trained SAEs + Neuronpedia) decompose polysemantic activations into sparser, more monosemantic features. `nnsight` is an alternative tracing API over HF models.

Security use: **locate the refusal direction** (hand off to [`abliteration`](../abliteration/SKILL.md)); find where a secret or behavior is stored; **detect a backdoor trigger** via anomalous activations on trigger tokens; explain a jailbreak by patching the activation that flips refusal→comply; probe for memorized data.

## Observation vs causation (the core discipline)

- Logit lens, attention patterns, and SAE features are **observational** — correlation, not cause. A causal claim needs an **intervention** (activation/path patching) with controls: matched token counts between clean/corrupt prompts and a sane baseline.
- **SAE reconstruction error is non-trivial** — a feature is an interpretive hypothesis, not ground truth; validate against output effects.
- Attribution values depend on the background/baseline dataset and the explainer — report them, and prefer exact explainers (Tree/Linear) over approximations when the model allows.

## References

- Attribution: [shap/shap](https://github.com/shap/shap), [pytorch/captum](https://github.com/pytorch/captum), [LIME](https://github.com/marcotcr/lime)
- LLM internals: [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) (v4.x), [SAELens](https://github.com/decoderesearch/SAELens), [nnsight](https://github.com/ndif-team/nnsight), [Neuronpedia](https://www.neuronpedia.org)
- Companions: [`abliteration`](../abliteration/SKILL.md) (edit the direction you locate), [`transformers`](../transformers/SKILL.md) (load), [`scikit-learn`](../scikit-learn/SKILL.md) / [`pytorch`](../pytorch/SKILL.md) (artifacts), [`adversarial-robustness-toolbox`](../adversarial-robustness-toolbox/SKILL.md) and [model-attacks](../../offensive-ctf/ai-ml-ctf/references/model-attacks.md) (backdoor/attack side)
