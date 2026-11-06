# Patch-diff and variant research

Load when a patch or established root cause provides a lead for comparing revisions, testing a fix, or finding related instances.

## Explain the semantic change

1. Identify the exact before/after revisions or binary builds and configuration. For pairs selected from a package or binary index, record the selection basis and verify the product branch, architecture, and relationship to the fix. The nearest older version or a fallback pair is only a lead; it may not bracket the fix ([PatchWatch pair selection](https://github.com/originsec/patchwatch/blob/5a221622b587a80ed967ebf3fa656f51467f378d/crates/patchwatch/src/winbindex/client.rs#L116-L172)). Check whether compiler, dependency, feature, or packaging differences could explain the comparison.
2. Separate security-relevant changes from formatting, relocation, compiler output, and unrelated refactoring. Preserve meaningful constants, sizes, signedness, and comparison conditions; normalization can erase the fix itself. A small diff or added check alone does not establish a security correction ([SPAIN, §§II–III, V](https://songfu1983.github.io/publications/icse17.pdf)).
3. State the old assumption, the changed check/state transition, the input or sequence that distinguishes them, and the property the patch appears to enforce. Trace from the triggering input to the changed operation, across functions when needed. Include relevant added/deleted functions and changed call sites: a fix may move into a new helper omitted from a modified-function shortlist. Read callers, tests, accepted/rejected paths, and check ordering before treating the patch as sufficient.
4. Apply the same relevant normal and suspect cases to both revisions when executable. Verify that the case reaches the intended path: a fixed build failing during setup or rejecting every input does not demonstrate a correct fix.
5. Keep a patch-derived hypothesis separate from a demonstrated vulnerability. If builds cannot be reproduced, preserve the static argument and the exact missing comparison.

## Check the patch in another binary

Use when source or version labels cannot establish whether a target build contains the relevant correction.

- Bind the old, fixed, and candidate artifacts to their own build identities. Locate corresponding functions with available structural, call, string, and data-flow evidence; inspect block correspondence in context, especially for duplicated code.
- Compare the candidate's patch-relevant conditions and operations against **both** old and fixed versions. Whole-function similarity can remain high after a small security fix; use it to locate candidates, then inspect the changed region and its paths ([BinXray, §§2–3, 4.6](https://chenbihuan.github.io/paper/issta20-xu-binxray.pdf)).
- Assess semantic equivalence on the relevant paths, including alternative fixes and backports. Check that the enforcing condition protects the relevant operation on the path under examination. A moved or rewritten guard need not resemble the original patch.
- Report evidence matching the old behavior, matching the correction, or unresolved/mixed. A missing function or ambiguous mapping is not proof that the patch is absent. Record compiler/architecture differences, inlining, or unrelated changes that prevent a reliable comparison.
- Keep patch presence, reachable vulnerable behavior, and impact as separate conclusions. Validate behavior when possible; a local match does not establish the status of other callers, components, or variants.

## Search the root-cause family

Start from an established instance. Describe the mechanism independently of its spelling: for example, validation before a meaning-changing transformation, inconsistent ownership checks across entry points, or a lifetime assumption that fails on one error path.

- Calibrate the search against the known instance and a guarded look-alike. If the known instance is absent, inspect search coverage and the model before drawing conclusions ([Trail of Bits, variant analysis](https://github.com/trailofbits/skills/blob/470419e16f97e112d01fc32f4898aea1755015d9/plugins/variant-analysis/skills/variant-analysis/SKILL.md)).
- Generalize one relevant dimension at a time: alternate callers, duplicated implementations, other consumers, types, state transitions, or boundary conditions. Choose structural, data-flow, binary, or textual search according to the question and available tools.
- Record included revisions/files and exclusions, ignored paths, unresolved calls, and model assumptions. Compare semantic matches, not just counts or line numbers.
- For each candidate, re-establish input control, reachability, the failed invariant, and effect. Shared syntax does not make two vulnerabilities equivalent; a correct caller or postcondition may distinguish them.
- A successful fix for the original trigger does not establish completeness. Test other ways to violate the same property and relevant adjacent boundaries; distinguish a missed variant from a separate cause.

Choose the stopping point by unresolved evidence and useful search yield, not a fixed match count or noise percentage.

## Retain the result

Keep the original cause, search/query version and coverage, minimal before/after comparison, and each candidate's disposition with evidence. Separate confirmed related instances, ruled-out look-alikes, and unresolved candidates. Name the residual condition when a patch is incomplete; do not infer novelty or a CVE assignment from a new match.
