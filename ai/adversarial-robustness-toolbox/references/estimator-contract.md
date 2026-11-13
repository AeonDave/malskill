# Estimator, preprocessing, and version contract

Load before wrapping a model, changing input normalization, relying on scores/gradients, or upgrading ART. API facts below are for ART 1.20.1 at [commit `cbc47a890a191809baa292992761030e7f46ab18`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/tree/cbc47a890a191809baa292992761030e7f46ab18); do not silently apply them to another installed version.

## Pin and inspect the runtime

Record `art.__version__`, Python, NumPy, scikit-learn, and the backend actually used. Pin ART in a disposable environment; do not infer API compatibility from a tutorial or current `latest` docs. ART 1.20.1's [`setup.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/setup.py) declares NumPy, SciPy, scikit-learn, six, setuptools, and tqdm. Include `packaging` as well: ART's top-level import reaches a module that imports `packaging.version`, although it is not declared there. No PyTorch/TensorFlow backend is needed for the included sklearn smoke test.

At runtime, print versions rather than assuming the install resolver chose what you expected:

```python
import art, numpy, sklearn
print(art.__version__, numpy.__version__, sklearn.__version__)
```

On API changes, re-check the relevant tagged source and estimator requirements before altering an experiment. In particular, check `Attack._estimator_requirements`, not only whether the wrapped model has a method with a familiar name.

## Choose and validate the adapter

An ART classifier adapter defines the contract between raw experiment inputs and the underlying model: accepted sample shape/dtype, label encoding, output scores, preprocessing, clipping, and (if applicable) gradient methods.

For scikit-learn, the [`SklearnClassifier` factory](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/classification/scikitlearn.py) dispatches known model classes to specialized adapters. For example, `LogisticRegression` becomes `ScikitlearnLogisticRegression`; its source implements `class_gradient` and `loss_gradient`. Generic `ScikitlearnClassifier` only promises the classifier behavior, not those gradients. FGM and PGD require `BaseEstimator` plus `LossGradientsMixin`; their constructors reject an estimator that does not satisfy those types. See [`FastGradientMethod`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/fast_gradient.py) and [`ProjectedGradientDescent`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/projected_gradient_descent/projected_gradient_descent.py).

For this adapter, `fit(x, y)` documents one-hot targets. The sklearn implementation preprocesses `x`, converts one-hot `y` to class indices, then calls the wrapped model's `fit`. `predict(x)` returns a `(n_samples, n_classes)` score matrix: `predict_proba` if available, otherwise one-hot-encoded `predict` output. Check the actual shape, finiteness, class ordering, and score semantics before using predictions as attack or privacy inputs. See the [ART estimator API docs](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/docs/modules/estimators/classification_scikitlearn.rst).

## Keep input coordinates coherent

- `clip_values=(min, max)` describes allowed input feature bounds. Use bounds in the exact coordinates passed to `generate`; attacks use them to clip candidates. They are not a substitute for preprocessing or a declaration that normalized features are in `[0, 1]`.
- `preprocessing=(subtrahend, divisor)` applies `(x - subtrahend) / divisor`; ART 1.20.1 constructs its standardisation preprocessor from these values. `preprocessing_defences` is a separate preprocessor interface. Avoid normalizing once outside the estimator and again inside it.
- Define epsilon in the coordinates that ART receives. If a model's conventional input has been externally normalized, translate the intended bound into that coordinate system and verify the adapter's preprocessing/gradient contract before moving normalization. Record the coordinate system and verify `max(abs(x_adv - x))` after generation.
- Keep clean samples, attack outputs, and estimator predictions finite; check shape, clip bounds, and actual displacement in the experiment rather than assuming an attack honored the intended configuration.

The base estimator implementation documents clipping and the `(subtrahend, divisor)` transform in [`estimator.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/estimator.py); the sklearn adapter documents how it applies them in [`scikitlearn.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/classification/scikitlearn.py).

## Scores, logits, and loss gradients are not interchangeable

`SklearnClassifier(..., use_logits=True)` is not a general conversion to raw logits. The generic adapter uses `predict_log_proba` only when the wrapped model has it; otherwise it raises. ART 1.20.1's factory dispatches specialized scikit-learn adapters without forwarding `use_logits`, and `ScikitlearnLogisticRegression` does not expose that constructor argument. Do not assume the factory's flag changed the specialized adapter. In addition, its `loss_gradient` implementation calls `predict`; changing that method's score output can change the gradient calculation. For FGM/PGD, use the default probability contract in the included LogisticRegression example unless a separately tested loss-gradient contract justifies another setting.

**ART 1.20.1 LogisticRegression caveat:** `ScikitlearnLogisticRegression.loss_gradient` preprocesses inputs, then calls `predict` on those already-preprocessed values; `predict` preprocesses again ([source](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/classification/scikitlearn.py#L896-L919)). With non-identity preprocessing, its loss gradient can disagree with the cross-entropy computed from that same adapter's predictions. The included smoke uses identity preprocessing only. Before relying on another configuration, compare gradients against centered finite differences of the same prediction loss in ART input coordinates; if they disagree beyond numerical tolerance, use a corrected, independently verified adapter. This is an adapter/version-specific limitation, not a claim about all ART estimators.

Check which method the chosen attack actually consumes. FGM and PGD call `estimator.loss_gradient(x, y)` and invert its direction for targeted mode. A model that emits class IDs or probability scores does not thereby provide a valid differentiable loss. If the attack requires `LossGradientsMixin` or another interface, verify the concrete adapter inherits it and test returned gradient shape and finite values before interpreting attack outcomes.

## Minimal runtime verification

Use the one local synthetic example at [assets/cpu_evasion_smoke.py](../assets/cpu_evasion_smoke.py) to exercise the 1.20.1 sklearn wrapper, FGM, PGD, score shapes, clipping, finite-value checks, L-infinity budget, and clean-correct denominator. It is an API smoke test, not evidence about a real model's robustness.

### Primary sources

- [ART 1.20.1 estimator documentation](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/docs/modules/estimators/classification_scikitlearn.rst)
- [`scikitlearn.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/classification/scikitlearn.py)
- [`estimator.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/estimators/estimator.py)
- [`fast_gradient.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/fast_gradient.py)
- [`projected_gradient_descent.py`](https://github.com/Trusted-AI/adversarial-robustness-toolbox/blob/cbc47a890a191809baa292992761030e7f46ab18/art/attacks/evasion/projected_gradient_descent/projected_gradient_descent.py)
