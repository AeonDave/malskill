---
name: adversarial-robustness-toolbox
description: "Build or review adversarial-ML experiments with Adversarial Robustness Toolbox (ART): estimator adapters, evasion, poisoning, membership inference, or model extraction."
license: MIT
compatibility: "ART 1.20.1 API baseline; included CPU example uses Python 3.12, NumPy and scikit-learn. Other backends require their own dependencies and validation."
metadata:
  author: AeonDave
  version: "1.0"
---

# Adversarial Robustness Toolbox

Use ART to implement a bounded experiment against an explicitly authorized model and dataset; ART is an API, not evidence that a model is robust or vulnerable. Pin the installed ART version and check the matching source before relying on API behavior. This guide is grounded in ART 1.20.1, tag commit `cbc47a890a191809baa292992761030e7f46ab18`.

## Workflow and evidence contract

1. Define model access, attacker knowledge, eligible inputs, data splits, perturbation or query budget, and success condition before choosing an attack.
2. Wrap the actual model with an ART estimator that exposes the interfaces required by the selected attack. Verify input domain, shape, labels, outputs, loss/gradient behavior, and clipping in that wrapper.
3. Keep training, tuning, and final evaluation data distinct. Record ART and dependency versions, estimator/backend, attack parameters, seeds, and any query accounting.
4. Check generated data against finite-value, shape, domain/clip, and stated perturbation-budget invariants. Report clean performance and attack metrics with explicit numerators and denominators. A result from one model, split, seed, or attack is not a general robustness claim.

For each report, include: (a) `art.__version__` and relevant framework versions; (b) model/estimator type and input/output contract; (c) preprocessing and clip domain; (d) threat model, attack/access mode, norm and epsilon units or query/training-data budget; (e) clean baseline, metric definition and denominator, attack parameters, seed, measured perturbation/query counts, and limitations. Separate source-established API facts from behavior observed in the run.

## Load the focused reference

- Adapter selection, preprocessing, loss gradients, output scores/logits, clipping, or an ART version change: [references/estimator-contract.md](references/estimator-contract.md).
- White-box evasion with FGM/PGD or a defensible perturbation/query-budget metric: [references/evasion-evaluation.md](references/evasion-evaluation.md).
- Authorized poisoning, membership-inference/privacy, or model-extraction workflow: [references/privacy-poisoning-extraction.md](references/privacy-poisoning-extraction.md).
- Reproducible CPU FGM/PGD API and invariant smoke test, without downloads or external models: [assets/cpu_evasion_smoke.py](assets/cpu_evasion_smoke.py).

For challenge artifacts and challenge-specific success oracles, load [AI/ML CTF](../../offensive-ctf/ai-ml-ctf/SKILL.md) instead of copying its broader playbooks here; load this skill only for ART-specific adapter or API work.
