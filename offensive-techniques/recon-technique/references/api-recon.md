# API reconnaissance and trust-boundary mapping

## Purpose

Build a complete API inventory before vulnerability probing so testing is targeted, low-noise, and authorization-aware.

## Inputs

- Base URLs and known API prefixes.
- OpenAPI/Swagger specs, Postman collections, GraphQL schemas, or captured traffic.
- Auth contexts: anonymous, normal user, privileged user, service account, tenant A/B.
- Scope limits, rate limits, and forbidden actions.

## Discovery sources

Prioritize sources in this order:

1. Official specs: `/openapi.json`, `/swagger.json`, `/api-docs`, GraphQL introspection when authorized.
2. Front-end bundles: routes, API clients, hardcoded feature flags, GraphQL operation names.
3. Browser/proxy traffic from normal user journeys.
4. Historical URLs from archives and URLScan.
5. Runtime errors revealing undocumented endpoints.

## Endpoint normalization

Normalize every route into this shape:

| Field | Example |
|---|---|
| Method | `GET` |
| Canonical path | `/api/v1/orders/{id}` |
| Source | `spec`, `traffic`, `frontend`, `archive` |
| Auth style | anonymous, cookie, bearer, API key, mTLS |
| Trust boundary | public, user, admin, internal, unknown |
| Data class | profile, payment, document, admin, telemetry |
| State impact | read, write, delete, workflow transition |

Keep undocumented endpoints separate from documented ones until behavior is confirmed.

## Trust-boundary map

Label endpoint families by who should be able to call them:

- `public`: no authentication expected.
- `user`: authenticated self-service operations.
- `admin`: privileged tenant or platform operations.
- `internal`: expected to be service-to-service only.
- `unknown`: observed but not yet understood.

Then verify with baseline requests:

- No token/session.
- Expired token/session.
- Valid low-privilege user.
- Same role in another tenant.
- Privileged role.

Record response fingerprints: status code, error shape, redirect behavior, and response length band.

## Parameter risk profiling

Mark high-risk parameters before active testing:

| Parameter type | Risk signal | Follow-up |
|---|---|---|
| Object references | `id`, `user_id`, UUID, slug | BOLA/IDOR tests |
| Role or state fields | `role`, `status`, `approved`, `owner` | Mass assignment and workflow abuse |
| URLs/files | `url`, `callback`, `webhook`, `avatar` | SSRF and file handling |
| Query operators | `filter`, `sort`, `$where`, `q` | SQL/NoSQL/operator injection |
| Rich text/templates | `html`, `template`, `message` | XSS/SSTI/template injection |
| Bulk arrays | `ids[]`, `items[]` | Partial authorization failures |

## Prioritized test matrix

Generate tests from inventory, not guesswork:

1. Object-level authorization on read/write/delete endpoints.
2. Function-level authorization on admin-like routes.
3. Mass assignment on create/update endpoints.
4. Injection probes on parser-heavy inputs.
5. SSRF on URL fetchers, importers, webhooks, and preview endpoints.
6. Workflow/state abuse on approval, billing, refund, and invitation flows.
7. Rate and replay abuse on login, reset, OTP, coupon, and transfer flows.

## GraphQL-specific recon

- Inventory query/mutation/subscription names.
- Decode Relay global IDs and map object type prefixes.
- Identify resolvers that return nested sensitive objects.
- Compare field availability by role and tenant.
- Treat subscriptions as real-time authorization surfaces.

## Output contract

Produce:

- Endpoint inventory with source and auth labels.
- Trust-boundary table with verified vs assumed status.
- Parameter risk profile.
- Prioritized test matrix.
- Coverage gaps and blockers.

## Common pitfalls

- Treating a spec as complete when front-end traffic shows drift.
- Testing only `GET` while `PUT`, `PATCH`, `DELETE`, or bulk endpoints behave differently.
- Ignoring tenant boundaries because same-role tests passed inside one tenant.
- Missing async job endpoints that apply stale permissions after submission.
