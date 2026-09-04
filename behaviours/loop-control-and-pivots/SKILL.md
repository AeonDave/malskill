---
name: loop-control-and-pivots
description: "Retry discipline for stuck work. Use when an approach fails repeatedly, when grinding a side problem (env setup, missing tool, credentials, file transfer) instead of the goal, or when a debug/exploit/build attempt is not converging. Enforces evidence-first pivots, a 3-strikes rule, and honest BLOCKED reporting over thrash - while resisting premature give-up: pivot the dead path, but hold the objective while budget and untried approaches remain."
license: MIT
compatibility: "AgentSkills-compatible loop-control guidance for coding, debugging, security testing, and research."
metadata:
  author: AeonDave
  version: "1.1"
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
   re-trigger it blindly; quote the failure and switch to a **different** test, not a repeat. New
   evidence or partial progress resets the count — strikes track *repeated identical failure*, not a
   path that is still yielding signal.
2. **Fail fast on non-retryable failures**: some errors never resolve by repetition — auth/permission
   denials, 404/not-found, malformed-input or unsupported-feature rejections. Spend zero retries: fix
   the cause, pivot, or surface `[BLOCKED: need X]` at once instead of burning the 3-strikes budget.
3. **Pivot on evidence**: `failed path → quote the exact failure → next shortest path`. Each retry
   must change a variable, not just re-run hope.
4. **Don't grind side quests**: a secondary problem gets one bounded attempt (see Budgets). If it
   doesn't yield, surface `[BLOCKED: need X]` and pivot to productive work rather than sinking the
   run into it.
5. **Hold the objective**: every step ties to the success signal. If you've drifted onto a
   sub-problem, name the drift and return to the goal (or escalate for the missing capability).
6. **Escalate honestly**: when genuinely stuck after the recovery pass, pivots, and local tests, load the narrowest
   hint/research support skill or hand back an honest blocker **with everything derived so far**
   (offsets, leaks, partial output) — never a fabricated success.

## Persist on the objective (the other half of fail-fast)

Fail-fast applies to a **path**, never to the **objective**. A dead path means pivot; it does not
license abandoning the goal. The dominant failure mode on capable models against hard targets is
*premature surrender* — bailing with "stuck" / "need a tool" / BLOCKED while budget and untried
attack-classes remain.

- **Two levels, opposite reflexes.** Pivot the vector/class fast (3-strikes, above); keep attacking
  the *objective* until the run budget is committed **or** every distinct attack-class has been tried
  and killed with evidence. Do not collapse "this path is dead" into "I am stuck."
- **Kill paths with tests, not proofs.** "Dead" requires a *failing live experiment*. A reasoning-based
  "this can't work / is unreachable / is impossible" verdict is a hypothesis, not a kill — abandoning
  the *correct* vector on a deductive impossibility is a top cause of losing solvable targets. When
  your attempts have become impossibility *arguments* instead of *experiments*, the pivot is to dynamic
  probing (hook the candidate call site, fuzz the threshold/length/format), not deeper static reasoning.
  (See `hypothesis-driven` → "'Impossible' is a hypothesis".)
- **Recovery pass before BLOCKED.** On a solvable target, before you report blocked: (a) diff current
  state vs your hypothesis and probe what is still *unverified*; (b) re-read recon for missed env
  vars, comments, headers, versions; (c) try the *simplest* attack of the class, not the cleverest;
  (d) send wild/empirical payloads — errors leak parser and structure.
- **What BLOCKED actually means.** A genuine blocker is a *missing external capability* — credential,
  authorization, access, or a tool you cannot obtain — not "out of ideas." Out-of-ideas → recovery
  pass or a hint/research skill; missing-capability → the BLOCKED report shape below.

## Budgets and hard stops

Set caps before starting. Trip a cap → stop, quote it, pivot or report.

- **Tool-calls per approach**: ~5–10 calls to prove or kill one hypothesis. Past that: path is dead.
- **Side-quest cap**: ~10 tool-calls or ~15 min on env/tooling/creds/transfer. Past that:
  `[BLOCKED: need X]`.
- **Wall-clock / token budget**: when ~70% of the run budget is spent, drop low-yield branches and
  reserve remainder for verification and reporting.
- **MCP / network retry cap**: at most 2 automatic retries on the same call with the same args.
  The third attempt must change the call, target, or route — otherwise mark it dead.
- **Sub-agent runaway**: kill and reassign a delegated worker when it exceeds its budget, produces
  no new artifacts across two status reports, or drifts off the stated goal.

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
