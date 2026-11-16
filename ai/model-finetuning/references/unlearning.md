# Unlearning — methods, verification, and serving

Load when removing knowledge/capabilities from a trained model, when verifying a vendor's or your own unlearning claim, or when serving an unlearned model quantized. Grounded in the 2025-2026 literature ([awesome-llm-unlearning](https://github.com/chrisliu298/awesome-llm-unlearning) 2026 section); arXiv IDs given as anchors.

## Method families

| Family | Method | Notes |
|---|---|---|
| Gradient ascent | plain GA | destabilizes beyond the target; avoid |
| **NPO** (`NPOTrainer`, TRL) | negative preference optimization | default; needs a frozen reference model |
| **RADNPO** (arXiv:2609.34251) | reference-free, token-level adaptive NPO | fixes NPO's low-entropy forgetting (repetitive degenerate outputs); no reference model saves VRAM; custom loss (~80 lines in a `Trainer.compute_loss`), not expressible in TRL configs. Still recoverable by relearning |
| **WHP** | fine-tune on augmented corpora | teach the opposite of the target knowledge |
| **RMU** | steering forget-activations toward random directions (WMDP) | strong output suppression (esp. WMDP-Bio), but generative hidden-state probing still recovers the content (2609.36612) |
| **MCU** (arXiv:2605.11685) | project the unlearning loss onto minor principal components | defense against relearning: dominant-PC edits are trivially restored; minor-component edits cost the attacker ~1/σ² steps per component. Wraps any of the above losses |
| Task arithmetic | subtract a forget task-vector | training-free — [`model-merging`](../../model-merging/SKILL.md) |
| Ablation | direction/knowledge-neuron ablation | training-free — [`abliteration`](../../abliteration/SKILL.md) |
| **Inference-time** (ARIA arXiv:2609.16229; UNBIND arXiv:2609.35913) | SAE-latent gating / conditional directional subtraction via hooks | reversible (remove hook), per-input, no weight change; weights keep the knowledge — a serving wrapper, not a sanitization. UNBIND uses two directions (Fisher detector + gradient-derived output dir) with adaptive magnitude — always-on subtraction destroys utility |
| **Black-box routing** (CBD, arXiv:2606.27683) | two small auxiliary models score behavioral divergence per query; route flagged queries to a reference LoRA | API-only access works; suppression at the interface — knowledge stays in the target weights; every access must pass through the router |

## Verification — how to test an unlearning claim

Output-level metrics create the illusion of forgetting (arXiv:2609.36612: a model can score clean on every output metric while per-layer probes regenerate the answers). Test in this order, cheapest first:

1. **Adversarial retrieval probes** — rephrasings, related-question chains, multi-hop elicitation (classic "jogging the memory"). A refusal or "I don't know" is **not** forgetting: IDK-tuning masks still-recoverable knowledge, so re-ask under paraphrase, multi-turn follow-ups, and position-shuffled MCQ (arXiv:2605.08765). Probe **natively in every language the model speaks** — forgetting weakens cross-lingually, so a fact removed in one language stays elicitable in another (arXiv:2609.05976).
2. **Relearning attack (RTT protocol)** — fine-tune the unlearned model on a small held-out forget split; measure recovery on the rest. Most published methods partially recover; RTT is the standard audit (arXiv:2605.11685).
3. **Gray-box recovery without forget data (POPS, arXiv:2607.06649)** — optimize a prompt suffix on a fine-tuned copy of the victim, then LoRA on the victim's own suffix-prompted outputs; recovers most unlearned multimodal knowledge with zero forget-set access.
4. **Tokenization bypass (Toketive, arXiv:2609.29045)** — query the same string under alternative valid subword segmentations (raw token IDs, round-trip verified); locate-then-edit methods patch only the canonical trajectory, so non-canonical tokenization recovers pre-edit answers. Feed raw IDs — any re-canonicalization at the API defeats the test.
5. **Hidden-state probing (arXiv:2609.36612, code OptimAI-Lab/HiddenStateUnlearning)** — train lightweight per-layer probe decoders on the forget set; if any layer regenerates answers while outputs are clean, forgetting is output-only. Strongest single test for "did the knowledge leave the representations" (the paper's fix, PARS, folds these probes into an adversarial min-max objective).
6. **Depth score (UDS, arXiv:2605.24614, code gnueaj/unlearning-depth-score)** — causal activation patching against a retain-trained reference scores how deep erasure goes; it tracks residual knowledge more faithfully than output/MIA metrics (AUC 0.971) and flags cases those metrics rate as erased while UDS shows them still recoverable. Needs full + retain + unlearned checkpoints.
7. **Forget-set extraction (TAS, arXiv:2609.03662)** — black-box: refusal footprints themselves reveal *what* was unlearned (Thompson-sampled template/entity search over retained data; budget scales with the search space, up to ~5k queries, recovering the forgotten entity near-100% and most forgotten prompts). A model whose refusals are distinguishable from its retained behavior leaks its forget set.

An unlearning claim that has not faced at least relearning + one representation-level test is unverified. Ceiling (arXiv:2607.19442): forward-only/black-box tests cannot *certify* forgetting — a plain logit-suppression model passes the whole forward battery — and for facts the retained data can reconstruct, no oracle-free certificate exists; certification needs a matched retain-only reference plus a relearning round-trip, and even then stays necessary-not-sufficient.

## Serving rule — quantization resurfaces unlearning

Post-training quantization (4-bit) systematically weakens unlearning via two mechanisms: the forget-loss sits in a sharper minimum than the retain-loss, so quantization's weight perturbation knocks the model out of the narrow forget basin (arXiv:2609.27355: 13%→54%, ~4x resurfacing on MUSE-News); and diffuse unlearning updates land far below the 4-bit bin width (47–828x), so rounding erases them (arXiv:2605.15138). Rules:

- Never certify unlearning at full precision — evaluate on the **exact quantized artifact you serve**.
- Quantization-aware options: sensitivity-guided smoothing toward flat minima (2609.27355), or circuit-restricted edits with a per-parameter magnitude floor above the bin width (MANSU, 2605.15138).

## Agent domains

- **Behavior/trajectory unlearning (GiRPO, arXiv:2609.33639)** — agents must forget *behaviors*, not facts: a knowledge-clean agent can still enact the trajectory. GiRPO injects forget-trajectories as penalized pseudo-rollouts into GRPO groups; GA/NPO collapse task success here.
- **Execution-state unlearning (arXiv:2609.04875)** — for stateful agents, deleting the memory record is a no-op: KV cache, generated summaries, and pending plans remain contaminated. Provenance-guided selective replay re-executes only the post-exposure suffix (checkpoint metadata makes restore a KV-cache crop). Scope is runtime state — complements, does not replace, weight-level unlearning.

## Related

- [`abliteration`](../../abliteration/SKILL.md) — training-free behavior editing (the inference-time family's ancestor)
- [`model-merging`](../../model-merging/SKILL.md) — task-arithmetic subtraction
- [`interpretability`](../../interpretability/SKILL.md) — activation patching mechanics used by UDS
- `offensive-ctf/ai-ml-ctf` — challenge-shaped unlearning artifacts
