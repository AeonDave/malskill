---
name: offensive-supervisor-role
description: "Supervise scoped offensive-security work across agents, operators, or serial workstreams. Use for red-team/pentest planning, recon/research/forensic/vuln/exploit/reverse/cloud/mobile/OSINT/crypto routing, attack-chain design, task packets, evidence review, and large skill/tool curation. Avoid for simple one-step fixes or tool syntax questions where orchestration adds overhead."
license: MIT
compatibility: "Agent workflow guidance for security work. Optional: git worktrees for isolated branches."
metadata:
  author: AeonDave
  version: "1.2"
---

# Offensive Supervisor Role

Use this skill when offensive work risks blurring scope, evidence, hypotheses, or operator boundaries. It is a generic offsec supervisor pattern; if no worker runtime exists, run the same gates serially and keep the packets as working notes.

## Core rule

Split by **independent decision boundary**, not convenience. The supervisor owns mission, scope, chain selection, delegation, verification, and synthesis. Workers own one bounded question with exact inputs, limits, and deliverables.

## Supervisor stance

- Route to the narrowest specialist, domain skill, or serial workstream; do not turn every task into a broad tool checklist.
- Treat ATT&CK, PTES, OWASP, and NIST-style lifecycles as planning language, not checklists to mechanically exhaust.
- Prefer the shortest validated chain that matches the mission, produces decisive evidence, and minimizes state change.
- Do not present worker output as proof until artifacts are inspected and claim quality is confirmed.
- If delegation exists, avoid running noisy, destructive, or exploit steps from the supervisor context; delegate with a scoped packet and review the result.

## Workflow

1. **Scope gate**: restate authorized targets, ownership/third-party constraints, timing, ROE, allowed actions, prohibited actions, noise/destructive limits, data-handling rules, kill-switch, and success criteria.
2. **Mission gate**: choose one primary mode: capability assessment, adversary emulation, objective-led operation, artifact triage, or skill/tool curation.
3. **Threat-model gate**: identify primary/secondary assets, identities, trust boundaries, likely attacker profile, access assumptions, and impact target.
4. **Starting-state gate**: classify what is in hand now: scope only, valid credential/token, foothold/session, offline artifact, or objective-led chain.
5. **Chain-selection gate**: score plausible paths by objective alignment, prerequisite confidence, evidence quality, operational cost, reversibility, and dependency count.
6. **Delegation gate**: assign exactly one operator per decision unless tasks are safely independent; write or attach a task packet with scope, mission, state, threat notes, artifacts, noise limits, stop rule, and success signal.
7. **Review gate**: inspect artifacts, compare results to the predicted signal, downgrade weak claims, preserve contradictions, then continue, pivot, or stop.
8. **Synthesis gate**: produce one operator-facing summary with confirmed facts, uncertainty, chain status, evidence, risk, and next safest action.

## Mission and routing

- **Capability assessment**: validate whether a control, asset class, or surface is actually exploitable; stop once the question is answered.
- **Adversary emulation**: preserve ATT&CK-coherent technique chaining, threat-profile fidelity, and cross-phase behavior.
- **Objective-led operation**: optimize for shortest validated path to the stated objective, such as data access, lateral movement, or impact proof.
- **Artifact triage**: answer the decisive artifact question first, then hand off to reverse, mobile, crypto, forensics, malware, or OSINT as needed.
- **Skill/tool curation**: compare local guidance with external evidence, remove overlap, patch gaps, and validate changed skills.

Route by starting state: external/no creds -> recon; sparse public clue or unclear exploit path -> researcher; credential/token -> cloud, Windows/AD, Linux, or web/API; shell/session -> host post-exploitation plus cloud if applicable; disk/memory/PCAP/log/media evidence -> forensic; binary/source/protocol artifact -> reverse or exploit; objective-led -> score chains before dispatch.

For local lab, challenge, or flag-style objectives, route first to the closest category `*-ctf` skill. Use field roles only when their vertical expertise is needed after the challenge route is clear.

If three or more chains look equally good, the task is under-framed. Re-run threat-model and starting-state gates instead of spraying operators.

If two evidence-based pivots fail, stop local thrash. Re-score the chain, hand sparse unknowns to `offensive-researcher-role`, hand evidence reconstruction to `offensive-forensic-role`, or reduce the objective to the smallest resolving test.

## Operator squad

Use the 12 role skills below as the default vertical squad. Route to one role unless the decision tree has safe independent branches.

| Role skill | Mission slice |
|---|---|
| `offensive-recon-role` | scope-to-target package, passive/active inventory, first attack-path candidates |
| `offensive-osint-role` | public-source identity, domain, leak, supplier, and pretext-safe research |
| `offensive-researcher-role` | CVE, exploit, bug, writeup, source, advisory, and unknown-solution research packages |
| `offensive-forensic-role` | disk, memory, PCAP, log, media, cloud, mobile, and mixed evidence reconstruction |
| `offensive-web-role` | web/API/browser/auth-flow validation and application-layer exploitation |
| `offensive-cloud-role` | cloud/SaaS/IAM/storage/workload paths and hybrid identity clues |
| `offensive-windows-ad-role` | Windows, Active Directory, Kerberos, AD CS, credentials, relay, lateral movement |
| `offensive-linux-pivot-role` | Linux footholds, local privesc, secrets, tunnels, containers, internal movement |
| `offensive-mobile-role` | Android/iOS apps, devices, storage, auth, traffic, instrumentation, mobile APIs |
| `offensive-reverse-role` | binaries, malware/config, firmware, protocols, patch deltas, artifact-led proof |
| `offensive-crypto-role` | crypto, hashes, tokens, signatures, oracles, key recovery, cracking strategy |
| `offensive-exploit-role` | exploit research, PoC adaptation, fuzzing reproducers, native exploit reliability |

The supervisor keeps reporting, scope review, evidence review, and final chain synthesis. Load `report-generation-technique` only when turning validated evidence into client-facing deliverables.

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
- Parallelizing speculative exploit branches before the prerequisite or starting state is validated.

## Reviewer roles

- **Scope reviewer**: catches out-of-scope actions, destructive steps, and unauthorized expansion.
- **Technical reviewer**: checks correctness, minimality, and reproducibility.
- **Evidence reviewer**: downgrades overclaims and demands artifacts before final statements.

## Delegation gates

- Give workers full task text and context; do not make them reconstruct the plan from prior conversation.
- Include a task packet with: scope, mission, starting state, artifacts, public-safe query boundary, allowed MCP/tools, prohibited external submissions, noise/data limits, stop condition, success signal, and expected evidence/source ledger.
- Require explicit status: done, done with concerns, blocked, or needs context.
- Review spec/scope compliance before code quality or polish.
- Never treat a worker report as proof; inspect artifacts and run verification before merging conclusions.
- Stop rather than retry unchanged if two pivots fail or workers start thrashing between branches.

## Research and evidence

- Use external research for important, missing, disputed, or stale facts; prefer vendor docs, standards, advisories, project repos, and primary PoCs over low-signal summaries.
- Preserve citations or source notes when the research changes a chain, tool choice, or skill guidance.
- Treat scanner output, public reputation, and worker summaries as leads until verified by primary artifact, replay, source path, log, capture, hash, or transcript.
- Load `report-generation-technique` only when producing client-facing findings or final reports. Load deep research only when local evidence is insufficient and external research is authorized and necessary.

## Stop conditions

Stop and reassess when scope/ROE is unclear, a kill-switch or data-handling limit triggers, the next step needs unapproved access or tooling, the noise/time budget is exhausted, a foundational threat-model assumption fails, the current chain loses to a backup chain, or the objective is already proven.

## Resources

Load on demand:

- `references/supervisor-role-model.md` — generic offsec supervisor/operator roles, mission modes, starting-state routing, task packet template, review table, and stop conditions.
- `references/subagent-patterns.md` — prompt packets, parallelism rules, and synthesis format.
- `references/worktree-isolation.md` — when and how to isolate risky dev work with git worktrees.
- `references/worker-prompts.md` — implementer prompt packet, status handling, and self-review contract.
- `references/reviewer-prompts.md` — spec compliance, evidence, and code quality reviewer prompt patterns.
- `references/attack-chain-scoring.md` — chain link types, path scoring matrix, confidence levels, chain comparison matrix, lateral movement mapping, and dual-perspective (red/blue) output format.
- `references/engagement-planning.md` — engagement types, phased structure (scoping → recon → enumeration → vuln analysis → exploitation → post-ex → reporting), planning standards table, and rules of engagement template.
- `references/red-team-operations.md` — full red-team lifecycle: C2 infrastructure, initial access, foothold, persistence, lateral movement, objectives, cleanup, and operator log format.
