# Compile explicit knowledge into sparse memory

Load when the task can be answered from a bounded, reviewable fact set and the target may use tables instead of a prescribed neural architecture. This is a construction method for a constrained classifier or retriever; validate any security-tooling adaptation on its own task.

## Define facts before tensors

Keep source records separate from compiled arrays. Give each fact a stable ID, source locator and revision, applicability conditions, relation direction, polarity, and review status. Preserve conflicting records instead of averaging them into a confident assertion. A scanner hit or writer-generated statement is a candidate for review, not an established fact.

For an artifact-triage prototype, a record might look like this synthetic example:

```json
{
  "fact_id": "format.fixture-07",
  "subject": "fixture-format",
  "relation": "has_header",
  "object": "ABCD",
  "polarity": "positive",
  "applies_to": {"format_revision": "1"},
  "source": {"path": "fixtures/format-spec.txt", "section": "header", "revision": "1"},
  "status": "reviewed"
}
```

Keep exact predicates such as version ranges, byte signatures, and prerequisites in a deterministic eligibility check. Semantic overlap may rank already-eligible evidence; it must not override a failed prerequisite or turn an unknown version into a match. Preserve a direct rule/lookup baseline when the entire task is exact matching.

Freeze a concept map and its normalizer:

- Use stable concept IDs and explicit aliases. Do not conflate negation, direction, units, or version qualifiers with their affirmative/unqualified forms.
- Define unknown tokens, punctuation, multiword concepts, and option-only concepts. Reject malformed records before compilation.
- Record source-to-concept and concept-to-row dependencies. Treat vocabulary changes as structural edits that may affect the entire model.
- If initialization uses randomness, derive row-local seeds from stable IDs; a global random stream can shift unrelated rows after an insertion or deletion.

## Start with a traceable scorer

One fact-matching design uses a vector `k_i` for each eligible fact, a question vector `q`, and a candidate vector `o_c`. In the paper's option-specific construction, `o_c` excludes concepts already present in `q`:

```text
s_c = max over eligible facts i of (k_i dot q) * (k_i dot o_c)
```

Define normalization, weighting, and the empty-fact-set result. This equation is a baseline scoring component, not a reproduction of the paper's full pipeline, which also contains additional scoring and preprocessing logic.

For this overlap scorer, use nonnegative concept weights and keep polarity/contradiction in separate eligibility and result fields. Negating a fact vector flips both dot products, leaving their product positive; negative weights do not implement logical negation. A signed alternative needs an explicitly different scoring rule and contradiction tests.

Return the winning fact IDs and the two overlap terms with each score. Handle empty vectors, no supporting fact, ties, and contradictory support explicitly. Select an abstention policy on development data and report coverage with accuracy; raw overlap scores are neither probabilities nor proof that a statement is true. A source row explains a score contribution, not necessarily the correctness of the answer.

## Test whether the representation distinguishes facts

Run these against the uncompressed scorer before tuning a hash table:

| Fixture | Required observation |
|---|---|
| Same normalized key and eligibility, conflicting targets | Abstention or an unresolved candidate set unless additional context distinguishes the facts |
| Similar keys, different direction/relation; query omits the distinction | Preserve the ambiguity instead of inventing the missing relation |
| Query joins concepts from separate facts | Detect unsupported joint activation; do not infer a new fact from co-activation alone |
| Repeated equivalent facts and near-duplicate distractors | Measure changes in ranking, abstention, and contributors while the intended answer remains fixed |

Keep representational ambiguity, cross-talk between stored facts, and hash collision/truncation as separate failure classes. A larger hash table cannot distinguish identical observable keys; an uncompressed control helps locate the failing layer. Additive memories can be sensitive to fact multiplicity, so define deduplication/weighting rather than assuming duplicate records are harmless.

If substituting a softmax or iterative reader, declare a new inference contract: normalization, projections, temperature, masking, iteration budget, and stopping criterion. Verify target retrieval separately from convergence and score concentration. [Modern Hopfield theory](https://arxiv.org/pdf/2008.02217) gives guarantees under pattern-separation and related assumptions; these do not establish exact recall for arbitrary correlated keys or the pair-addressed table below. Inspect whether an implementation adds learned projections before calling the substituted reader optimizer-free.

## Add associative addressing only when justified

Profile explicit fact matching first. For a bounded pair-addressed memory, define all dimensions before compiling:

| Symbol | Meaning |
|---|---|
| `C` | Number of concepts in the frozen vocabulary |
| `J` | Maximum question concepts selected for pair formation |
| `H` | Number of hash-addressed rows |
| `R` | Stored concept slots per row |
| `A` | First-order concept-to-concept table, shape `C x C` |
| `t_h` | Sparse recalled concept vector stored at address `h` |
| `mu` | Weight of first-order recall |

For each unordered pair of selected concept IDs `a < b`, use a fixed, recorded hash such as `h(a,b) = (a*p + b) mod H`. Accumulate:

```text
r   = sum over selected pairs (a,b) of q[a] * q[b] * t_h(a,b) + mu * A^T q
s_c = o_c dot r
```

Here vectors are columns; a row-vector implementation uses `q @ A`. Check orientation against an asymmetric fixture. The published `mem_assoc2` forward selects at most 16 concepts, giving at most 120 pair reads; this is an implementation choice, not a universal setting.

- Count collisions and row truncation during build. Record which facts lost entries; compare predictions with an uncompressed control before accepting compression.
- Trace merged rows back to every contributing fact. Removing one fact requires recomputing affected aggregates and top-`R` selection, not zeroing a shared address.
- Freeze `H`, `R`, hash parameters, selection/tie rules, and accumulation order in the manifest. Changing them is a new build contract.
- Bound runtime claims by the dimensions held fixed. Pair reads can be bounded while concept encoding, first-order multiplication, and storage still grow with `C`, `H`, or `R`.
- Inspect the representation: an indexed table can still allocate dense `H x R` arrays, and a nominally sparse first-order table may be densified. Measure bytes, including integer IDs.

## Compile and inspect

1. Compile only the approved source snapshot using a deterministic builder. Keep evaluation examples inaccessible to the build process; use the isolation checks in [evaluation](evaluation.md).
2. Validate finite weights, valid IDs, row capacities, tensor shapes, and source coverage. Fail on truncated or dropped facts unless the manifest records an explicitly accepted policy.
3. Save the source revision, vocabulary, compiler/scorer versions, dimensions, dtype, seeds, provenance mapping, and artifact hashes together.
4. Inspect several complete paths: source record -> normalized concepts -> stored entries -> recalled contribution -> candidate score. Include one unknown, one contradiction, and one collision if hashing is enabled.
5. Rebuild unchanged inputs, then patch or remove one fact and compare both tensors and predictions. Load [evaluation](evaluation.md) for locality controls and cost measurement.

At inference, use only the frozen encoder, tables, and scorer. Any writer call, external retrieval, or runtime source update changes the system being evaluated and must be declared separately.

## Primary implementation anchors

- [Weight-Space Programming Doesn't Need Transformers](https://arxiv.org/html/2611.22055v1), sections 3-4 and appendices: fact matching, associative recall, and locality experiments.
- [Fixed associative forward](https://github.com/effl-lab/Weight-Space-Programming/blob/51ce8acf253106cda939d855a5307783d1bd0b6c/wsp/given_archs/memory/mem_assoc2.py) and [released builder](https://github.com/effl-lab/Weight-Space-Programming/blob/51ce8acf253106cda939d855a5307783d1bd0b6c/models/opus/mem_assoc2-arc_blind_K0_r0/build.py): inspect addressing, mixed recall, dense allocations, and row truncation before adapting the design.
