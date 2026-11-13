# Evasion experiments and metrics

Load when generating or evaluating input perturbations. The examples and API statements here are pinned to [ART 1.20.1](https://github.com/Trusted-AI/adversarial-robustness-toolbox/tree/cbc47a890a191809baa292992761030e7f46ab18); re-check the installed version before reusing parameters.

## Freeze the threat model before calling `generate`

Write down the model's input representation and allowed range; the attacker’s white-box/score/label access; the `L_p` norm and epsilon in ART input coordinates; targeted or untargeted objective; any per-sample mask; and the query/compute limit. Keep model training, attack tuning, and final test examples separate. Choose parameters on a validation split, then report the held-out test result. Include attack seeds and random-initialization settings where relevant.

For gradient-based white-box attacks, FGM and PGD require an ART `BaseEstimator` implementing `LossGradientsMixin`. Confirm the estimator's gradient matches the loss and preprocessing being evaluated; see [estimator-contract.md](estimator-contract.md). The constructor checks these required types. If the model only returns labels or scores, that is not proof it supplies a usable loss gradient.

## Use FGM and PGD according to their actual parameters

ART 1.20.1 [`FastGradientMethod`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/fast_gradient.py) accepts `norm`, `eps`, `eps_step`, `targeted`, `num_random_init`, `batch_size`, and `minimal`. For ordinary non-minimal FGM, `eps` bounds the step; `eps_step` is for minimal-perturbation mode. For targeted FGM, provide target labels as `y`. If untargeted and `y=None`, ART uses current model predictions as labels; for an evaluation against known ground truth, pass the true labels for the clean-correct samples.

ART 1.20.1 [`ProjectedGradientDescent`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/projected_gradient_descent/projected_gradient_descent.py) also accepts `max_iter`, `random_eps`, `decay`, and `verbose`. Each iteration projects onto the requested norm ball and clips to estimator `clip_values`. Set `num_random_init=0` and `random_eps=False` for a deterministic no-random-start smoke run; otherwise record and seed the initialization. Its implementation uses a NumPy path for the sklearn adapter and framework-specific paths for some neural estimators. Do not claim another backend was validated by a sklearn test. ART documents that for non-infinity norms its projection step rescales noise and may be suboptimal for `p != 2`; account for this implementation caveat when choosing a norm.

`eps` is expressed in the values supplied to ART, not automatically in the model's pre-normalized or display-space units. Set `clip_values` to those same input coordinates. Clipping can change a candidate; independently verify both `x_adv` bounds and `||x_adv - x||_p <= eps` with a small numeric tolerance.

## Evaluate on clean-correct examples

First compute clean predictions on the held-out test set. Let `eligible = (clean_pred == y_true)`. Generate the attack and calculate the conditional attack metric on exactly this set, using the original labels for untargeted evaluation. Report the full test clean accuracy separately; do not divide attack successes by every test sample if the claimed denominator is clean-correct samples.

For untargeted evaluation:

- `N_clean_correct = sum(eligible)`; fail/mark undefined if it is zero.
- Success count is `sum(pred_adv[eligible] != y_true[eligible])`.
- Conditional attack success rate is that count divided by `N_clean_correct`.
- Also report conditional robust accuracy, `sum(pred_adv[eligible] == y_true[eligible]) / N_clean_correct`; state explicitly that it is conditional on clean correctness.

For targeted evaluation with target `t`:

- Restrict to clean-correct samples for which `t != y_true`. A sample already in the target class is not an eligible targeted success.
- Provide the target labels to `generate(..., y=target_labels)` with `targeted=True`.
- Success count is `sum(pred_adv[eligible_target] == target[eligible_target])`; divide by `N_eligible_target`, and report that denominator.

A concise implementation is in [assets/cpu_evasion_smoke.py](../assets/cpu_evasion_smoke.py): it filters to clean-correct held-out examples before generating attacks, checks targeted eligibility, and asserts finite values, bounds, output shape, and measured `L∞` budget. Its success rates only validate the synthetic example's behavior; they say nothing about a real model.

## Count budgets and report evidence

For each run, report model/estimator and ART versions; data split and clean accuracy; attack class, norm, `eps`/`eps_step`, iteration count, initialization, target policy, seed, and preprocessing/clip range; sample count; numerator/denominator; and measured maximum/summary perturbation. Compare multiple relevant epsilon values and seeds when the question is robustness over a range, not one operating point. Include any failed or skipped inputs rather than silently dropping them.

For black-box evaluation, define a query as the actual call/record charged by the target interface and enforce the budget at that boundary. An ART attack's iteration count, batch size, or generated sample count is not automatically the number of victim queries. Instrument and report actual query rows/calls, including retries or failures according to the evaluator's counting rule. Do not claim query-limited coverage without that accounting.

A successful example establishes only that this exact model, input, and configuration met the stated objective. A failed attack is not evidence of robustness; use a threat model and attack suite appropriate to the claim, and do not infer universal robustness from one attack.

## Reproduce the CPU smoke

From the repository root, use a temporary Python 3.12 environment and pin the tested dependencies. Include `packaging` because ART 1.20.1's top-level import reaches a source module importing `packaging.version`, although `setup.py` does not declare it.

```powershell
$venv = Join-Path $env:TEMP 'art1201-env'
py -3.12 -m venv $venv
uv pip install --python "$venv/Scripts/python.exe" 'adversarial-robustness-toolbox==1.20.1' 'numpy==2.5.4' 'scikit-learn==1.9.1' 'scipy==1.18.1' 'packaging==26.3'
& "$venv/Scripts/python.exe" ai/adversarial-robustness-toolbox/assets/cpu_evasion_smoke.py
```

The tested runtime is Python 3.12.10 with ART 1.20.1, NumPy 2.5.4, scikit-learn 1.9.1, SciPy 1.18.1, and packaging 26.3; no optional neural backend is installed. On POSIX systems, use the venv interpreter at `<venv>/bin/python` instead of `<venv>/Scripts/python.exe`. Do not activate/install into the global interpreter. The smoke uses generated NumPy arrays and scikit-learn LogisticRegression only; it downloads no data or weights. Its successful exit requires nonzero successes for each synthetic FGM/PGD case and all shape, finite-value, clipping, budget, and denominator checks; this only verifies the fixture/API path, not real-model robustness.

### Primary sources

- [ART evasion API documentation, 1.20.1](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/docs/modules/attacks/evasion.rst)
- [`fast_gradient.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/fast_gradient.py)
- [`projected_gradient_descent.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/projected_gradient_descent/projected_gradient_descent.py)
- [`projected_gradient_descent_numpy.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/projected_gradient_descent/projected_gradient_descent_numpy.py)
- [`Attack` estimator requirement checks](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/attack.py)
