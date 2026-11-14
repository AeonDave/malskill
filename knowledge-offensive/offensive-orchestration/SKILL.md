---
name: offensive-orchestration
description: "Coordinate agents across security investigations, assessments, and labs: divide attack-path work, manage shared target sessions, and reconcile evidence across assets, identities, and attempts."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
---

# Offensive Orchestration

Coordinate the security task through its next verified outcome. Load [orchestration](../../knowledge/orchestration/SKILL.md) for delegation, model/effort selection, scheduling, job lifecycle, and integration; apply the additions below to security state and evidence. Use existing task constraints without inventing new approval stops.

## Split investigations around independent state

- Delegate by asset, trust boundary, artifact, or falsifiable hypothesis with a distinct proof requirement. Parallel static analysis of separate samples or patch pairs often fits; interacting operations on the same process, account, service, or debugger need a single owner or explicit serialization.
- Launch follow-up work when its prerequisite is established: an artifact exists, a build matches, an identity is confirmed, or a session is usable. A scanner label, worker claim, or suggested attack path is a lead, not that prerequisite.
- Match the worker to the uncertain part: bounded artifact extraction can use an efficient model; unfamiliar internals, cryptography, exploitability, or ambiguous runtime behavior may need stronger reasoning and domain tools. Agent count does not substitute for expertise.

## Route by the question

Give each worker a concrete question, the necessary context, and the relevant skills. Combine skills when a question crosses boundaries; hand work to another worker only when separate context, ownership, or expertise helps.

| Question | Starting skill |
|---|---|
| Scope what to attack and why, or plan a named-adversary emulation | [threat-modeling](../threat-modeling/SKILL.md) or [adversary-emulation-planning](../adversary-emulation-planning/SKILL.md) |
| Map assets or investigate public sources | [recon-technique](../../offensive-techniques/recon-technique/SKILL.md) or [osint-technique](../../offensive-techniques/osint-technique/SKILL.md) |
| Investigate a vulnerability or advisory, or validate supported web impact | [vuln-research](../vuln-research/SKILL.md) or [web-exploit-technique](../../offensive-techniques/web-exploit-technique/SKILL.md) |
| Assess cloud access, a host session, or an AD path | [cloud-security-technique](../../offensive-techniques/cloud-security-technique/SKILL.md), [post-exploit-technique](../../offensive-techniques/post-exploit-technique/SKILL.md), or [active-directory-technique](../../offensive-techniques/active-directory-technique/SKILL.md) |
| Analyze a mobile app, physical device, binary, or forensic artifact | [mobile-technique](../../offensive-techniques/mobile-technique/SKILL.md), [hardware-technique](../../offensive-techniques/hardware-technique/SKILL.md), [reversing-technique](../../offensive-techniques/reversing-technique/SKILL.md), or [forensic-technique](../../offensive-techniques/forensic-technique/SKILL.md) |
| Build a CVE inventory or review a public test artifact | [cve-search](../cve-search/SKILL.md) or [poc-weaponization](../poc-weaponization/SKILL.md) |

## Add security context to the job contract

Include only what changes execution or interpretation:

- Stable asset/sample identity, build or hash, relevant configuration, and observation time. An address, filename, or function offset alone may identify different objects after a change.
- Network position, identity and privilege, session state, required access, and references to credentials through the approved access mechanism. Keep raw secrets out of broad prompts, logs, and shared notes.
- The hypothesis, decisive observation and controls, existing evidence, known failed attempts with their conditions, and expected artifacts. Carry the relevant original request/output, trace, sample, or reproduction locator rather than a bare verdict.
- Mutable resources owned, expected state changes, interference risks, and who verifies restoration or cleanup when required by the task.

## Protect attribution and shared state

Assign one owner to a shared debugger, authenticated session, mutable account, or state-changing target operation. Read-only operations can still interfere through load, rate limits, caches, or observation windows; coordinate when that affects validity. Separate worktrees do not separate those resources.

Tag evidence with the job/attempt and relevant target state. Separate competing experiments by timing, input markers, or isolated fixtures so one worker's effect is not credited to another. Preserve raw evidence and append corrections; do not overwrite a finding with a newer unexplained verdict. Revalidate dependent conclusions after a reset, patch, privilege change, or different build.

Reconcile timeout and cancellation against target state before retrying an action that may already have succeeded. Do not reuse a late result until its attempt and environment match the current question. Record failed collection and untested paths as coverage gaps.

## Integrate evidence, not verdict counts

Compare conflicting results by identity, build, prerequisites, input, timing, and method. Seek the smallest discriminating check; agreement among workers using the same advisory or scanner is one source. Preserve unresolved alternatives when evidence cannot decide.

Load [evidence-before-claims](../../behaviours/evidence-before-claims/SKILL.md) when promoting a lead into a finding or reconciling claims for an engagement report. Separate observed behavior, inferred cause, reachable impact, and untested extensions. Report the achieved objective, evidence, coverage gaps, remaining sessions/jobs, and next useful action.

For investigations spanning many artifacts or sessions, load the [operational brain](../../behaviours/offensive-operator-mode/references/brain.md) and link job results, consequential routing decisions, and failures into the existing task record. Use [handoff](../../behaviours/handoff/SKILL.md) for an explicit transfer.

## When configuring the agent infrastructure

Enforce tool, credential, filesystem, and network access in the execution layer. Model instructions do not provide isolation; containers alone do not establish the required boundary. Keep privileged control sockets and writable host configuration out of worker environments unless the task requires them.

Review MCP/tool definitions and detect changes. Verify local artifacts where supported; authenticate and govern remote endpoints rather than treating a local checksum as a pin on remote behavior. Load [untrusted-input-hygiene](../../behaviours/untrusted-input-hygiene/SKILL.md) when ingesting target output, tool descriptions, shared messages, or worker files; validate their provenance and destination format before use.
