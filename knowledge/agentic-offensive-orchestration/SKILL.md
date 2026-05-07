---
name: agentic-offensive-orchestration
description: "Coordinate multi-agent or multi-threaded offensive-security research and development work. Use for scoped recon analysis, exploit triage, payload/tool development, code review, and large skill curation tasks that can be split into independent subproblems. Avoid for simple one-step tasks where orchestration adds overhead."
license: MIT
compatibility: "Agent workflow guidance for local repositories and authorized security work. Optional: git worktrees for isolated branches."
metadata:
  author: AeonDave
  version: "1.1"
---

# Agentic Offensive Orchestration

Use this skill when one context window would blur scope, evidence, and hypotheses.

## Core rule

Split by **independent decision boundary**, not by convenience. Each subagent or parallel thread must have a self-contained objective, inputs, limits, and output format.

## Workflow

1. **Scope gate**: restate target boundaries, allowed actions, noise/destructive limits, and success criteria.
2. **Task decomposition**: separate recon, source review, exploitability, tooling, validation, and reporting when they can proceed independently.
3. **Context packet**: give each worker only what it needs: artifacts, paths, commands, constraints, and exact deliverable.
4. **Parallelize only safe independence**: do not parallelize tasks that mutate the same repo, target state, account, database, or exploit chain step.
5. **Review gate**: validate outputs against evidence, scope, and contradictions before merging conclusions.
6. **Synthesis**: produce one operator-facing summary with facts, uncertainties, and next actions.

## Good splits

- One worker maps scanner findings while another checks source reachability.
- One worker reviews exploit preconditions while another builds a local reproducer.
- One worker curates candidate tools while another checks repo overlap and validation rules.
- One worker searches public advisories while another inspects local code paths.

## Bad splits

- Multiple workers editing the same files without isolation.
- Parallel noisy scans against the same target without rate/noise coordination.
- Asking several agents the same broad question and averaging opinions.
- Delegating final safety/scope decisions to a worker without review.

## Reviewer roles

- **Scope reviewer**: catches out-of-scope actions, destructive steps, and unauthorized expansion.
- **Technical reviewer**: checks correctness, minimality, and reproducibility.
- **Evidence reviewer**: downgrades overclaims and demands artifacts before final statements.

## Delegation gates

- Give workers full task text and context; do not make them reconstruct the plan from prior conversation.
- Require explicit status: done, done with concerns, blocked, or needs context.
- Review spec/scope compliance before code quality or polish.
- Never treat a worker report as proof; inspect artifacts and run verification before merging conclusions.

## Resources

Load on demand:

- `references/subagent-patterns.md` — prompt packets, parallelism rules, and synthesis format.
- `references/worktree-isolation.md` — when and how to isolate risky dev work with git worktrees.
- `references/worker-prompts.md` — implementer prompt packet, status handling, and self-review contract.
- `references/reviewer-prompts.md` — spec compliance, evidence, and code quality reviewer prompt patterns.
- `references/attack-chain-scoring.md` — chain link types, path scoring matrix, confidence levels, chain comparison matrix, lateral movement mapping, and dual-perspective (red/blue) output format.
- `references/engagement-planning.md` — engagement types, phased structure (scoping → recon → enumeration → vuln analysis → exploitation → post-ex → reporting), planning standards table, and rules of engagement template.
- `references/red-team-operations.md` — full red-team lifecycle: C2 infrastructure, initial access, foothold, persistence, lateral movement, objectives, cleanup, and operator log format.
