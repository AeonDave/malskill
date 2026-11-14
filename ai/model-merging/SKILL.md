---
name: model-merging
description: "Combine or edit open-weight models in weight space without training, using mergekit: SLERP, TIES, DARE, task arithmetic, passthrough/frankenmerge, and MoE assembly. Use to blend capabilities, build model soups, recover quality after abliteration, or add/subtract behaviors via task vectors on same-architecture checkpoints."
license: MIT
compatibility: "Python 3.10+; pip install mergekit; CLI mergekit-yaml. Runs out-of-core on CPU (high RAM, GPU optional). Models must share architecture/tokenizer family — merging across families needs --allow-crimes and usually breaks."
metadata:
  author: AeonDave
  version: "1.0"
---

# model-merging

Combine two or more checkpoints (or add/subtract their deltas from a base) directly in weight space — no training, no gradients. A merge of complementary fine-tunes often matches or beats its parents on benchmarks. This is the weight-arithmetic counterpart to training ([`model-finetuning`](../model-finetuning/SKILL.md)) and to activation/direction editing ([`abliteration`](../abliteration/SKILL.md)). The standard tool is `mergekit`.

## Pick a method

| `merge_method` | Idea | Models | Use |
|---|---|---|---|
| `linear` | weighted average | ≥2 | model soups, averaging checkpoints |
| `slerp` | spherical interpolation | exactly 2 | smooth blend of two same-family models |
| `task_arithmetic` | add/subtract task vectors (deltas from a base) | ≥2 | transfer or remove a specific skill/behavior |
| `ties` | task arithmetic + trim + sign election | ≥3 | merge many models with less interference |
| `dare_ties` / `dare_linear` | task arithmetic + random prune & rescale | ≥2 | drop noisy delta before merging |
| `della`, `breadcrumbs` | task arithmetic + magnitude/outlier pruning | ≥2 | refine task vectors |
| `passthrough` | copy/stack layers (frankenmerge) | 1+ | depth up-scaling, layer surgery |
| `mergekit-moe` (separate CLI) | assemble dense models into a sparse MoE | ≥2 | FrankenMoE |

SLERP is the simplest good choice for two models; use TIES/DARE for three or more. DARE is a pre-processing step, so it appears as `dare_ties`/`dare_linear`.

## Run

```yaml
# config.yaml — SLERP of two same-family fine-tunes
slices:
  - sources:
      - model: org/model-a
        layer_range: [0, 32]
      - model: org/model-b
        layer_range: [0, 32]
merge_method: slerp
base_model: org/model-a
parameters:
  t:
    - filter: self_attn
      value: [0, 0.5, 0.3, 0.7, 1]
    - filter: mlp
      value: [1, 0.5, 0.7, 0.3, 0]
    - value: 0.5
dtype: bfloat16
```

```bash
pip install mergekit
mergekit-yaml config.yaml ./merged --copy-tokenizer --lazy-unpickle --out-shard-size 1B
```

The merge runs on CPU with enough RAM; evaluate the result on a GPU afterward. `--lazy-unpickle` and `--out-shard-size` keep memory bounded for large models.

## Security-relevant uses

- **Recover capability after abliteration**: merge an abliterated model with its base to keep most of the refusal reduction while restoring quality lost to the edit.
- **Task arithmetic as behavior surgery**: add a capability delta, or subtract a "safety/alignment" delta computed as the difference between an aligned and a base checkpoint.
- **Custom blends**: combine a code model with an instruction model for a tailored offensive-assistant build.

## Gotchas

- Same architecture and tokenizer family only; `--allow-crimes` forces mismatched layer counts/architectures but usually produces a broken model — validate every output.
- Merges can regress silently, especially on math/reasoning; benchmark (MMLU/GSM8K) before trusting a merge, as with [`abliteration`](../abliteration/SKILL.md).
- High RAM, not GPU, is the usual bottleneck — models load into memory.
- Record the exact recipe (models, method, parameters) — a merge is reproducible only from its config.

## References

- Upstream: [arcee-ai/mergekit](https://github.com/arcee-ai/mergekit) (method list in the README); [NVIDIA: intro to model merging](https://developer.nvidia.com/blog/an-introduction-to-model-merging-for-llms)
- Companions: [`model-finetuning`](../model-finetuning/SKILL.md), [`abliteration`](../abliteration/SKILL.md), [`transformers`](../transformers/SKILL.md), [`ollama`](../ollama/SKILL.md) (serve the merged model)
