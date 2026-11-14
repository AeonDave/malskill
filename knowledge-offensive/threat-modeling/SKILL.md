---
name: threat-modeling
description: "Systematic threat modeling of a system, app, or feature before an assessment: decompose into elements (DFD), enumerate threats per element (STRIDE), build attack trees for high-value goals, prioritize, and map to ATT&CK to feed the assessment plan. Use when scoping what to attack and why — before technique selection."
license: MIT
compatibility: "Agent workflow guidance; method-agnostic (STRIDE, attack trees, PASTA). Works from architecture docs, code, or a live walk-through."
metadata:
  author: AeonDave
  version: "1.0"
---

# Threat Modeling

Answer *what is worth attacking and why* before choosing techniques. A threat model is a prioritized list of threats grounded in the system's actual structure — it feeds assessment scope, technique selection, and (via ATT&CK) emulation planning. Without it, assessment effort follows tool convenience instead of impact.

## When to activate

- Planning an assessment against a system you are only starting to understand
- A feature/architecture change needs a security review before testing
- The client asks "what are our biggest exposure areas" rather than "find bugs in X"
- Bridging design-stage analysis to real adversary behavior (ATT&CK mapping)

## Method selection

| Method | Best for |
|---|---|
| **STRIDE per-element** | Technical design review of app/service/infrastructure; systematic coverage, needs no past-attack data |
| **Attack trees** | One high-value attacker goal with multi-step paths; communicates depth to stakeholders |
| **PASTA** | Risk-centric engagements that must tie threats to business impact (7 stages) |
| **LINDDUN** | Privacy-focused analysis |

Default: STRIDE per-element for the technical pass; switch to attack trees when one goal (e.g. "access customer PII") dominates the engagement.

## Workflow

1. **Decompose** — build the DFD: external entities, processes, data stores, data flows, trust boundaries. Sources: architecture docs, code walk-through, cloud console, live probing. Trust boundaries (auth edge, service mesh, tenant isolation, human/machine) are where most threats live.
2. **Enumerate per element** — apply STRIDE to each element; not every threat applies to every type:

| Element | Applicable STRIDE threats |
|---|---|
| External entity | S, R |
| Process | S, T, R, I, D, E |
| Data store | T, R, I, D |
| Data flow | T, I, D |
| Trust boundary crossing | all six — highest yield |

3. **Ground each threat** in the actual implementation: "EoP on the API gateway" means naming the mechanism (broken auth, JWT confusion, SSRF-to-metadata) — a threat without a plausible mechanism is an assumption. Test cheap discriminators early (`hypothesis-driven`).
4. **Prioritize** — impact × likelihood × attainability from the current position. Mark each threat with the evidence that would confirm it.
5. **Map to ATT&CK** ([CTID Threat Modeling with ATT&CK](https://ctid.mitre.org/projects/threat-modeling-with-attack)): each plausible threat maps to the techniques an adversary would use to realize it — this converts the model into testable assessment work.
6. **Deliver** — threat list (ID, element, STRIDE category, mechanism hypothesis, priority, ATT&CK techniques) + the DFD. It feeds assessment scope, technique selection, and [`adversary-emulation-planning`](../adversary-emulation-planning/SKILL.md).

## LLM/agent applications

For LLM-powered systems, agent tool calls are new **processes** and tool outputs are new **data flows** — apply STRIDE to them directly: tool-result spoofing (S), context tampering (T), action repudiation (R), prompt/output leakage (I), agent-loop DoS (D), tool-driven EoP (E). Technique-side detail: `offensive-ctf/ai-ml-ctf/references/llm-attacks.md`, framework-side: `langchain-py`.

## Best practice

- Model from the attacker's entry position (external, low-priv) — threats reachable only from kernel or adjacent-tenant come later in the plan.
- One mechanism per threat entry; merge duplicates. A 40-line threat list beats a 400-line catalog nobody reads.
- Record what you *dismissed* and why (out of scope, mitigated, unreachable) — reviewers and future assessments need the negative space.
- Re-model on architecture changes; threat models rot with the design.

## Gotchas

- Do not inherit a vendor's threat model as-is — it reflects their mitigations, not your assessment position.
- STRIDE on a whiteboard without the implementation check produces threats that are already mitigated; verify one mechanism before prioritizing.
- The DFD must include the boring elements (backup jobs, monitoring, CI) — real attack paths route through them constantly.

## References

- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html) · [MITRE CTID — Threat Modeling with ATT&CK](https://ctid.mitre.org/projects/threat-modeling-with-attack)
- Related: [`adversary-emulation-planning`](../adversary-emulation-planning/SKILL.md) (the plan built from this model), [`deep-research-offensive`](../deep-research-offensive/SKILL.md) (evidence for each attack-path link), [`vuln-research`](../vuln-research/SKILL.md) (finding the actual bugs), [`recon-technique`](../../offensive-techniques/recon-technique/SKILL.md) (populating the DFD from live targets)
