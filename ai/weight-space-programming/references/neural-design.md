# Direct neural weight design and repair

Use when the artifact must implement its behavior through specified neural operations. For authored fact tables, use [sparse-memory.md](sparse-memory.md); use [evaluation.md](evaluation.md) for comparative and deployment claims.

## Freeze the executable specification

Record these before editing tensors:

- Inputs: feature order, units, valid ranges, missing values, token IDs, vocabulary, padding, sequence limits, and any normalization.
- Forward path: layer order, activations, residual additions, normalization, attention masks, positional representation, and tied parameters.
- Outputs: coordinate or class meanings, logits versus probabilities, decoder, thresholds, tie-breaking, and invalid-input behavior.
- Editable surface: exact tensors and indices; whether architecture, preprocessing, vocabulary, or decoder changes are permitted.
- Runtime: dtype, tensor layout, serialization format, and deterministic or stochastic execution settings.

For dense layers, state the equation and orientation: this reference uses `y[o] = sum(W[o][i] * x[i]) + b[o]`, with `W` shaped `(outputs, inputs)`. Check the actual framework's convention rather than transposing by assumption. Biases shift activation boundaries; embedding rows and output columns require an explicit vocabulary mapping.

Keep a reference oracle outside the forward path. A wrapper that computes the answer and passes it through arbitrary weights does not demonstrate a neural implementation.

Check representability before authoring. A finite affine/ReLU network with a continuous scalar output cannot exactly implement a jump over a continuous input interval. A discrete input domain or threshold decoder changes that constraint. If the required mapping does not fit the allowed architecture, change the declared architecture or approximation contract; do not silently smooth the target. An independent [construction protocol](https://github.com/ctrimm/weight-space-programming/blob/b312974277a5d7bfb7830d543a428e4b8109a32b/experiments/eitc-credit/PROTOCOL.md) retains this failure in a stipulated arithmetic task.

## Author the smallest named computation

1. Decompose the specification into intermediate quantities with known ranges: indicators, thresholds, counters, comparisons, or bounded accumulators.
2. Assign each quantity to a channel or subspace. Record the linear combination, bias, activation, and destination for every authored path.
3. Compose one operation at a time and inspect intermediate values. Check sign, scale, saturation, and boundary behavior before combining paths.
4. Keep unused channels inactive where the architecture permits it. In a pretrained model, do not zero unrelated channels merely to simplify the construction.
5. Treat normalization, residual mixing, tied weights, or soft attention as part of the computation. A locally correct matrix can fail after those operations.

Do not infer a feature's semantics from its name or a plausible weight pattern alone. Confirm the hypothesis with probes or interventions permitted by the task; label an untested reading as a hypothesis. The [original WSP work](https://rikiyat.github.io/blog/weight-space-programming/) separates reading, repair, and construction experiments with different access to execution and feedback; preserve those distinctions in a reproduction.

For a weight-reading audit, permute output coordinates together with the evaluator's decoder and confirm unchanged task behavior. Check whether the reader's proposed tensor-to-output interpretation follows the permutation; anonymized labels help separate computation tracing from dataset recognition. The [label-permutation study](https://arxiv.org/html/2611.08070v1) motivates this control in small classifiers; it does not establish a general failure of weight reading or writing.

## A self-contained authored fixture

Contract: one finite scalar `x` in `[-10, 10]`; output `clip(x - 2, 0, 3)`. The hidden channels are `ReLU(x - 2)` and `ReLU(x - 5)`; subtracting the second caps the first. Use this as a tensor-layout fixture, not as evidence of general model capability.

```python
import math


def dense(values, weights, biases):
    if len(weights) != len(biases) or any(
        len(row) != len(values) for row in weights
    ):
        raise ValueError("incompatible tensor shapes")
    return [
        sum(w * value for w, value in zip(row, values)) + bias
        for row, bias in zip(weights, biases)
    ]


def forward(values, parameters):
    hidden = dense(values, parameters["w1"], parameters["b1"])
    hidden = [max(0.0, value) for value in hidden]
    return dense(hidden, parameters["w2"], parameters["b2"])


PARAMETERS = {
    "w1": ((1.0,), (1.0,)),
    "b1": (-2.0, -5.0),
    "w2": ((1.0, -1.0),),
    "b2": (0.0,),
}


def predict(x):
    if not math.isfinite(x) or not -10.0 <= x <= 10.0:
        raise ValueError("input must be finite and within [-10, 10]")
    return forward((x,), PARAMETERS)[0]


for x, expected in [(-10.0, 0.0), (2.0, 0.0), (3.0, 1.0),
                    (5.0, 3.0), (10.0, 3.0)]:
    assert math.isclose(predict(x), expected, rel_tol=0.0, abs_tol=1e-12)
```

The forward path contains only generic dense/ReLU/dense operations; the task constants are parameter data. Keep that separation when saving or loading the artifact. The wrapper validates the input contract; it does not compute the target formula.

## Read or repair an existing network

Preserve the original artifact and reproduce the failure under its actual preprocessing and decoder. Start from a specific hypothesis about a path, unit, or tensor; avoid interpreting arbitrary coordinates as stable human concepts.

Record a patch manifest containing the original artifact hash, tensor names and indices, old/new values or deterministic transformation, intended intermediate effect, and predicted output changes. Save the edited artifact separately. Include hashes of architecture, input mapping, and decoder so that a changed wrapper cannot masquerade as a weight repair.

Compare original and edited outputs on the failing case, nearby counterexamples, and held-out unaffected cases. Where possible, disable only the edited path or restore the original values to test the causal explanation. A small parameter count does not guarantee a small behavioral effect.

Inspect how an editing method obtains its update. A closed-form final write does not make the whole method optimizer-free: [ROME's value computation](https://github.com/kmeng01/rome/blob/0874014cd9837e4365f3e6f3c71400ef11509e04/rome/compute_v.py) optimizes a target activation with Adam before forming the rank-one weight update. Declare such optimization and its data access; do not present it as direct specification-to-weight authoring under a no-optimizer contract.

## Verify semantics and precision

Test exact thresholds, values immediately on both sides, extrema, invalid/non-finite inputs, and combinations that activate competing paths. For the fixture, include neighborhoods of `2` and `5` and an independent oracle over additional values in the declared range.

Repeat checks after serialization and on the deployed dtype/runtime; arithmetic identities in real numbers do not guarantee equal floating-point outputs. Inspect intermediate ranges for overflow, underflow, saturation, or cancellation. Set tolerances from the output contract and report any unsupported input region.

For claimed interpretability, have an independent reader reconstruct the computation from its channel/parameter specification and compare behavior on unseen inputs. [iWSP](https://github.com/csinva/weight-space-programming-autoresearch) uses explicit authoring and reconstruction experiments; validation-guided revisions remain adaptive even when training is prohibited.

## Use a compiler when the specification fits

[Tracr](https://github.com/google-deepmind/tracr) compiles supported RASP programs into transformer parameters through named intermediate subspaces. Use it as a compiler-generated fixture when the task can be expressed in supported RASP; distinguish compilation from an LLM inferring weights directly.

Pin a revision and environment: the upstream repository is archived. Record the program, finite vocabulary, maximum sequence length, and required beginning-of-sequence token. Compare compiled outputs with the program's semantics over the admitted input domain. If exporting to another transformer implementation, validate the adapter and outputs separately; weights alone do not establish compatible execution.

Run Tracr's [static and input-dependent validation](https://github.com/google-deepmind/tracr/blob/9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd/tracr/compiler/validating.py): `validate(program)` alone cannot detect every unsupported categorical `Aggregate`; `validate(program, xs)` checks a concrete input. Test representative and boundary inputs, then compare interpreter and compiled outputs. Enumerate small finite domains. Record [`mlp_exactness`](https://github.com/google-deepmind/tracr/blob/9ce2b8c82b6ba10e62e86cf6f390e7536d4fd2cd/tracr/compiler/compiling.py); increasing its value can cause numerical problems through larger parameter norms.

### Iterative programs with ALTA

Use [ALTA](https://arxiv.org/html/2410.18077v2) when the fixture needs iterative state updates expressible by its program language and Universal Transformer compilation. Keep compiler-generated feed-forward blocks distinct from its optional learned blocks; learned blocks introduce a training stage.

- Declare the layer/iteration budget and expected terminal state. The [examined compiled runner](https://github.com/google-deepmind/alta/blob/afb0559da1dc08a3819c5ae20e0547686052b75a/framework/transformer/transformer_utils.py) runs a fixed `max_layers` loop; interpreter support for halting does not establish dynamic halting in that runner.
- Compare interpreter and compiled intermediate states, final outputs, insufficient iterations, and extra iterations after a terminal state. An algorithm that handles longer inputs may require more inference layers.
- Preserve attention-mask assumptions when changing sharpness or dtype. In the [examined configuration](https://github.com/google-deepmind/alta/blob/afb0559da1dc08a3819c5ae20e0547686052b75a/framework/compiler/compiler_config.py), `attention_scalar**2` must remain significantly below the relative-mask magnitude `1e9`; increasing sharpness can break masking. Recheck the configuration in the pinned release used for execution.
