---
name: loop-control-and-pivots
description: "Retry discipline for stuck work. Use when an approach fails repeatedly, when grinding a side problem (env setup, missing tool, credentials, file transfer) instead of the goal, or when a debug/exploit/build attempt is not converging. Enforces evidence-first pivots, a 3-strikes rule, and honest BLOCKED reporting over thrash."
license: MIT
compatibility: "AgentSkills-compatible loop-control guidance for coding, debugging, security testing, and research."
metadata:
  author: AeonDave
  version: "1.0"
---

# Loop Control and Pivots

Repeating a failing approach burns budget and hides progress. Fail fast, pivot on evidence, and stay
on the goal.

## Activation triggers

- The same approach has failed ~2–3 times (same error, same dead end).
- You are grinding a **side problem** — env setup, a missing tool, credentials, a file transfer,
  working around tooling — instead of the actual deliverable.
- A debug / exploit-dev / build / research thread is not converging.

## The rules

1. **3-strikes → dead**: after ~3 evidence-based attempts at one approach, mark the path dead. Do not
   re-trigger it blindly; quote the failure and switch to a **different** test, not a repeat.
2. **Pivot on evidence**: `failed path → quote the exact failure → next shortest path`. Each retry
   must change a variable, not just re-run hope.
3. **Don't grind side quests**: a secondary problem gets a **bounded** attempt. If it doesn't yield,
   surface `[BLOCKED: need X]` and pivot to productive work rather than sinking the run into it.
4. **Hold the objective**: every step ties to the success signal. If you've drifted onto a
   sub-problem, name the drift and return to the goal (or escalate for the missing capability).
5. **Escalate honestly**: when genuinely stuck after pivots and local tests, load the narrowest
   hint/research support skill or hand back an honest blocker **with everything derived so far**
   (offsets, leaks, partial output) — never a fabricated success.

## Anti-patterns

| Smell | Instead |
|---|---|
| Re-running the same command hoping it works | change an input/assumption, or pivot |
| Two hours on env/tooling for a 10-minute task | bounded attempt → `[BLOCKED: need X]` → pivot |
| "Almost there" for the 5th identical attempt | quote the failure, mark the path dead, pivot |
| Silent give-up | report the blocker + partial results + next smallest step |

## Blocked report shape

`[BLOCKED: need X]` — what you were trying, the exact failure (verbatim), what you derived, and the
one capability/decision that would unblock it. Pair with `evidence-before-claims` so the blocker is
as auditable as a success would be.
