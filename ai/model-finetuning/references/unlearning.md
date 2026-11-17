# Unlearning — methods, verification, and serving

Load when removing training-data influence, auditing an unlearning claim, or evaluating an unlearned model's deployment. Define the forget target, retain tasks, available model access, and intended claim before selecting a method. Results below are method- and benchmark-specific, not universal guarantees of erasure.

## Method families

| Family | Method | Selection constraint |
|---|---|---|
| Gradient ascent | plain GA on forget-set loss | Can damage retained utility; use a retain objective and monitor both sets. |
| [NPO](https://arxiv.org/abs/2404.05868) | negative preference optimization | Uses reference-model likelihoods; verify the chosen implementation rather than assuming a TRL `NPOTrainer` API. |
| [RADNPO](https://arxiv.org/html/2609.34251v1) | reference-free, token-adaptive negative preference objective | Addresses concentrated/repetitive outputs in the reported experiments; the paper still observes recovery after relearning. |
| [WHP](https://arxiv.org/html/2310.02238v2) | fine-tune on alternative token labels | Uses generic replacements and model predictions to approximate labels without target knowledge; does not simply teach the opposite facts. |
| RMU | redirect forget activations toward random targets while preserving retain activations | Output suppression can coexist with recoverable hidden-state information; include representation-level evaluation. |
| [MCU](https://arxiv.org/html/2605.11685v2) | target minor components of representations | Evaluated as a defense against relearning; robustness depends on the attack, model, and optimization setup. |
| Task arithmetic / ablation | forget-vector subtraction / direction editing | Training-free edits: see [`model-merging`](../../model-merging/SKILL.md) and [`abliteration`](../../abliteration/SKILL.md). |
| Inference-time ([ARIA](https://arxiv.org/html/2609.16229v1), [UNBIND](https://arxiv.org/html/2609.35913v1)) | SAE-based intervention / conditional directional steering | Weights remain unchanged. Evaluate the serving intervention separately from weight-level removal; removing it removes the suppression. |
| [CBD](https://arxiv.org/html/2606.27683v1) | auxiliary-model divergence scores route forget-related queries away from the target | Works with final-response access to the target, but trains local auxiliary models. Claims apply to the routed interface, not the target weights. |

## Verification — match tests to access

Start with held-out forget and retain evaluations and a pre-unlearning baseline. Compare with a matched retain-only model when available. Record model/tokenizer versions, splits, budgets, and the exact artifact tested; distinguish target suppression, residual recoverability, retained utility, and forget-set privacy.

| Access / question | Test and interpretation |
|---|---|
| Response API: does suppression survive query variation? | Test paraphrases, multi-turn queries, and shuffled multiple-choice answers. Refusal or “I don't know” alone does not establish forgetting ([honesty evaluation](https://arxiv.org/html/2605.08765v1)). Evaluate fact-aligned prompts in the deployment's supported languages; cross-lingual transfer can be incomplete and asymmetric ([multilingual evaluation](https://arxiv.org/html/2609.05976v1)). |
| Editable model: can target behavior recover? | Relearn on one forget subset and evaluate on a disjoint subset; report the budget and compare recovery with a retain-only baseline when available. The [MCU paper's RTT evaluation](https://arxiv.org/html/2605.11685v2) uses this split; it is not a claim of irreversible erasure. |
| Multimodal model with fine-tuning, logits/gradient access, but no forget data | [POPS](https://arxiv.org/html/2607.06649v1) evaluates recovery using out-of-distribution data and model-generated supervision. Its gray-box requirements exceed ordinary text-only API access. |
| Raw token-ID access: does the result depend on canonical tokenization? | [Toketive](https://arxiv.org/html/2609.29045v1) tests alternative valid segmentations of the same text. A text API that re-tokenizes inputs cannot perform this test; report it as unavailable. |
| Hidden-state access: are target answers still recoverable? | [Generative probe decoders](https://arxiv.org/abs/2609.36612) measure layer-wise leakage. Separate probe training and evaluation data; assess generalization against baselines so probe training itself is not mistaken for retained knowledge. |
| Original, unlearned, and retain-only checkpoints | [UDS](https://arxiv.org/html/2605.24614v1) uses activation patching to measure residual knowledge. Its normalized score needs a retain-only model; without one, the paper's reduced patching test is only an unnormalized causal indicator. |
| Response API: does the removal reveal its target? | [TAS](https://arxiv.org/html/2609.03662v1) tests whether behavioral footprints expose forgotten entities/prompts using retained-data structure. This evaluates forget-set privacy, which is distinct from recovery of the forgotten answers. |

For editable models, include relearning and at least one representation-level test. For restricted APIs, report the narrower observable result and missing access. Passing a finite test suite is not a general certificate: [distribution-restoration research](https://arxiv.org/html/2607.19442v1) shows that forward metrics and round-trip thresholds can misclassify both suppression and retraining references. Calibrate against matched references; state uncertainty rather than declaring proof of erasure.

## Serving — evaluate after quantization

Quantization can restore previously suppressed behavior. Reported mechanisms include sensitivity to weight perturbations around narrow forget-loss minima ([loss-landscape study](https://arxiv.org/html/2609.27355v1)) and unlearning updates smaller than quantization bins ([MANSU](https://arxiv.org/html/2605.15138v1)). These observations do not imply the same recovery rate for every model or quantizer.

- Evaluate the **exact artifact served**, whether full precision or quantized, with the deployed tokenizer and inference-time interventions.
- If quantization breaks the measured removal, evaluate a quantization-aware method against the same forget/retain suite. Smoothing and circuit-restricted magnitude constraints are proposed mitigations, not deployment guarantees.

## Agent domains

- **Behavior/trajectory targets:** [GiRPO](https://arxiv.org/html/2609.33639v1) studies trajectory-level unlearning through policy optimization. Evaluate complete action sequences and retained task success; fact-recall tests alone do not establish behavioral removal.
- **Execution-state targets:** [provenance-guided selective replay](https://arxiv.org/html/2609.04875v1) addresses contaminated prompts, summaries, plans, and KV cache. Deleting a memory record alone may leave derived state. Replay requires provenance/checkpoints and side-effect controls; do not reissue consequential tool actions merely to reconstruct state.

## Related

- [`interpretability`](../../interpretability/SKILL.md) — activation-patching mechanics
- [`ai-ml-ctf`](../../../offensive-ctf/ai-ml-ctf/SKILL.md) — challenge-shaped unlearning artifacts
