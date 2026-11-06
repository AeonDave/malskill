# Recon to vulnerability-research handoff

Load when handing identified assets or entry points to [vuln-research](../../../knowledge-offensive/vuln-research/SKILL.md). Preserve the observations needed to choose the next check without repeating discovery.

## Establish usable target identity

For the surface being handed over, establish or mark unknown:

- Current host/service reachability and resolution, including wildcard or shared-host ambiguity.
- Relevant ports or endpoints and the evidence supporting the technology/build fingerprint.
- For HTTP, redirects, virtual-host routing, and any intermediary that may answer instead of the application.
- Available authentication roles and which surfaces each can reach.

Resolve an identity gap in recon when it prevents a meaningful check. Useful research on an identified surface can proceed while unrelated discovery continues.

## Target package

For each prioritized asset, produce:

| Field | Example |
|---|---|
| asset | `api.example.com` |
| source | passive CT, DNS brute-force, URL archive, direct scan |
| ip/cname | current resolution and CDN/cloud notes |
| ports/services | `443 nginx`, `8443 Tomcat`, `22 OpenSSH` |
| web metadata | status, title, framework, WAF, auth requirement |
| interesting paths | `/api/v1`, `/graphql`, `/admin`, `/actuator` |
| proposed question/check | published-version applicability, configuration review, ownership check |
| priority rationale | public, legacy stack, admin surface, data value |
| evidence and time | observation timestamp, request/response or tool-output path |
| unresolved coverage | unknown build, inaccessible role, untested endpoint |

## Route the next question

- Known advisory or version/configuration applicability → [cve-search](../../../knowledge-offensive/cve-search/SKILL.md).
- Coverage across the identified inventory or scanner leads → [vuln-research's assessment coverage](../../../knowledge-offensive/vuln-research/references/assessment-coverage.md).
- A concrete suspicious behavior → the hypothesis and experiment workflow in [vuln-research](../../../knowledge-offensive/vuln-research/SKILL.md).

## Handoff check

Recon is done enough when the next operator can answer:

- What surface and security question should be examined first, and why?
- Which observations identify the actual service and user/role context?
- What remains unknown or untested?
- What result would change the next decision?
