# Risk prioritization for vulnerability search

## Purpose

Prioritize findings by exploitation likelihood, impact, exposure, and mission relevance instead of CVSS alone.

## Inputs

- Confirmed asset inventory from recon.
- Service versions and configuration context.
- Scanner findings and manual evidence.
- CISA KEV, EPSS, exploit availability, and public PoC context.
- Business/mission criticality of the affected asset.

## SSVC-style decision points

| Decision point | Values | Why it matters |
|---|---|---|
| Exploitation status | none, PoC, active | Active exploitation raises urgency immediately |
| Technical impact | partial, total | Determines maximum compromise scope |
| Automatability | no, yes | Determines scale and urgency |
| Exposure | internal, authenticated, internet-facing | Changes likelihood and required access |
| Mission prevalence | minimal, support, essential | Maps technical risk to business priority |
| Safety/public impact | minimal, material, severe | Raises priority for critical services |

## Outcome labels

| Label | Action |
|---|---|
| Track | Normal remediation queue; monitor for new exploitability evidence |
| Track* | Prioritize next window; watch threat intel and compensating controls |
| Attend | Escalate and accelerate validation/remediation |
| Act | Immediate mitigation, containment, or exploitation proof if in offensive scope |

## Prioritization workflow

1. Deduplicate scanner output by root cause and affected component.
2. Confirm version/config match against live evidence.
3. Check CISA KEV and active exploitation reports.
4. Check EPSS and public exploit quality.
5. Determine whether exploitation is automatable at scale.
6. Map asset criticality and exposure.
7. Assign outcome and next action.

## Offensive handoff criteria

Handoff to `vuln-exploit-technique` when:

- Finding is confirmed or has strong reproducible evidence.
- Target version/config matches exploit prerequisites.
- Impact is high enough to justify controlled exploitation.
- Rules of engagement allow proof beyond detection.

Handoff to `web-exploit-technique` when:

- Vulnerability class is web/API-specific.
- Request/response evidence identifies the vulnerable surface.
- Auth context and state-change limits are clear.

## Evidence fields

For each finding retain:

- Asset and owner if known.
- Vulnerability class or CVE.
- Version/config proof.
- Exploitability status and sources.
- Required privilege and user interaction.
- Potential impact and affected data/system.
- Priority outcome and rationale.

## Common pitfalls

- Ranking solely by CVSS while ignoring active exploitation.
- Treating PoC existence as reliable exploitability without testing prerequisites.
- Ignoring compensating controls like WAF, segmentation, or disabled modules.
- Escalating low-value internal-only findings above exposed critical services.
