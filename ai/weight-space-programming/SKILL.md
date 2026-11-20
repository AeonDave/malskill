---
name: weight-space-programming
description: "Read, author, or repair model weights directly without an optimizer. Use for explicit neural programs, sparse fact memories with fixed inference, and traceable classifiers or bounded model-audit fixtures for security tasks."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# Weight-Space Programming

Treat model parameters as an authored program: specify their meaning, construct or edit them, and verify the resulting computation. Apply this to a bounded security-support task such as an interpretable artifact classifier, an evidence-backed fact memory, or a model-audit fixture.

## Establish the contract

Record the task, admissible inputs, expected outputs, failure or abstention behavior, and acceptance oracle before authoring parameters. Compare with a direct rule, lookup, or search baseline; select a neural or associative representation only when its properties serve the task.

Identify which object may change:

- **Fixed architecture:** freeze preprocessing, forward operations, and decoding; author only the allowed parameters.
- **Architecture design:** choose a representation and build process, then freeze the runtime before evaluating the resulting artifact.
- **Existing model repair:** preserve the original checkpoint and isolate a specific failure; constrain the patch and check unaffected behavior.

Define what the writer may inspect: specifications, source facts, example labels, tensors, probes, and validation scores. Keep the final evaluation outside this feedback channel.

## Keep the computation inspectable

1. Give input features, intermediate channels, tensor axes, and outputs explicit meanings. Preserve mappings between source statements, generated parameters, and runtime outputs.
2. Separate authoring/build code from the deployed inference implementation. Save parameters or compiled tables as versioned data with their schema and provenance.
3. Run the frozen inference path from the saved artifact. Do not hide the target algorithm in preprocessing or a task-specific forward branch while claiming the weights implement it.
4. Diagnose failures through intermediate values and controlled interventions. Revise the smallest supported part, then repeat targeted and unaffected-case checks.
5. Preserve unsuccessful candidates and feedback when comparing authoring strategies; report selection and evaluation budgets.

If the task permits programmed preprocessing or runtime rules, document them as part of the system. Evaluate the whole pipeline and distinguish those rules from computation represented by weights.

## Keep claims within the evidence

- **No optimizer** does not mean **no feedback**: validation-guided revisions and candidate selection are adaptive. Report them separately from gradient training or fitted parameters.
- A pretrained writer contributes learned knowledge. Describe what was trained, written, retrieved, or compiled; do not call the complete system training-free because the target received no gradient updates.
- A named channel or readable fact is an interpretation to test. Demonstrate output dependence with interventions before claiming causality or local edit effects.
- Changes to an authored fact table do not establish erasure from a pretrained writer or another model. Route removal claims to the [unlearning reference](../model-finetuning/references/unlearning.md).
- Bounded fixtures and candidate-ranking results do not establish general language capability, vulnerability applicability, or production detection quality. Validate the intended security task independently.

## Load the required workflow

| Reference | Load when |
|---|---|
| [references/neural-design.md](references/neural-design.md) | Writing weights for a fixed neural architecture, interpreting tensor roles, repairing an existing model, or choosing a compiler-generated fixture. |
| [references/sparse-memory.md](references/sparse-memory.md) | Compiling authored facts and concepts into a sparse memory with a fixed scoring procedure. |
| [references/evaluation.md](references/evaluation.md) | Reproducing results, comparing methods, testing edit locality, or making accuracy, efficiency, and deployment claims. |

Use [model-merging](../model-merging/SKILL.md) for checkpoint arithmetic, [model-finetuning](../model-finetuning/SKILL.md) for gradient adaptation, and [abliteration](../abliteration/SKILL.md) for residual-direction edits. Use [model-scanning](../model-scanning/SKILL.md) before loading untrusted artifacts and [pytorch](../pytorch/SKILL.md) for tensor/checkpoint mechanics.

## Deliver and verify

For construction or repair, deliver the input/output contract, exact forward and decoder implementation, authored source or patch, compiled artifact, provenance manifest, and evaluation results. Include the permitted feedback, baseline comparison, unresolved cases, and tested runtime/precision.

Construction or repair requires a reproducible build or patch, successful execution from the saved artifact, and acceptance checks on inputs not used to revise it. For read-only weight interpretation, deliver the proposed computation, tensor evidence, and checks permitted by the protocol; if execution is forbidden or unavailable, mark the interpretation unverified by execution. If only a hypothesis or toy fixture was validated, identify that scope.

## Method source

- [Weight-Space Programming Doesn't Need Transformers](https://arxiv.org/html/2611.22055v1) — architecture authoring, sparse memories, and the evaluation conditions underlying the method. Load the workflow references for operational guidance.
