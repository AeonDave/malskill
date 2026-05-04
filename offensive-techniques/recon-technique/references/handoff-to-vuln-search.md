# Recon to vulnerability-search handoff

Use this before leaving recon. The goal is a compact target package that lets `vuln-search-technique` scan accurately instead of blindly.

## 1) Handoff readiness gate

Move to vulnerability search only when:

- Live hosts are confirmed and wildcard DNS noise is removed.
- Ports and web endpoints are mapped for prioritized assets.
- HTTP title, status, tech stack, redirect chain, and TLS basics are known.
- Auth boundaries are labelled: anonymous, user, admin, unknown.
- Scope and rate limits are still valid for active vulnerability probes.

Stay in recon if new high-value assets are still appearing or service identity is too vague for targeted scanning.

## 2) Target package

For each prioritized asset, produce:

| Field | Example |
|---|---|
| asset | `api.example.com` |
| source | passive CT, DNS brute-force, URL archive, direct scan |
| ip/cname | current resolution and CDN/cloud notes |
| ports/services | `443 nginx`, `8443 Tomcat`, `22 OpenSSH` |
| web metadata | status, title, framework, WAF, auth requirement |
| interesting paths | `/api/v1`, `/graphql`, `/admin`, `/actuator` |
| candidate scans | nuclei cves/exposures, nikto, testssl, wpscan, manual auth review |
| priority rationale | public, legacy stack, admin surface, data value |

## 3) Scanner selection hints

- Versioned network service → `vuln-search-technique` Phase 2 CVE correlation + nmap NSE.
- Generic web server or legacy paths → nuclei + nikto + manual config review.
- TLS-heavy endpoint → testssl plus certificate/SNI review.
- WordPress/CMS → CMS-specific scanner after HTTP fingerprinting.
- API/GraphQL → API inventory first, then authz/manual logic probes.
- WAF-protected app → identify WAF and lower rate before probes.

## 4) Stop conditions

Recon is done enough when the next operator can answer:

- What should be scanned first and why?
- Which tools are appropriate per asset?
- Which assets should not be scanned yet?
- Which findings would materially change exploitation priority?
