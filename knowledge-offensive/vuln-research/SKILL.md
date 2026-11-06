---
name: vuln-research
description: "Discover and validate vulnerabilities in applications, services, source code, binaries, and firmware. Use for assessment coverage and scanner-finding validation, bug-bounty investigations, patch-diff and variant analysis, and reproducible security findings."
license: MIT
metadata:
  author: AeonDave
  version: "2.1"
---

# Vulnerability Research

Turn a research lead into a defensible finding, a rejected hypothesis, or a precise unanswered question. Work in short loops: **hypothesis → discriminating experiment → evidence → next decision**. Keep updates brief; retain inputs, traces, and decisions in the task workspace.

## Establish the target and the security property

- Identify the artifact or deployment actually examined: revision/build, configuration, architecture/runtime, entry points, and relevant dependencies. Bind observations to that identity.
- Exercise or inspect a normal operation first. A running process, responding port, or successful tool invocation does not establish that the relevant application path works.
- State what must remain true: who may act on which object, what data may cross a boundary, what memory/state must remain valid, or which operation must be atomic. Distinguish a documented requirement from an inferred assumption. Normal traces suggest properties; they do not establish the entire specification ([Felmetsger et al., §§3–4](https://www.usenix.org/event/sec10/tech/full_papers/Felmetsger.pdf)).
- Read existing advisories, patches, tests, and design notes when they resolve a specific uncertainty. Absence from public search does not establish novelty. Do not require a literature survey before inspecting a useful local lead.

## Select the next hypothesis

Map the relevant chain: **controlled input or action → reachable processing → security decision/state → observable consequence**. Include callers, transformations, checks, ownership, and error paths needed to explain it.

Prioritize plausible input control, consequential boundaries, changed or complex code, and the cost of resolving uncertainty. Language, a suspicious API, or a severity score alone does not select the best research path.

For each active lead, record one proposed failure, supporting evidence, the strongest alternative explanation, and the observation that would distinguish them. Follow one consequential unknown to an answer; expand to adjacent paths when the result gives a reason. When parallel work is useful, separate independent hypotheses and artifacts, with one integration owner.

## Run a discriminating experiment

1. Define the expected secure result and the observation that would contradict it. Use a normal case and a meaningful contrasting case; vary identity, input, sequence, timing, or configuration deliberately.
2. Use the smallest suitable analysis: source/data-flow inspection, a request sequence, debugger trace, binary instrumentation, emulation, symbolic reasoning, or fuzzing. Select available tools by capability; GDB and Ghidra are examples, not dependencies.
3. Verify that the experiment reaches the intended path. Record the actual response **and relevant state/effect**; an HTTP code, scanner label, crash count, or success banner is insufficient by itself.
4. Separate path reached, defect triggered, and effect detected. Record only distinctions the available evidence can support; coverage or a crash does not establish exploitable impact ([Magma, §4.3](https://hexhive.epfl.ch/publications/files/21SIGMETRICS.pdf)).
5. Preserve exact inputs, initialization/reset, observations, and changed conditions. For intermittent results, record successful/total attempts and investigate the dependency; neither one success nor one failure establishes reliability.

If execution is unavailable, continue useful static analysis and identify the missing runtime check. If the normal control fails, diagnose the experiment before attributing the test failure to the target. A negative test closes only the tested conditions, not every entry path.

## Establish cause and challenge the conclusion

Trace the result back to the first violated condition. Check whether input control and reachability survive wrappers, validation, privilege changes, parsing, state transitions, and build-specific behavior. Check the strongest counterexample with the same care as the positive case; do not invent an unseen guard or assume one is absent.

Minimize the input or operation sequence while retaining the relevant effect. Deduplicate by supported root cause; stack signatures and similar output are provisional groupings. Crash totals do not measure distinct vulnerabilities ([Klees et al., §7](https://obj.umiacs.umd.edu/acm_ccs18/Fuzz_testing_CCS18.pdf)).

Keep **observed impact**, additional plausible impact, and untested prerequisites separate. A crash may establish an availability issue under demonstrated conditions; it does not establish code execution. A fix suggestion should address the violated property, with a regression check that would distinguish the fix from an unrelated behavior change.

## Load depth only for the current question

| Need | Load |
|---|---|
| Plan vulnerability checks from an asset inventory or validate scanner findings | [assessment-coverage.md](references/assessment-coverage.md) |
| Binary evidence, direct-call harnesses, or emulated results need validation | [binary-experiments.md](references/binary-experiments.md); [reversing-technique](../../offensive-techniques/reversing-technique/SKILL.md) for artifact analysis; [emulation-technique](../../offensive-techniques/emulation-technique/SKILL.md) for execution models |
| Analyze a patch diff, check a fix in another build, or find related instances | [patch-and-variant-analysis.md](references/patch-and-variant-analysis.md) |
| Trace source-level data/control flow or run a fuzzing campaign | [source-review-technique](../../offensive-techniques/source-review-technique/SKILL.md) or [fuzzing-technique](../../offensive-techniques/fuzzing-technique/SKILL.md), respectively |
| Resolve published claims, affected versions, or a downloaded PoC | [deep-research-offensive](../deep-research-offensive/SKILL.md), [cve-search](../cve-search/SKILL.md), or [poc-weaponization](../poc-weaponization/SKILL.md), respectively |

Use the selected tool's skill for syntax. If research stalls, load [known-problem-hint-research](../../knowledge/known-problem-hint-research/SKILL.md) for a focused outside lead. Keep research state in the existing notes system; use [1337's task notes](../../behaviours/1337/references/brain.md) when continuity across experiments or sessions needs structure.

## Deliver a reproducible result

Lead with the finding or current decision. Include only what another researcher needs:

- Exact target/build and conditions; affected input, actor, object, or entry point.
- Root cause and security property, linked to source locations or module-relative addresses.
- Minimal reproduction and control, expected versus observed results, and retained evidence paths.
- Demonstrated impact, remaining prerequisites, and checks not performed.
- Next discriminating check, or the fix principle and regression check when established.

Label evidence as static or runtime-observed; distinguish a candidate from a reproduced finding. Report `not reproduced` as a test outcome, not automatically a rejection. For a rejected lead, preserve the counterevidence and condition that would justify reopening it. Do not bury one supported finding in a list of speculative weaknesses.
