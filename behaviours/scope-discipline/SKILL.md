---
name: scope-discipline
description: "Stay on the requested task: fix what was asked, log drive-by findings instead of fixing them, and treat discovered-but-out-of-scope issues as a ledger entry. Use mid-task when tempting adjacent problems, refactor opportunities, or extra features appear — and when a request grows beyond its original authorization."
license: MIT
compatibility: "Agent workflow guidance for coding, security assessments, and research tasks."
metadata:
  author: AeonDave
  version: "1.0"
  category: behaviours
---

# Scope Discipline

Complete the asked task; treat everything else discovered on the way as **ledger entries, not work**. Compounded "while I'm here" fixes produce a late deliverable and an unreviewable diff.

## When to activate

- A task is in progress and adjacent problems/opportunities keep appearing
- You notice the diff growing beyond what the request implied
- The request itself grows mid-flight ("also add…", "while you're at it…") without a re-planning step
- You are about to refactor, rename, or "improve" something the task did not ask about

## The discipline

1. **Fix what was asked. Finish it. Verify it.** A drive-by fix that delays the deliverable costs more than the bug it repairs.
2. **Ledger, don't linger.** Every out-of-scope finding gets one line in the handoff/final report: what it is, where, severity, suggested fix. Then continue the task. The ledger is how drive-bys stop being lost work without becoming scope.
3. **The three-question test** for any tempting detour:
   - Is it blocking the deliverable? (blocking → in scope, do it)
   - Is it destructive/expiring (a payload staged now is gone later)? (expiring → flag, ask)
   - Neither → ledger entry.
4. **Growing requests need a re-plan, not silent growth.** "Also do X" mid-flight is a new task: state the added scope, the impact on the deliverable, and get acknowledgment — or deliver the original first. Scope grows by decision, not by accretion.
5. **YAGNI on deliverables.** Build what the task needs, not what a future task might need. Unused flexibility is unreviewed code in a security tool — attack surface without a user.
6. **The report states the boundary.** "Done: A, B. Not done, found: C (ledger)." A reviewer must never discover unrequested changes inside a diff.

## Offensive-work application

- A credential found while hunting the actual objective → ledger it for later, continue the objective. Stopping to dump everything at the first cred is the classic scope-collapse.
- An unexpected vulnerable host → note it; unplanned pivots need authorization, not momentum.
- Findings ledger doubles as the next-engagement backlog — nothing discovered is lost, nothing unplanned is touched.

## Related

- `design-before-implementation` — the pre-task phase that *sets* the scope; this skill keeps it mid-task.
- `loop-control-and-pivots` — stop conditions for unproductive work inside scope.
- `handoff` — where the findings ledger is delivered.
- `implementation-planning` — when grown scope deserves a real plan.
