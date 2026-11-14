---
name: software-guidelines
description: "Implement and review scoped code changes in a repository. Use for patch impact, dependent caller updates, repository conventions, and preserving unrelated work; use software-architecture for structural design and simplification decisions."
license: MIT
metadata:
  author: AeonDave
  version: "1.3"
---

# Software Guidelines

Deliver a complete, reviewable change for the requested outcome. Apply this workflow to security tooling and its supporting code, from a local fix to a change spanning several modules.

## Inspect the edit context

- Read applicable instructions, inspect worktree status and relevant diffs, and examine the affected implementation before editing. Identify pre-existing changes and preserve them, including in files the task also touches. Re-read changed regions if another writer may have updated them; do not reset unrelated work.
- Follow the affected entry point through relevant callers, state changes, side effects, and tests. Verify that APIs and dependencies used by the patch exist in the checked version; distinguish existing capabilities from interfaces being introduced.
- Identify the requested behavior, what must remain stable, and the smallest useful acceptance check. Use repository conventions for routine choices. If an unresolved decision changes scope, a public contract, or data integrity, use `design-before-implementation`; continue independent authorized work.

## Make the change complete and focused

- Tie each part of the diff to the outcome or a necessary supporting change. Include required callers, tests, configuration, and documentation even when the request names only one function. Avoid unrelated features, dependency upgrades, formatting, and cleanup.
- When a symbol, signature, or data shape changes, inspect both its definition and consumers. Check indirect uses such as exports, registration strings, configuration keys, and serialized fields where relevant; a compile pass or literal-name search may miss these.
- Update the maintained source of generated artifacts and use the repository's generation workflow when required. Inspect generated changes for consistency and unrelated churn; do not patch only a derived copy that regeneration will overwrite.
- Reuse an existing convention or helper when its behavior fits. Do not reuse a similarly named abstraction without checking its error, ownership, and side-effect contracts. Add dependencies or abstractions only for a concrete requirement or boundary.
- Keep necessary validation, authorization, error propagation, and cleanup. Do not remove safeguards merely to shorten the patch or assume a failure path is impossible without establishing its preconditions.
- Allow requested simplification or a refactor needed to implement the change safely. Keep its preservation contract explicit and separate it from behavior changes where useful for review. Load [software-architecture](../software-architecture/SKILL.md), then its simplification reference when making those structural or readability decisions.
- Remove imports, parameters, helpers, and temporary diagnostics made obsolete by this change. Leave unrelated pre-existing cleanup for a separately scoped task; mention it only when it affects the outcome or poses a material risk.

## Verify and review the delivered patch

- Check the changed behavior and its affected consumers. Prefer an existing relevant check or reproducer; add a regression test when it protects a real behavior. Use `testing-reliability` when assertions, mocks, timing, or flaky results may mislead.
- For performance work, measure the relevant workload before changing it when practical; disclose an unavailable baseline and measurement limits. Use a user or project target when one exists; otherwise report the measured change and tradeoffs without inventing an acceptance threshold.
- Review the final diff against the requested outcome and initial worktree state. Look for missed consumers, accidental behavior changes, generated-file drift, obsolete code, and changes that belong to someone else. Keep fixes and their necessary supporting artifacts together.
- Use `verification-before-completion` for required checks, evidence reuse, failed gates, and completion wording. Passing checks support only the behavior they cover. Finish authorized implementation rather than stopping after a proposal or adding an approval gate for routine edits.

## Load deeper guidance when needed

- `software-architecture` — module boundaries, public contracts, state ownership, architectural tradeoffs, or behavior-preserving simplification.
- `implementation-planning` — dependent work, shared-file ownership, or a handoff that needs an executable plan.
- `dependency-discipline` — adding or upgrading a dependency, wiring CI installs, or responding to a supply-chain incident.
- `secure-tooling-implementation` — writing or reviewing a tool that processes untrusted input (scanner, loader, parser, agent).
- The relevant language pattern/testing skill — syntax, idioms, and executable checks for the actual stack.

For change sizing and separating substantial refactors, apply [Google's focused-change guidance](https://google.github.io/eng-practices/review/developer/small-cls.html#what-is-small) to the logical change and its consumers; preserve the repository's own review and testing policy.
