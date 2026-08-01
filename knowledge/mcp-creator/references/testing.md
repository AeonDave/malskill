# MCP Server Validation Checklist

## Contents

- [Documentation and spec-claim validation](#documentation-and-spec-claim-validation)
- [Protocol and discovery tests](#protocol-and-discovery-tests)
- [Tool, result, schema, and list tests](#tool-result-schema-and-list-tests)
- [Streamable HTTP tests](#streamable-http-tests)
- [MRTR tests](#mrtr-tests)
- [Tasks extension tests](#tasks-extension-tests)
- [Background worker and administrative lifecycle tests](#background-worker-and-administrative-lifecycle-tests)
- [Subscriptions tests](#subscriptions-tests)
- [Explicit state, workspace, and interactive-process tests](#explicit-state-workspace-and-interactive-process-tests)
- [Data-plane and large-output tests](#data-plane-and-large-output-tests)
- [Security tests](#security-tests)
- [MCP Apps tests](#mcp-apps-tests)
- [Authorization and observability tests](#authorization-and-observability-tests)
- [Compatibility tests](#compatibility-tests)
- [Publication readiness](#publication-readiness)

## Documentation and spec-claim validation

Status scope: MCP Core 2026-07-28, Official MCP Extensions, Custom Application Patterns, and Deprecated / Legacy labeling

Validate the server's own documentation and every MCP conformance claim before publication:

- Confirm native V2 text does not require `initialize`, `notifications/initialized`, `Mcp-Session-Id`, hidden session state, or connection affinity.
- Confirm `server/discover` is documented as server-required and client-optional.
- Confirm no official `tasks/list` method is claimed.
- Confirm no deprecated feature is recommended as a new default.
- Confirm each complete or MRTR result example carries the correct `resultType`.
- Parse fenced examples intended as strict JSON.
- Confirm custom catalogs, workspaces, artifacts, output modes, process handles, registries, hard kill, and admin tools are labelled as custom application behavior.
- Confirm extensions are labelled optional, negotiated, disabled by default, and not implied by core conformance.
- Search for legacy terms, classify each occurrence, and reject any unlabelled recommendation.

## Protocol and discovery tests

Status: MCP Core 2026-07-28

- Call an ordinary supported RPC without a prior discovery request.
- Call `server/discover`; verify supported versions, capabilities, extensions, server identity metadata, `resultType`, `ttlMs`, and `cacheScope`.
- Verify discovery data matches implemented behavior.
- Send an unsupported protocol revision and assert `UnsupportedProtocolVersionError` (`-32022`).
- Omit or corrupt required per-request protocol metadata and assert the specified protocol behavior.
- Verify every request includes protocol version and client capabilities in `_meta`.
- Verify client identity is handled per request and never used as authentication.
- Verify result metadata contains server information where appropriate and it never changes authorization.
- Round-robin related requests across instances; assert no hidden connection state.
- Reuse a connection for unrelated principals/workflows; assert no context bleed.
- Verify lists may vary by current authorization but not previous calls on the connection.

## Tool, result, schema, and list tests

Status: MCP Core 2026-07-28 plus Custom Application Pattern catalog behavior

- Assert the intended direct tool count and names.
- Exercise catalog search, exact lookup, family filters, and unknown-operation suggestions.
- Verify `run_tool` applies the internal operation's policy, risk class, and schema.
- Verify deterministic tool, prompt, resource, template, and catalog ordering.
- Verify `ttlMs` and `cacheScope` are present and semantically correct on cacheable results.
- Compare public/private responses under anonymous, authorized, cross-tenant, revoked, and changed-scope contexts.
- Verify cache keys vary by authorization, protocol revision, and extension settings.
- Exercise default JSON Schema 2020-12 features and supported explicit dialects.
- Verify a no-parameter schema is valid and unambiguous.
- Bound deep schemas, many `$ref`s, compositions, catalog size, validation time, and result size.
- Reject or safely handle external network `$ref`s; never fetch them automatically.
- Validate returned `structuredContent` against `outputSchema`.
- Exercise object, array, scalar, boolean, and null structured content where declared.
- Verify JSON-RPC/protocol errors are distinct from completed tool results with `isError: true`.
- Verify successful tool results use `resultType: "complete"`.

## Streamable HTTP tests

Status: MCP Core 2026-07-28

- Send each request or notification as its own POST.
- Require `MCP-Protocol-Version` and `Mcp-Method`.
- Require `Mcp-Name` for `tools/call`, `resources/read`, `prompts/get`, and other applicable named operations.
- Reject missing, malformed, or header/body-mismatched values with HTTP 400 and `HeaderMismatch` (`-32020`).
- Compare header names case-insensitively and method/name values case-sensitively.
- Generate `Mcp-Param-*` only from valid `x-mcp-header` annotations.
- Exercise nested statically reachable string, integer, and boolean properties.
- Reject annotation on arrays, composition paths, `$ref` paths, unsupported primitive types, duplicates, empty names, and invalid HTTP tokens.
- Encode/decode non-ASCII, control-containing, leading/trailing-whitespace, and sentinel-shaped values with the exact Base64 sentinel.
- Reject CR/LF injection and invalid encoded values.
- Verify sensitive fields, secrets, PII, and bearer handles are never mirrored.
- Reject an invalid present `Origin` with HTTP 403.
- Verify local deployment binds to localhost by default.
- Break a response stream and retry with a new JSON-RPC request ID.
- Exercise idempotency protection for duplicate side-effecting retries.
- Assert no dependency on `Last-Event-ID`, SSE event IDs, event redelivery, HTTP GET streams, or protocol sessions.

## MRTR tests

Status: MCP Core 2026-07-28

- Call each supported MRTR method used by the product and receive `resultType: "input_required"`.
- Verify `inputRequests`, `requestState`, or both are present.
- Verify input request keys are stable, unique within the request, minimal, and understandable.
- Never return an input request type absent from current client capabilities.
- Retry the original method and material arguments with `inputResponses`, exact state, and a new JSON-RPC request ID.
- Exercise accepted, declined, cancelled, malformed, unknown, duplicate, partial, and missing responses.
- Exercise a second `input_required` result when required input remains missing.
- Reject tampered, expired, replayed, cross-principal, cross-tenant, cross-method, and changed-argument state.
- Enforce one-time consumption when the operation requires it.
- Verify any instance can process the retry.
- Assert no destructive side effect before confirmation.
- Assert idempotent behavior after retry or duplicate delivery.
- Confirm MRTR is not used as a durable background execution queue.

## Tasks extension tests

Status: Official MCP Extension — `io.modelcontextprotocol/tasks`

- Advertise Tasks in discovery only when fully implemented and enabled.
- Include Tasks in current request capabilities and verify the server may return either the normal result or `resultType: "task"`.
- Omit Tasks from current request capabilities and assert the server never returns a task.
- Persist the task durably before the Task handle response.
- Verify unique, non-enumerable `taskId`, `ttlMs`, and `pollIntervalMs`.
- Poll with `tasks/get` and respect the suggested interval.
- Exercise `working`, `input_required`, `completed`, `failed`, and `cancelled`.
- Submit accepted, declined, malformed, duplicate, unknown, and late input through `tasks/update`.
- Request cancellation with `tasks/cancel`; test honored and not-honored behavior.
- Verify cooperative acknowledgment is not treated as proof of worker termination.
- Assert `completed`, `failed`, and `cancelled` never transition.
- Resume after client disconnect, server restart, and instance change.
- Exercise expiry, retention, revoked authorization, and result cleanup.
- Reject cross-principal and cross-tenant get, update, cancel, and result access.
- Assert no global Task enumeration and no claim of an official `tasks/list`.
- Receive `notifications/tasks` only through an authorized opted-in subscription when notifications are implemented.
- Verify a client without Tasks receives the documented bounded fallback or actionable capability error.

## Background worker and administrative lifecycle tests

Status: Custom Application Pattern

- Map every internal worker state deterministically to an official Task state.
- Exercise thread, subprocess, and external-job associations used by the implementation.
- Verify timestamps, elapsed time, redacted argument summaries, result/error storage, and bounded status history.
- Exercise concurrent polling/update/cancel without registry races.
- Verify bounded in-memory logs and artifact spooling.
- Exercise retention, cleanup, restart reconciliation, and orphan detection.
- Test cooperative cancel, remote cancel, process-group signal, optional hard kill, and timeout.
- When cancellation or cleanup fails, verify the object remains visible with accurate evidence.
- Authorize and audit custom list, diagnostics, force-cancel, delete, and cleanup tools.
- Verify custom admin tools cannot enumerate or mutate another principal's jobs.

## Subscriptions tests

Status: MCP Core 2026-07-28 plus optional Tasks notifications

- Open `subscriptions/listen` with each supported notification filter.
- Verify `notifications/subscriptions/acknowledged` is first for that subscription and reports the accepted subset.
- Correlate every notification with `io.modelcontextprotocol/subscriptionId`.
- Exercise tool-, prompt-, resource-list, resource-subscription, and Task changes as implemented.
- Assert unrequested or unsupported notification types are not sent.
- Keep request-scoped progress and message notifications on the originating response stream.
- Exercise multiple concurrent subscriptions and demultiplexing on stdio.
- Exercise client cancellation, HTTP stream close, stdio cancellation, graceful closure, disconnect, reconnect, and revoked authorization.
- Enforce concurrent-stream, queue, event-rate, and resource limits.
- Reject cross-principal resource filters and prevent cross-tenant event delivery.
- Verify cleanup leaves no retained unauthorized subscription state.

## Explicit state, workspace, and interactive-process tests

Status: Custom Application Pattern built on MCP Core explicit identifiers

- Create an explicit handle on one instance and use it on another.
- Exercise owner, non-owner, cross-tenant, expired, revoked, malformed, unknown, and replayed handle behavior.
- Verify every handle operation reauthorizes the current principal.
- Exercise workspace path normalization, traversal, absolute escape, symlink escape, quota, and cleanup.
- Verify mutable workspace data and immutable artifacts remain distinct.
- Start an interactive process; read initial output; send input; perform a bounded wait; signal; list authorized handles; close.
- Verify reads return unread output rather than the full history.
- Verify bounded tails and artifact spooling under large output.
- Preserve final unread output through process exit and close.
- Verify process-group cleanup and no orphan remains.
- Assert interactive handles are neither protocol sessions nor Tasks.

## Data-plane and large-output tests

Status: Custom Application Pattern

- Upload a small inline payload and read it back when supported.
- Enforce the inline cap and reject oversized inline input.
- Negotiate a large upload with expected size, SHA-256, MIME type, expiry, and authorization.
- Complete the HTTP/data-plane transfer and verify bytes before artifact commit.
- Reject invalid, expired, replayed, wrong-size, wrong-checksum, cross-principal, and cross-tenant transfer tokens.
- Analyze/list the artifact and import it to an authorized workspace when mutable tools require it.
- Negotiate download and fetch the exact bytes through a short-lived authorized URL.
- Exercise `inline`, `artifact`, and `auto` thresholds.
- Verify preview, truncation indicator, byte size, checksum, MIME type, retention, and fetch instructions.
- Verify artifact metadata and transfer URLs use private caching when authorization-dependent.
- Clean up partial uploads, expired URLs, unclaimed outputs, and deleted workspaces without deleting retained artifacts incorrectly.

## Security tests

Status scope: MCP Core 2026-07-28 and Custom Application Pattern negative tests

- Path traversal, absolute-path escape, symlink escape, and unsafe archive extraction.
- Unsafe URL, redirect pivot, DNS rebinding, private-network target, and scheme/port bypass.
- Destructive operation without verified authorization and confirmation.
- Missing, wrong-issuer, expired, revoked, or insufficient-scope credentials.
- Command injection, shell metacharacters, timeout, resource exhaustion, and orphan cleanup.
- Secret leakage through results, errors, previews, logs, artifacts, Tasks, MRTR state, subscriptions, headers, and trace baggage.
- Identifier enumeration and existence oracles across principals and tenants.
- Oversized requests, pages, catalogs, schemas, descriptions, results, notifications, logs, and uploads.
- Large output unexpectedly returned inline.

## MCP Apps tests

Status: Official MCP Extension; run only when the server implements Apps

- Negotiate Apps support and test the non-UI fallback without it.
- Retrieve each UI resource through the extension contract.
- Enforce sandbox, CSP, permission, size, MIME type, and integrity policy.
- Block disallowed resource, connection, navigation, and embedding origins.
- Validate `postMessage` origin and message shape.
- Mediate tool calls and user consent; reject ambient privilege.
- Verify no access to host cookies, storage, DOM, or parent navigation.
- Revoke authorization and verify the App loses protected access.
- Assert core functionality does not depend on Apps and UI state is not treated as a protocol session.

## Authorization and observability tests

Status: MCP Core 2026-07-28 plus optional authorization extensions

- Validate a present authorization-response `iss` before code redemption.
- Key credentials by issuer and reject reuse with another authorization server.
- Change issuer and require new registration or credentials.
- Exercise Client ID Metadata Documents as the preferred path.
- When DCR compatibility is enabled, verify the correct OpenID Connect `application_type`.
- Verify self-reported client/server identity never grants access or selects a tenant.
- Exercise OAuth Client Credentials or Enterprise-Managed Authorization only when negotiated and configured.
- Propagate valid `traceparent`, `tracestate`, and bounded baggage.
- Reject or neutralize malformed and oversized trace metadata.
- Verify baggage cannot alter authorization, routing, caching, or policy.
- Redact secrets and control telemetry cardinality.
- Verify stdio diagnostics go to stderr and do not corrupt protocol output.

## Compatibility tests

Status: Deprecated / Legacy

- Keep native `2026-07-28` and older protocol tests in separate suites.
- Verify native requests never require a handshake or protocol session.
- If older peers are supported, test the compatibility adapter's exact version selection and lifecycle.
- Verify legacy fallback cannot leak connection-affine context into the native domain layer.
- Assert Roots, Sampling, Logging, HTTP+SSE, deprecated `includeContext` values, and DCR are not native defaults.
- Assert legacy custom detach/job behavior is labelled server-specific and does not masquerade as Tasks.

## Publication readiness

Status scope: quality practice across all implemented categories

Document and verify:

- install, build, run, restart, and cleanup procedures;
- supported protocol revision and real stdio and/or Streamable HTTP smoke command;
- direct tool/resource inventory and any application catalog;
- supported official extensions, settings, fallback, and unsupported cases;
- deprecated-feature policy and compatibility boundary;
- authentication, authorization, tenant, cache, and subscription model;
- explicit handle/workspace lifecycle and backing-store requirements;
- Task retention, polling, update, cancellation, worker cleanup, and orphan policy;
- artifact/data-plane limits, checksums, URLs, retention, and privacy;
- Apps fallback and security policy when implemented;
- environment variables and secret-loading model;
- known limitations as explicit unsupported cases.

Do not claim readiness until unit, integration, transport, security, cleanup, restart, horizontal-handling, and publication checks pass in the real deployment shape.
