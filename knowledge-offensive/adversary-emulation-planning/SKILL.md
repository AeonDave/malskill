---
name: adversary-emulation-planning
description: "Build an adversary emulation plan from CTI: extract TTPs from threat reports, map to ATT&CK, prioritize against the target's actual stack, and structure the plan as phased procedures with detection expectations. Use when an engagement must emulate a specific adversary or campaign rather than run open-ended testing."
license: MIT
compatibility: "Agent workflow guidance; ATT&CK Enterprise/Mobile matrices. Works from CTI reports, incident data, or actor profiles."
metadata:
  author: AeonDave
  version: "1.0"
---

# Adversary Emulation Planning

Adversary emulation = replicating a **specific adversary's TTPs** against your target to test detection and response — scoped to a named actor or campaign, not open-ended exploitation. The plan is a CTI-driven blueprint: which techniques, in what order, with what procedures, and what the defender should have seen.

## When to activate

- The engagement contract names an adversary/campaign to emulate (APT-style, ransomware operator, infostealer)
- Validating detections against realistic TTP sequences rather than individual techniques
- Purple-team work: each planned procedure pairs with a detection expectation
- Converting fresh CTI into testable steps before the intel ages out

## Workflow

1. **Extract TTPs from CTI** — from reports on the chosen actor/campaign: initial access, execution, persistence, credential access, lateral movement, exfiltration. Extract the *behavior* (what was done to which component) not the vendor's tool names: "scheduled task with encoded PowerShell" is a TTP; "Cobalt Strike" is a tool.
2. **Map to ATT&CK** — assign technique IDs (T1053.005, T1027…). Where the report lacks granularity, infer the most likely technique and mark the inference.
3. **Prioritize against the target stack** — a TTP targeting macOS processes is noise on a Windows estate; weight by (a) relevance to the actual technologies in scope, (b) frequency across the actor's reports, (c) data sources the target actually emits (you cannot test detection of logs that don't exist).
4. **Adapt procedures** — reimplement each technique against the target's stack with your own tooling; CTI describes intent, not runnable commands. Keep the ATT&CK ID stable across your variant.
5. **Structure the plan** — phases following the adversary's real kill chain, each with: objectives, techniques (IDs), concrete procedures, execution notes, and **expected detection** (which log/telemetry/analytic should fire).
6. **Execute and capture** — run procedures per `rules-of-engagement`, record what fired vs the expectation; the gap list is the purple-team deliverable.

## Plan structure (MITRE AEP shape)

```markdown
# Emulation Plan — <actor/campaign>
## Background: actor motivation, targets, notable incidents
## C2 phases: staging → initial foothold → escalation → lateral → objective
### Phase: Initial Access
- T1566.001 Spearphishing Attachment
  - Procedure: mail with macro-doc → DLL payload via scheduled COM
  - Detection expectation: Sysmon EID 15 (Alternate Data Stream) + AMSI hit
- ...
```

Reference format: [MITRE Adversary Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library) (APT3/APT29 plans). Micro emulation plans = single compound behaviors, automatable — use for focused purple-team sessions.

## Best practice

- **Fresh CTI degrades**: re-extract TTPs before each planning cycle; a year-old actor profile emulates an adversary that may have changed tooling.
- Sequence matters for detection: defenders tune on *chains*, not isolated techniques — plan phases that mirror the actor's real ordering.
- Pair each procedure with its detection expectation in the plan itself; executing without the expectation column turns the exercise into a Pentest, not an emulation.
- Where the actor used tooling you cannot stage, substitute behavior-equivalent implementations (same ATT&CK ID, your code) — the ID is the contract with the defenders.

## Gotchas

- CTI reports describe **outcomes**, not commands: "deployed a web shell" leaves tool, path, and persistence to you — infer the most probable technique and document the inference.
- Tool-name-centric CTI (report lists the actor's C2 framework) tempts tool-matching instead of behavior-matching — extract TTPs, then choose your own implementation.
- Emulation plans inherit the actor's noise: some TTPs are loud by design; flag phases that will trip third-party monitoring and agree on handling beforehand (see `rules-of-engagement`).

## References

- [MITRE Adversary Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library) · [ATT&CK](https://attack.mitre.org/) · [CTID](https://ctid.mitre.org/)
- Related: [`threat-modeling`](../threat-modeling/SKILL.md) (the model upstream — emulation plans test the threats that matter), [`deep-research-offensive`](../deep-research-offensive/SKILL.md) (validating each attack-path link and detection claim), [`offensive-orchestration`](../offensive-orchestration/SKILL.md) (parallel agent execution of plan phases), [`rules-of-engagement`](../../behaviours/rules-of-engagement/SKILL.md)
