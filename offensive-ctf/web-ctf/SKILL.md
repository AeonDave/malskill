---
name: web-ctf
description: "Challenge-solving methodology for web-application challenge solving. Integrates web-exploit-technique, vuln-search-technique, recon-technique, and fuzzing-technique with preserved imported CTF techniques, generic writeup-derived patterns, and tool-routing for agentic AI. Use for HTTP apps, APIs, browser clients, auth flows, file uploads, SSRF, XSS, SQLi, SSTI, XXE, deserialization, request smuggling, and prototype pollution."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Web CTF

Goal: solve web-application challenge solving tasks with professional offensive methodology, preserved imported technique coverage, and reproducible evidence.

## When this skill applies

- HTTP apps, APIs, browser clients, templates, auth flows, file uploads, SSRF, XSS, SQLi, SSTI, XXE, deserialization, request smuggling, or prototype pollution
- tasks requiring endpoint mapping, parameter discovery, exploit chaining, or stateful session testing

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Use `references/source-coverage.md` to see preserved imported topics.
4. Load debrandized imported references only for deep technique details.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `web-exploit-technique`
- `vuln-search-technique`
- `recon-technique`
- `fuzzing-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and preserved specialized patterns from the imported corpus.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `offensive-tools/web/jwt-tool`
- `offensive-tools/web/commix`
- `offensive-tools/web/xsstrike`
- `offensive-tools/web/smuggler`
- `offensive-tools/vuln-scanners/sqlmap`
- `offensive-tools/vuln-scanners/sstimap`
- `offensive-tools/recon/ffuf`
- `offensive-tools/recon/katana`
- `offensive-tools/network/burpsuite`

Tool syntax belongs in the tool skills. This skill decides when a tool family fits and what output should validate progress.

## Writeup-derived patterns

- Public writeup patterns favor artifact-first triage, shortest reproducible path, and explicit validation signal before pivoting.
- Record failed hypotheses with evidence so an agent does not repeat expensive dead paths.
- Prefer category-specific tools after surface classification instead of running every scanner or brute-forcer by habit.
- End with a replayable proof: recovered secret, local verification, exploit output, decoded artifact, or correlated evidence chain.

## Category-specific quick pivots

- Map endpoints, auth boundaries, parameters, and state-changing actions before exploitation.
- Capture one normal request/response pair per feature and read HTML, JS bundles, headers, routes, and alternate methods before fuzzing.
- Decide where the objective likely lives: browser DOM/state, API response, local file, database row, internal service, environment, or admin-only action.
- Classify trust-boundary input: templates, redirects, file paths, headers, serialized objects, background jobs, webhooks, OAuth callbacks, uploads, or parser/proxy seams.
- For information disclosure, build a channel map: errors, debug endpoints, DVCS/backups, config/secrets, schemas/introspection, client bundles/source maps, headers, exports, object storage, observability, and cache/CDN metadata. Diff anonymous, owner, and non-owner responses by status, length, ETag, cache headers, and body digest.
- For JWT/OIDC, build a token matrix before mutation: token type, issuer, audience, authorized party, client, service, key ID, and acceptance endpoint. Test header-controlled keys, token confusion, cross-service reuse, expiry/skew, and refresh-token rotation separately.
- For open redirects, compare server validation against real browser navigation after canonicalization. Test userinfo, protocol-relative URLs, backslashes, fragments/query tricks, Unicode/IDNA, numeric IPs, double encoding, Host/X-Forwarded-* construction, and multi-hop chains into OAuth/OIDC or SSRF flows.
- For IDOR/BOLA, build a Subject × Object × Action matrix with at least two principals. Collect IDs from list/search/export/log/client-bundle sources, then swap object, tenant, parent, and projection fields across REST, GraphQL, WebSocket, gRPC, batch, and job-result endpoints.
- For function-level authorization, build an Actor × Action × Transport matrix. Test basic versus privileged users across REST, GraphQL, gRPC, WebSocket, method overrides, content types, gateway headers, tenant selectors, and job/webhook finalize paths.
- For business logic, model the state machine and invariants first: value conservation, uniqueness/idempotency, quota monotonicity, exclusivity, tenant scoping, and approval preconditions. Then test replay, reordering, stale finalize requests, concurrency, time-window edges, and client-computed totals.
- For CSRF, inventory state-changing endpoints and session model first. Check cookies/SameSite, anti-CSRF token binding, Origin/Referer enforcement, simple content types, method overrides, GET mutations, GraphQL GET/persisted queries, WebSocket Origin checks, and OAuth connect/logout flows.
- For file uploads, map the full pipeline: ingress, storage key, validation point, metadata, processors, scan queue, CDN/cache, and serving headers. Test extension/MIME/magic mismatches, polyglots, SVG/HTML inline rendering, archive traversal/symlinks, metadata parser sinks, presigned-upload header control, and access-before-scan races.
- For traversal/LFI/RFI, inventory every file operation first: downloads, previews, templates, logs, exports/imports, archives, uploads, and report engines. Probe normalization with encodings, mixed separators, absolute paths, Unicode dots/slashes, proxy/app decode differences, then escalate from read to include, write/extract, wrapper, log/session poisoning, or template execution only when evidence supports it.
- For RCE, identify the execution sink before payload tuning: command wrapper, template engine, expression evaluator, deserializer, media/document converter, build hook, SSRF-to-admin service, or container control plane. Establish a quiet oracle (output, timing, DNS/HTTP callback, file write), confirm context (user, cwd, PATH, shell, sandbox/container), and prove only the smallest control needed for the objective.
- For SQLi, identify query shape before extraction: SELECT/INSERT/UPDATE/DELETE plus WHERE, ORDER, GROUP, LIMIT, JSON/XML, full-text, and identifier positions. Choose the quietest reliable oracle (error, boolean diff, visible UNION, timing, OAST), fingerprint DBMS only as needed, and inspect ORM/query-builder raw fragments such as dynamic identifiers, `LIKE`, `IN`, `ORDER BY`, JSON operators, and report/export filters.
- For SSRF, map every server-side fetcher: URL params, webhooks, previews, imports, renderers, analytics, GraphQL resolvers, and background crawlers. Establish an OAST or timing/status oracle, then test loopback/RFC1918/link-local/IPv6/address-encoded targets, parser differentials, redirect chains, protocol handlers, header/method control, and high-value metadata or control-plane endpoints.
- For XSS, trace source to sink before payload iteration: URL/hash/referrer, postMessage, storage, WebSocket/SSE, server JSON, file metadata, or rendered markdown into HTML, attribute, URL, JS string, CSS, SVG/MathML, DOM API, framework escape hatch, or template sink. Then evaluate sanitizer, CSP, Trusted Types, MIME/sniffing, hydration, and alternate render paths with minimal context-specific proof.
- Confirm vulnerability class with minimal request/response proof, then chain only as far as objective requires.
- Preserve session state across proxy, CLI, and custom scripts.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve source coverage: every imported file is mapped in `references/source-coverage.md` and available in `references/imported/`.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/agentic-workflow.md](references/agentic-workflow.md) — category workflow, tool routing, and technique handoff.
- [references/source-coverage.md](references/source-coverage.md) — no-loss map of preserved imported source files and topics.
- [references/imported/source-skill.md](references/imported/source-skill.md) — preserved, debrandized imported technique material.
- [references/imported/auth-and-access-2.md](references/imported/auth-and-access-2.md) — preserved, debrandized imported technique material.
- [references/imported/auth-and-access.md](references/imported/auth-and-access.md) — preserved, debrandized imported technique material.
- [references/imported/auth-infra.md](references/imported/auth-infra.md) — preserved, debrandized imported technique material.
- [references/imported/auth-jwt.md](references/imported/auth-jwt.md) — preserved, debrandized imported technique material.
- [references/imported/client-side-advanced.md](references/imported/client-side-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/client-side.md](references/imported/client-side.md) — preserved, debrandized imported technique material.
- [references/imported/cves.md](references/imported/cves.md) — preserved, debrandized imported technique material.
- [references/imported/field-notes.md](references/imported/field-notes.md) — preserved, debrandized imported technique material.
- [references/imported/node-and-prototype.md](references/imported/node-and-prototype.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-2.md](references/imported/server-side-2.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-advanced-2.md](references/imported/server-side-advanced-2.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-advanced-3.md](references/imported/server-side-advanced-3.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-advanced-4.md](references/imported/server-side-advanced-4.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-advanced.md](references/imported/server-side-advanced.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-deser.md](references/imported/server-side-deser.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-exec-2.md](references/imported/server-side-exec-2.md) — preserved, debrandized imported technique material.
- [references/imported/server-side-exec.md](references/imported/server-side-exec.md) — preserved, debrandized imported technique material.
- [references/imported/server-side.md](references/imported/server-side.md) — preserved, debrandized imported technique material.
- [references/imported/sql-injection.md](references/imported/sql-injection.md) — preserved, debrandized imported technique material.
- [references/imported/web3.md](references/imported/web3.md) — preserved, debrandized imported technique material.
