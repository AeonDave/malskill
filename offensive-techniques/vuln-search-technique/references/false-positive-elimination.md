# False-positive elimination workflow

Use this before handing a scanner or manual finding to exploitation. The goal is to prove the finding is real, in scope, reachable, and attributable.

## 1) Reproduce outside the scanner

For every high or critical candidate:

- Recreate the exact request or probe manually.
- Remove scanner-only headers and payload noise unless they are required.
- Confirm the response changes when the vulnerability condition is removed.
- Capture raw request/response or service transcript.

If manual replay fails, keep the item as unconfirmed and investigate scanner assumptions.

## 2) Control matrix

| Finding type | Positive proof | Negative control |
|---|---|---|
| CVE/version | Exact vulnerable version + reachable component | Patched version check, module disabled check |
| SQLi/XSS/SSTI | Payload changes response in class-specific way | Benign payload and encoded non-payload response |
| SSRF | Controlled outbound callback or internal differential | Same URL in inert parameter |
| Auth/IDOR | User A accesses/modifies user B resource | Same request with no auth or wrong role fails |
| Misconfig | Sensitive behavior observed from scoped origin | Expected restricted path fails |
| TLS/config | Tool finding matches protocol transcript | Cross-check with independent TLS client/tool |

## 3) Confounder checks

Eliminate these before escalation:

- Cache: response reused from previous request.
- Redirect: scanner evaluated final URL but report names original URL.
- WAF/CDN block page: payload triggered edge behavior, not origin vulnerability.
- Auth state: stale admin cookie or session contamination.
- Version mismatch: banner lies, backport patch applied, or module not installed.
- Multi-tenant bleed: finding belongs to shared infrastructure outside scope.
- Race/timing: one-off anomaly not reproducible.

## 4) Confidence levels

| Level | Meaning | Handoff? |
|---|---|---|
| C0 | Scanner-only or hypothesis | No |
| C1 | Manual one-off signal | No, needs controls |
| C2 | Reproducible with one control | Maybe for further validation |
| C3 | Reproducible with positive and negative controls | Yes |
| C4 | Impact path proven safely | Yes, ready for exploit technique |

## 5) Evidence package

For each confirmed item include:

- Target, endpoint/service, timestamp, source IP if relevant.
- Scanner/tool and version if scanner found it.
- Manual reproduction steps at technique level, not full tool manual.
- Positive evidence and negative control evidence.
- Impact hypothesis and safest exploitation route.
- Known uncertainty and constraints.
