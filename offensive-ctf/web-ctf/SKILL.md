---
name: web-ctf
description: "Lab/CTF: web challenges; HTTP apps, APIs, browser clients, auth, uploads, SSRF, XSS, SQLi, SSTI, XXE, deserialization, smuggling."
license: MIT
compatibility: "AgentSkills-compatible agents; local challenge artifacts; authorized training and lab environments."
metadata:
  author: AeonDave
  version: "1.0"
  category: ctf-solving
---

# Web CTF

Goal: solve web-application CTF tasks with professional methodology, curated high-signal references, and reproducible evidence.

## When this skill applies

- HTTP apps, APIs, browser clients, templates, auth flows, file uploads, SSRF, XSS, SQLi, SSTI, XXE, deserialization, request smuggling, GraphQL/WebSocket APIs, or prototype pollution
- tasks requiring endpoint mapping, parameter discovery, exploit chaining, or stateful session testing

## Operating model

1. Classify the dominant artifact, primitive, or objective.
2. Load the closest `offensive-techniques` methodology before selecting tools.
3. Load the closest curated reference for the dominant primitive before touching deep topic banks.
4. Use `sql-injection.md` as the deep bank when the focused SQLi reference is too shallow for the current edge case.
5. Choose the smallest tool chain that can produce a validation signal.
6. Record the exact proof path and stop once the objective is reproducible.

## Technique integration

Primary methodology to load:

- `web-exploit-technique`
- `vuln-search-technique`
- `recon-technique`
- `fuzzing-technique`

Use these as decision engines. This skill adds challenge-oriented triage, time-boxing, and curated reference routing.

## Tool routing

Prefer these tool families when the corresponding signal appears:

- `jwt-tool`
- `commix`
- `xsstrike`
- `smuggler`
- `zap`
- `sqlmap`
- `sstimap`
- `tplmap`
- `ssrfmap`
- `nosqlmap`
- `dalfox`
- `nuclei`
- `ffuf`
- `feroxbuster`
- `httpx`
- `katana`
- `gau`
- `hakrawler`
- `burpsuite`
- `mitmproxy`

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
- For GraphQL, separate schema discovery, resolver auth, batching/alias abuse, depth/cost limits, persisted query behavior, and GET-vs-POST CSRF. Test field-level auth with two principals before chasing injection payloads.
- For WebSocket/SSE, capture the handshake and one normal message flow. Test Origin checks, auth binding after connect, message type confusion, replayed subscriptions, room/channel IDOR, and server-side event injection.
- For request smuggling/desync, fingerprint front-end and back-end behavior first. Use one harmless differential proof before attempting cache poisoning, credential capture, or admin-bot pivots.
- Confirm vulnerability class with minimal request/response proof, then chain only as far as objective requires.
- Preserve session state across proxy, CLI, and custom scripts.

## Quality gates

- No claim without a validation signal: recovered secret, replayed exploit, decoded artifact, reproduced model behavior, or corroborated evidence.
- Do not brute force before representation, constraints, and success oracle are known.
- Keep a pivot ledger: hypothesis, evidence, result, next shortest path.
- Preserve coverage by starting from curated reference packs, then loading deep banks only for unresolved edge cases.
- Keep challenge/platform/competition names out of notes and generated reports.

## Resources

- [references/auth-access-control.md](references/auth-access-control.md) — curated auth pack: sessions, access control, JWT/JWE, OAuth/OIDC/SAML, identity-admin pivots, and auth edge cases.
- [references/browser-attacks.md](references/browser-attacks.md) — curated client/browser pack: XSS, DOM sinks, CSP bypass, XS-leaks, cache poisoning, and Node/prototype chains.
- [references/server-injection.md](references/server-injection.md) — curated server-side sink pack: LFI/traversal, SSTI, SSRF, XXE, parser abuse, and loose-validation flaws.
- [references/server-execution.md](references/server-execution.md) — curated execution pack: runtime injection, upload-to-RCE, deserialization, and advanced framework chains.
- [references/web-vulnerabilities-and-cves.md](references/web-vulnerabilities-and-cves.md) — curated framework/product CVE pack for stack-specific web shortcuts.
- [references/web3-attacks.md](references/web3-attacks.md) — curated Web3/web-wallet/contract interaction pack.
- [references/sql-injection.md](references/sql-injection.md) — deep SQLi bank for DBMS quirks, filter bypasses, second-order cases, timing oracles, and SQL-adjacent injections.

Use the focused references as the primary load path; use the SQLi deep bank when an edge case needs more detail.
