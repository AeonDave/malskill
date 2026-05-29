---
name: agentic-offensive-orchestration
description: "Coordinate scoped offensive-security work across subagents, MCP tools, or serial workstreams. Use for pentest/red-team routing, CTF/lab solving, recon/research/forensic/exploit/reverse/cloud/mobile/OSINT/crypto splits, tool/skill curation, and large evidence-heavy tasks with independent decision boundaries. Avoid for simple one-step commands or single-role tasks where orchestration adds overhead."
license: MIT
compatibility: "Agent workflow guidance for local repositories and authorized security work. Optional: git worktrees for isolated branches."
metadata:
  author: AeonDave
  version: "1.3"
---

# Agentic Offensive Orchestration

Use this skill when offensive work needs multiple agents, MCP tools, or serial workstreams without losing scope, evidence, or velocity. The mission is rapid delegation, precise review, and one coherent synthesis.

## Core rule

Split by **independent decision boundary**, not by convenience. The orchestrator owns mission, scope, routing, task packets, verification, and synthesis. Workers own one bounded question with exact inputs, limits, and deliverables.

Do not orchestrate just because multiple tools exist. Route to one specialist when one role can answer the question faster.

If using a supervisor, do not let the main model become a passive waiting room. Dispatch specialized agents with their own role/skill loadouts, then keep the main thread advancing on a safe independent branch, reviewing completed outputs, or updating the blackboard. If the main thread would only launch async work and poll, run that work synchronously instead.

## Workflow

1. **Scope gate**: restate authorized targets, lab/challenge boundary, ROE, allowed actions, prohibited actions, noise/destructive limits, data-handling rules, and success signal.
2. **Mode gate**: choose one mode: pentest/red-team operation, CTF/lab solving, artifact triage, exploit research, tool/skill curation, or code/tool development.
3. **Starting-state gate**: classify current state: scope only, sparse clue, credential/token, foothold/session, offline evidence, source/binary artifact, or objective-led chain.
4. **Routing gate**: load the narrowest supervisor or role skill; for challenge tasks route first to the closest `*-ctf` skill.
5. **Task packet gate**: give each worker a compact packet with objective, inputs, boundaries, allowed MCP/tools, prohibited external submissions, output format, stop rule, and success signal.
6. **Topology gate**: choose single-operator, supervisor-light, or swarm-lite based on branch independence, budget, target noise, and merge cost.
7. **Parallelism gate**: parallelize only safe independent branches; keep exploit chains, state-changing actions, and shared-file edits serial unless isolated.
8. **Review gate**: inspect artifacts, source ledgers, commands, diffs, or transcripts. Treat worker output as a lead until verified.
9. **Synthesis gate**: produce one operator-facing result: confirmed facts, confidence, contradictions, chain status, risks, next smallest action.

## Topology and dispatch

- **Single operator**: default for small source, one endpoint/artifact cluster, clear oracle, or one likely primitive.
- **Supervisor-light**: use when two or more branches are independent enough that a worker can run while the main operator probes, reviews, or prepares merge context.
- **Swarm-lite**: use only when branches have distinct context, oracle, or decision boundary and merge criteria are defined before launch. No fixed worker cap; cap by independence, budget, target noise, and merge cost.
- Dispatch sync by default. Use async only when the branch is independent, output format is predefined, and the main operator can make real progress elsewhere.
- Re-topologize after two failed pivots, strong source/runtime contradiction, decisive branch merge, or evidence that a worker became stale or duplicate.
- Retire stale or duplicate workers immediately after the merge point. Do not run two agents on the same primitive unless one builds and one reviews.
- Grow the swarm when independent branches, model diversity, or source/runtime contradictions can be tested in parallel. Shrink it when branches converge, outputs duplicate each other, target noise rises, or merge cost exceeds expected signal.
- Create local replica/lab-builder branches when behavior depends on exact versions, framework defaults, parser quirks, serialization, middleware order, race timing, sandbox rules, or build/runtime drift. The lab must answer one narrow question and record divergence from target evidence.
- Choose model cost by task: cheap models for triage, route maps, source skim, and negative filtering; standard models for normal workers; premium/rescue models only after concrete dead end plus sharp question. Use one premium branch at a time.

Each worker declares: role, loaded skills, input, allowed actions, stop condition, expected output. Role skills are loaded by name, not source path; load only what the branch needs.

Maintain a blackboard:

- facts: confirmed observations only;
- hypotheses: theory, confidence, and disproof test;
- artifacts: paths, req/res, logs, tokens, scripts, hashes, source refs;
- attempts: test -> output -> interpretation -> next;
- dead paths: failed branches worth preserving;
- queue: next cheapest discriminating tests.

## Routing model

- For full mission supervision, chain scoring, or final synthesis, load `offensive-supervisor-role`.
- For sparse public clues, CVEs, exploits, writeups, advisories, GitHub code, patch hints, or repeated unknowns, route to `offensive-researcher-role`.
- For disk, memory, PCAP, event logs, archives, screenshots, media/stego, mobile backups, cloud snapshots, or evidence reconstruction, route to `offensive-forensic-role`.
- For direct vertical work, route to the narrowest role: recon, OSINT, web, cloud, Windows/AD, Linux pivot, mobile, reverse, crypto, or exploit.
- For CTF/lab/flag-style objectives, route directly to the closest category `*-ctf` skill; load multiple only when the bundle is genuinely cross-domain.

Use Tavily-backed search/research/crawl, fetch, GitHub source search, and other MCP tools only when local context is insufficient and the query is public-safe. External research must produce a source ledger; it must not receive private target identifiers, secrets, proprietary snippets, or unpublished vulnerability detail without explicit approval.

## Good splits

- Researcher checks CVE/prior art while reverse inspects local code path.
- Forensic reconstructs PCAP/log timeline while web validates one request replay.
- Recon builds scoped asset package while OSINT validates public ownership and supplier clues.
- Exploit reviews PoC safety while another worker builds an isolated local reproducer.
- Skill curator compares external docs while another worker validates local repo structure and changed-skill hygiene.
- Traffic/surface mapper builds endpoint or artifact corpus while exploit/source operator tests one clear primitive.
- Research fan-out uses distinct models, source scopes, or context packets when prior-art disagreement matters; all return citations and one decisive local test.

## Bad splits

- Multiple workers editing the same files without isolation.
- Parallel noisy scans against the same target without rate/noise coordination.
- Asking several agents the same broad question and averaging opinions.
- Delegating final safety/scope decisions to a worker without review.
- Parallelizing speculative exploit branches before prerequisite evidence is validated.
- Sending private target data to Tavily, public search, sandboxes, or LLM APIs without approval.
- Launching async workers and then idling or polling instead of doing useful independent work.
- Keeping workers alive after their branch is confirmed, disproved, or superseded by merged evidence.

## Reviewer roles

- **Scope reviewer**: catches out-of-scope actions, destructive steps, and unauthorized expansion.
- **Technical reviewer**: checks correctness, minimality, and reproducibility.
- **Evidence reviewer**: downgrades overclaims and demands artifacts before final statements.

## Delegation gates

- Give workers full task text and context; do not make them reconstruct the plan from prior conversation.
- Include public-safe query boundaries and external-submission limits when any MCP/web research is possible.
- Require explicit status: done, done with concerns, blocked, or needs context.
- Review spec/scope compliance before code quality or polish.
- Never treat a worker report as proof; inspect artifacts and run verification before merging conclusions.
- If two evidence-based pivots fail, stop unchanged retries; route to researcher, forensic, supervisor re-score, or the smallest resolving test.
- Evidence reviewers are spawned after a decisive claim, not by default. Premature review agents slow the chain and add noise.

## Output contract

Return:

- status: `done`, `done with concerns`, `blocked`, or `needs context`;
- routing summary: chosen mode, role/skill loaded, and why alternatives were not used;
- task packets issued or serial workstreams run;
- verified facts with evidence pointers and confidence;
- contradictions, negative findings, and unresolved assumptions;
- next action: smallest safe test, owner role, approval needed, and stop condition.

## Resources

Load on demand:

- `references/subagent-patterns.md` — prompt packets, parallelism rules, and synthesis format.
- `references/worktree-isolation.md` — when and how to isolate risky dev work with git worktrees.
- `references/worker-prompts.md` — implementer prompt packet, status handling, and self-review contract.
- `references/reviewer-prompts.md` — spec compliance, evidence, and code quality reviewer prompt patterns.
- `references/attack-chain-scoring.md` — chain link types, path scoring matrix, confidence levels, chain comparison matrix, lateral movement mapping, and dual-perspective (red/blue) output format.
- `references/engagement-planning.md` — engagement types, phased structure (scoping → recon → enumeration → vuln analysis → exploitation → post-ex → reporting), planning standards table, and rules of engagement template.
- `references/red-team-operations.md` — full red-team lifecycle: C2 infrastructure, initial access, foothold, persistence, lateral movement, objectives, cleanup, and operator log format.
