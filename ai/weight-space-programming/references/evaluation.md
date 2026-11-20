# Evaluate authored weights and compiled memories

Load when reproducing a result, comparing architectures, accepting an edit, or deciding whether an authored model is useful in a security pipeline. Separate artifact validity, task quality, edit locality, and cost; success on one does not establish the others.

## Freeze the experiment boundary

Record the task, input/output contract, allowed architecture changes, authoring examples, feedback budget, and acceptance criteria before inspecting final results. Distinguish:

- **Construction:** the writer emits weights or a builder without a numerical optimizer.
- **Selection:** validation results choose prompts, architectures, weights, facts, or candidate generations. This is feedback-driven search even when no gradients are computed.
- **Evaluation:** frozen artifacts are scored on data unavailable to construction and selection.

Report all examples exposed during development, not only labeled examples shown in the first prompt. Record writer model/version, prompts, tool permissions, attempts, retained candidates, feedback, and pretrained encoders. A writer's prior knowledge can include a public benchmark; no direct test-file access does not prove absence of contamination.

Split by the deployment question: hold out paraphrases for wording robustness, new fact combinations for composition, and source families or versions for transfer. Keep a final set untouched by candidate selection. Mark unavailable independent evidence as untested.

## Verify the actual artifact

1. Inspect the encoder, builder, forward, decoder, and load path. Identify where task computation happens; source review of the forward alone cannot establish what the builder learned or accessed.
2. Build in a process with only approved authoring inputs. Freeze/hash the output, end that process, then score the immutable artifact in a separate process with evaluation access. A directory layout or renamed test file alone is not isolation.
3. Rebuild unchanged inputs twice. For a claimed deterministic build, compare exact tensor values and metadata; compare file hashes too when serialization is deterministic. Preserve every divergent artifact.
4. If a build interface accepts examples, repeat with changed labels and then changed inputs. Unexpected weight changes expose dependencies; unchanged weights are a useful control, not proof that no hidden data was accessed.
5. Check shape, dtype, finite values, token IDs, device placement, and state loading. Verify that forward uses the emitted tensors; task-specific branches, stored answer strings, or hidden retrieval must be counted as part of the model.
6. Run independent cases, boundary inputs, unknown symbols, contradictory facts, malformed input, and the intended precision/device. Apply the declared failure or abstention behavior.

For a known construction, also check its active-unit inventory, allowed coefficient pattern, repeated-constant consistency, and unused channels against the compiler specification. These structural invariants complement sampled outputs; they are not a general backdoor detector or proof outside the verified construction. The independent [weight-tamper audit](https://github.com/ctrimm/weight-space-programming/blob/b312974277a5d7bfb7830d543a428e4b8109a32b/experiments/weight-tamper-audit/audit.py) illustrates construction-specific checks.

When rescoring upstream artifacts, inspect comparison fields and tolerances, not only process exit status. The examined `harness/score_model.py` in the paper's release prints stored-score matches without making a mismatch a failing exit code. Audit ties too: its scorer gives all-equal logits uniform-guess credit, which differs from first-index `argmax`.

## Choose comparisons that answer the task

| Target | Required useful comparison |
|---|---|
| Known algorithm compiled into weights | Direct reference algorithm; deterministic compiler if the program fits its supported language |
| Authored fact memory | Dictionary/rules where applicable and BM25 over the **same fact corpus** |
| Claimed neural efficiency | Matched interface, data access, selection budget, dimensions/dtype, and an explicit allocation/latency boundary |
| Replacement for an existing pipeline | The actual deployed baseline, including any pretrained encoder or retrieval it uses |

Hold corpus, candidate choices, eligibility filters, and scoring rules constant where possible. Record deviations instead of silently giving one baseline better facts. For retrieval, record query construction, tokenization, stemming, stopwords, and ties. A random-label or untrained network control does not replace a competent task baseline.

Report sample counts, accuracy/error on the declared task, abstention coverage, and failures by meaningful slice. For ARC reproduction, keep Easy and Challenge results separate. For a security triager, distinguish an evidence-ranked lead from a confirmed finding; model confidence cannot establish exploitability or applicability.

## Test locality and explanation claims

Use an unchanged rebuild as the control, then change one source record or named weight block. Compare:

- Exact changed tensors/rows and their dependency manifests.
- Predictions on cases that should change, related cases that should remain valid, and a held-out unrelated set.
- Score margins and abstention decisions, not only top labels.
- Downstream aggregates, alternate rows, aliases, and duplicate facts that can preserve the removed information.

Test vocabulary changes separately from fact edits. Stable IDs and seeds reduce incidental drift but do not guarantee behavioral locality; shared rows and normalizers can affect unrelated predictions. Deleting a readable row is not an unlearning guarantee.

For an explanation, trace contributing rows or channels and intervene on them using the fixed evaluator. A plausible writer narrative, readable labels, or source provenance alone does not prove a causal mechanism. Report the tested input domain and counterexamples.

For factual repairs, keep three checks separate: the requested assertion, paraphrases of that assertion, and neighboring assertions that must not change. These are distinct axes in [ROME's CounterFact evaluation](https://rome.baulab.info/). Add dependent consequences when the application needs them; success on paraphrases does not establish multi-step consistency. For sequential edits, retain earlier edit tests and compare edit orders instead of extrapolating from a single successful patch.

## Escalate to a bounded proof when required

Finite samples cannot establish a claim over every real input in an interval. For a small authored piecewise-linear network, enumerate activation regions or use a verifier supported by the actual graph and input constraints. Declare the property separately from the implementation; for example, `0 <= output <= 3` is a range property, not equivalence to a clipping function.

With [Marabou](https://arxiv.org/html/2401.14461v1), encode the admissible input region and the **negation** of the desired property. A satisfying assignment is a counterexample to replay in the deployed runtime; UNSAT concerns only the encoded query. With APIs that accept the desired property directly, follow their documented convention instead of reversing it again. Preserve model/export hashes, constraints, solver version/options, result, and any proof certificate.

Treat timeout or unknown as unresolved. State strict/non-strict inequalities and any error margin explicitly; ruling out violations larger than an epsilon establishes only that tolerance. Check the export against the original forward, unsupported operations, and numerical semantics before calling the result a runtime guarantee. A real-arithmetic argument does not automatically certify quantized or floating-point execution. [alpha-beta-CROWN](https://github.com/Verified-Intelligence/alpha-beta-CROWN) offers bound propagation and branch-and-bound workflows; select a supported verifier only when the required guarantee warrants it, rather than making formal verification a prerequisite for every fixture.

## Measure cost at explicit boundaries

Record writer tokens/time and attempts, build time, and inference cost separately. Do not amortize authoring cost over an unspecified number of future requests.

- **Storage:** serialized bytes, tensor elements, nonzero count, index arrays, buffers, vocabularies, and source/provenance files. Count shared storage once; report sparse index overhead.
- **Runtime memory:** peak resident memory and, when used, allocated/reserved accelerator memory with the input batch. Nonzero counts do not measure dense allocation or peak RAM.
- **Latency:** device, dtype, threads, batch, warmup, repetitions, synchronization, and summary/distribution. Specify whether encoding, loading, transfer, candidate construction, and decoding are included.
- **Hot-kernel timing:** label measurements on already-encoded resident inputs separately from end-to-end requests. Compare identical boundaries and correctness tolerances.

Inspect the actual tensors before quoting parameter ratios: the paper's released pair memory includes dense allocations and integer address tables. Its published resident-input GPU timing does not establish an end-to-end speedup over a pretrained LLM.

## Acceptance record

Deliver the frozen artifact/manifest, supported domain, comparison results, failed cases, edit delta, and cost boundary. Identify the exact source revision and commands used. State one of: accepted for the declared task, useful only as an experimental fixture, or rejected against the baseline. Keep unavailable tests and unreplicated published claims explicit.

## Primary protocol anchors

- [Paper and appendices](https://arxiv.org/html/2611.22055v1): data/feedback, baselines, locality and measurement boundaries. [Pinned release](https://github.com/effl-lab/Weight-Space-Programming/tree/51ce8acf253106cda939d855a5307783d1bd0b6c) omits timing/analysis code and large edited checkpoints; released-model rescoring is narrower than full experimental reproduction.
- [Scorer](https://github.com/effl-lab/Weight-Space-Programming/blob/51ce8acf253106cda939d855a5307783d1bd0b6c/harness/score_model.py) and [BM25 baseline](https://github.com/effl-lab/Weight-Space-Programming/blob/51ce8acf253106cda939d855a5307783d1bd0b6c/bm25/bm25.py): inspect score comparisons and retrieval preprocessing.
- [iWSP data-use audit](https://github.com/csinva/weight-space-programming-autoresearch/blob/4f8eb61580fe9aa307c868d0bdd86914e673ef1f/experiments/evolve/audit_data_use.py): unchanged, label-altered, and input-altered rebuild controls.
- [Original WSP experiment protocol](https://github.com/RikiyaT/lm_understand-logs/blob/4d09ba6d6a7e891dd8063974dfe81b3d78e3494f/exp5_write_from_scratch/README.md): fixed interfaces, feedback restrictions, and raw artifact interpretation.
