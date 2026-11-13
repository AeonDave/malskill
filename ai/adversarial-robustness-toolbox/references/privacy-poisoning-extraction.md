# Poisoning, membership inference, and extraction workflows

Load only for one of these authorized model/data workflows. This is not a catalogue of ART attacks. API and requirements below are source-checked against [ART 1.20.1, commit `cbc47a890a191809baa292992761030e7f46ab18`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/tree/cbc47a890a191809baa292992761030e7f46ab18); re-check them against the installed release.

## Poisoning: construct, train, then evaluate separately

For an input-space backdoor transformation, `PoisoningAttackBackdoor(perturbation=callable_or_list)` has `_estimator_requirements = ()`: the attack object itself is not a model adapter. Its `.poison(x, y, broadcast=False)` requires `y` and returns transformed examples plus a copy of the supplied labels; with `broadcast=True` ART broadcasts the supplied label array. The callable(s) transform inputs; this helper does not fit the victim model or establish that a backdoor works. Supply the intended target labels and validate the output shape, label mapping, clip/domain constraints, and training-data provenance before passing it into an authorized training pipeline. Evaluate clean behavior and the trigger/target condition on a separate held-out set.

Do not assume the API selects poisoning points, label policy, or trigger semantics for you. Verify those in the experiment code. Source: [`backdoor_attack.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/poisoning/backdoor_attack.py).

## Privacy: learned black-box membership inference

`MembershipInferenceBlackBox(estimator, input_type="prediction"|"loss", ...)` requires `BaseEstimator` plus either `ClassifierMixin` or `RegressorMixin`. For `input_type="prediction"`, the attack features are the estimator's `predict` output (or supplied `pred`/`test_pred`). For `input_type="loss"`, it calls `compute_loss(x, y)`; if predictions are supplied instead of `x`, it needs `compute_loss_from_predictions`. The loss path also requires labels. Confirm those concrete methods and output shapes; passing the constructor's type check alone does not prove the selected input path will run.

Use `fit(x=members, y=..., test_x=nonmembers, test_y=...)` (or the equivalent precomputed predictions) to train the attack model. ART labels the first set members and the second non-members. Keep a separate member/non-member evaluation set for `infer`; report the class balance, attack-model setup, input type, and inference counts. Do not reuse the attack's fit pairs as its final evaluation and do not describe the result as a general privacy guarantee.

In 1.20.1, the default `attack_model_type="nn"` path imports PyTorch during `fit`/`infer`; the minimal sklearn/NumPy environment in this skill does not validate that backend. The source offers sklearn attack models such as `rf`, `lr`, `gb`, `dt`, `knn`, or `svm`; their behavior is source-verified but not run here. Select one explicitly when avoiding the PyTorch default, then test that path in its own environment. Source: [`black_box.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/inference/membership_inference/black_box.py).

## Extraction: budget the victim interface, not just the local attack

`KnockoffNets(classifier=victim, nb_stolen=..., sampling_strategy=..., ...)` requires a `BaseEstimator` and `ClassifierMixin`; `extract(x, thieved_classifier=...)` also requires a supplied ART classifier for the stolen model. ART's random selection chooses up to `min(nb_stolen, len(x))` candidate rows without replacement; adaptive mode requires `y`, while random mode warns that supplied `y` is unused. `nb_stolen` is a declared target-query budget, not a measurement of all external transport, retries, or provider billing. Count and enforce the real victim calls at the API boundary.

Before running, verify the candidate pool is permitted, query authorization and cap are explicit, and the stolen estimator accepts the fit contract this implementation uses: its `fit` calls pass `batch_size`, `nb_epochs`, and `verbose`. Do not assume an arbitrary sklearn estimator accepts these extra arguments. In 1.20.1 the victim prediction is reduced with `argmax` unless `use_probability=True`; with that option the raw `predict` output is passed onward. The source docstring describes logit outputs, so check this output/label contract for the actual victim and stolen estimator rather than inferring it from `use_probability`'s name. Evaluate agreement on an independent held-out set and report the actual victim query count and output type.

Source: [`knockoff_nets.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/extraction/knockoff_nets.py).

## Evidence to retain

For these workflows, preserve the ART release/commit, adapter and required mixins, data membership/provenance, train/validation/evaluation boundaries, relevant labels and output types, attack parameters, random seeds, and exact counts. Report only what was run. The poisoning helper's output is not proof of successful poisoning; a membership score is not a general privacy claim; and student/victim agreement is not proof of full model equivalence.
