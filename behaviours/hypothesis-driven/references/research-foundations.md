# Research Foundations

Use this source trail when the investigation needs stronger rationale than the compact workflow in `SKILL.md`. Do not load it by default; load it when updating the method, explaining why the discipline matters, or choosing among reduction, slicing, postmortem, or issue-tree tactics.

## Scientific debugging

- Source: The Debugging Book, "Introduction to Debugging" — <https://www.debuggingbook.org/html/Intro_Debugging.html>
- Source: Andreas Zeller, *Why Programs Fail* — <https://www.whyprogramsfail.com/>
- Practice impact:
  - Treat debugging as a scientific loop: observe, hypothesize, predict, experiment, refine.
  - Keep an explicit log because memory collapses failed hypotheses into a false narrative.
  - A useful diagnosis must explain both causality and incorrectness: how the faulty state leads to the failure, and why that state violates intended behavior.

## Assertions, contracts, and invariants

- Source: The Debugging Book, "Assertions" — <https://www.debuggingbook.org/html/Assertions.html>
- Practice impact:
  - Add preconditions, postconditions, and invariants as probes that fail closer to the defect than the final symptom.
  - Assertions are experiments, not input validation. Keep them side-effect free and do not make production logic depend on them.
  - Good invariants rule out entire state regions and turn vague "bad behavior" into a precise falsifier.

## Delta debugging and reduction

- Source: The Debugging Book, "Reducing Failure-Inducing Inputs" — <https://www.debuggingbook.org/html/DeltaDebugger.html>
- Practice impact:
  - Reduce large failing inputs, traces, code snippets, PCAP streams, or configs before deep analysis.
  - Reduction lowers cognitive load, shortens execution, clarifies duplicate reports, and reveals the failure-inducing difference between passing and failing cases.
  - The failure oracle must be precise. If reduction changes the error class, output, or oracle, mark it unresolved instead of accepting a misleading minimum.

## Slicing and origin tracking

- Source: The Debugging Book, "Tracking Failure Origins" — <https://www.debuggingbook.org/html/Slicer.html>
- Practice impact:
  - Ask two questions for any wrong value: where did this value come from, and why did this statement execute?
  - Data dependencies identify value origins; control dependencies identify decisions that made a path execute.
  - Dynamic slices rule out code and state that could not have affected the failing run, which keeps investigation focused.

## Issue trees and MECE decomposition

- Source: Untools, "Issue trees" — <https://untools.co/issue-trees/>
- Source: Arnaud Chevallier, "Draw question maps" — <https://powerful-problem-solving.com/build-issue-trees/>
- Source: Crafting Cases, "The Definitive Guide to Issue Trees" — <https://www.craftingcases.com/issue-tree-guide/>
- Practice impact:
  - Use a diagnostic "why" tree before a solution "how" tree.
  - Branches should be MECE enough to avoid blind spots and overlap, but also insightful and falsifiable enough to guide tests.
  - Prioritize branches by expected information gain and ability to eliminate whole regions of the problem space.

## Ladder of inference and assumption control

- Source: Untools, "Ladder of inference" — <https://untools.co/ladder-of-inference>
- Practice impact:
  - Slow down jumps from selected data to action. Insert the missing reasoning steps: interpretation, assumption, conclusion.
  - When disagreement or uncertainty rises, walk down the ladder to raw observations and rebuild upward with explicit assumptions.
  - Promote the riskiest assumption to a hypothesis and test it early.

## SRE postmortems and incident learning

- Source: Google SRE Book, "Postmortem Culture" — <https://sre.google/sre-book/postmortem-culture/>
- Source: Google SRE Workbook, "Postmortem Culture" — <https://sre.google/workbook/postmortem-culture/>
- Source: Google SRE Workbook, "Results of Postmortem Analysis" — <https://sre.google/workbook/postmortem-analysis/>
- Source: Google SRE Book, "Example Postmortem" — <https://sre.google/sre-book/example-postmortem/>
- Practice impact:
  - Keep analysis blameless and evidence-backed: timeline, impact, root cause, trigger, contributing factors, detection, mitigation, and action items.
  - Distinguish trigger from root cause. A traffic spike, deploy, or operator action may activate a latent system weakness without being the full cause.
  - Action items should be specific, owned, measurable, and aimed at prevention, faster detection, mitigation, or better process.

## Agentic debugging patterns

- Source: `schickling/dilagent` README — <https://raw.githubusercontent.com/schickling/dilagent/main/README.md>
- Source: `doraemonkeys/claude-code-debug-mode` README — <https://raw.githubusercontent.com/doraemonkeys/claude-code-debug-mode/master/README.md>
- Source: `franzenzenhofer/debug-mode-skill` SKILL.md — <https://raw.githubusercontent.com/franzenzenhofer/debug-mode-skill/main/SKILL.md>
- Practice impact:
  - Reproduce before fixing, then generate several hypotheses instead of chasing the first stack trace.
  - Use hypothesis-tagged instrumentation, for example `H3 branch=slow_path`, so logs remain attributable across tool calls and agent turns.
  - Write hypothesis logs and runtime logs to durable scratch/session files when state matters; ephemeral chat summaries are not enough for long investigations.
  - Validate with red-to-green evidence and, when safe, a counter-experiment that makes the failure return.
