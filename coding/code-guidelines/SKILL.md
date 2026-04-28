---
name: code-guidelines
description: "Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations on LLM coding pitfalls (Dec 2025). Use when writing, reviewing, or refactoring code across any language to avoid hidden assumptions, overengineering, orthogonal edits, vague goals, and sycophantic approval of bad requests. Especially relevant in agent-first workflows where errors are subtle conceptual mistakes rather than simple syntax issues."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
---

# Code Guidelines

Five behavioral principles addressing the most common failure modes of LLM-assisted coding, as identified by Andrej Karpathy (December 2025).

> "The models make wrong assumptions on your behalf and just run along with them without checking. They don't manage their confusion, don't seek clarifications, don't surface inconsistencies, don't present tradeoffs, don't push back when they should."

> "They really like to overcomplicate code and APIs, bloat abstractions, don't clean up dead code — implement a bloated construction over 1,000 lines when 100 would do."

> "They still sometimes change/remove comments and code they don't sufficiently understand as side effects, even if orthogonal to the task."

— Karpathy, [Dec 2025](https://x.com/karpathy/status/2015883857489522876)

**Context:** With LLM agents handling the majority of code in agent-first workflows, errors are no longer simple syntax mistakes but *subtle conceptual errors that a slightly sloppy, hasty junior dev might do* — harder to spot, higher stakes. Watch the output like a hawk.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks (obvious one-liners, simple typos), apply judgment — not every change needs the full rigor.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State assumptions explicitly. If uncertain, ask rather than guess.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask for clarification.
- Resist sycophancy: if the request is flawed or ambiguous, say so rather than silently complying.

Failure mode: silently picking an interpretation and running 200 lines in the wrong direction.

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Don't leave dead code behind.

The test: would a senior engineer say this is overcomplicated? If yes, simplify.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless explicitly asked.

The test: every changed line should trace directly to the user's request.

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

> "LLMs are exceptionally good at looping until they meet specific goals. Don't tell it what to do, give it success criteria and watch it go. Change your approach from imperative to declarative to get the agents looping longer and gain leverage."
— Karpathy

Transform imperative tasks into verifiable goals:

| Imperative (weak) | Declarative goal (strong) |
|---|---|
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Fix the bug" | "Write a test that reproduces it, then make it pass" |
| "Refactor X" | "Ensure tests pass before and after" |
| "Make it faster" | "Benchmark first; target < 100ms p99; verify no regression" |

For multi-step tasks, state a brief plan before starting:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria enable independent looping. Weak criteria ("make it work") require constant clarification.

---

## 5. Self-Review Before Returning

**Review your own output with fresh eyes before marking it done.**

After generating a solution:

- Re-read the diff: does every changed line trace directly to the request?
- Check for speculative additions, style drift, and orthogonal refactors.
- Verify that the success criteria defined in step 4 are actually met.
- If tests were required, confirm they pass.

Effective practice: *review the output with a fresh context window before finalizing* — this catches issues that human review often misses.

---

## Signs These Guidelines Are Working

- Diffs contain only requested changes — no drive-by improvements.
- Code is simple the first time — fewer rewrites due to overengineering.
- Clarifying questions come before implementation, not after mistakes.
- PRs are clean and minimal — no speculative features or style normalization.
- The agent pushes back on flawed requests rather than silently complying.
- Self-review catches issues before human review is needed.

---

## Resources

| File | When to load |
|---|---|
| `references/examples.md` | Concrete before/after examples for all five principles |
