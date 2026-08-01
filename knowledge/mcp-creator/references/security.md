# MCP Server Security Checklist

## Contents

- [Security status and trust boundaries](#security-status-and-trust-boundaries)
- [Tool exposure and destructive actions](#tool-exposure-and-destructive-actions)
- [Files, paths, workspaces, and artifacts](#files-paths-workspaces-and-artifacts)
- [Network, URLs, and external handles](#network-urls-and-external-handles)
- [Commands and subprocesses](#commands-and-subprocesses)
- [Secrets](#secrets)
- [Authentication and authorization](#authentication-and-authorization)
- [Explicit handles and Tasks](#explicit-handles-and-tasks)
- [MRTR continuation state](#mrtr-continuation-state)
- [Streamable HTTP headers and transport](#streamable-http-headers-and-transport)
- [Caching](#caching)
- [Subscriptions and notifications](#subscriptions-and-notifications)
- [OAuth and metadata](#oauth-and-metadata)
- [Schema and resource exhaustion](#schema-and-resource-exhaustion)
- [MCP Apps](#mcp-apps)
- [Observability](#observability)
- [Error handling](#error-handling)

## Security status and trust boundaries

Status: Cross-cutting controls for MCP Core 2026-07-28, Official MCP Extensions, and Custom Application Patterns

Before implementation, identify:

- authenticated principal, tenant, scopes, and credential issuer;
- which metadata is self-reported and therefore untrusted;
- public, private, local-only, and administrative operations;
- data classification, retention, cache scope, and audit requirements;
- trusted server components versus clients, proxies, extension hosts, adapters, and external services.

No opaque identifier, `clientInfo`, `serverInfo`, header, annotation, Task ID, subscription ID, or trace field is proof of authorization.

## Tool exposure and destructive actions

Status: Custom Application Pattern using MCP Core tools and MRTR

- Keep the direct surface small without treating invisibility as access control.
- Mark destructive behavior accurately and require authorization plus explicit confirmation for deletion, overwrite, revoke, publish, send, deploy, execute, or mutation.
- Use MRTR for required interactive confirmation. Perform no irreversible work before an accepted, verified continuation.
- Separate catalog policy classes and risk tiers even when operations share `run_tool`.
- Avoid unrestricted command or HTTP-fetch tools unless they are the product and have strong policy controls.
- Make high-risk behavior discoverable with concise warnings and actionable denial errors.

## Files, paths, workspaces, and artifacts

Status: Custom Application Pattern

- Reject traversal and absolute paths unless explicitly supported.
- Resolve and verify paths under a principal-scoped workspace root before every read, write, import, or delete.
- Never trust a supplied filename as a destination path; normalize to a basename or generate a server-side name.
- Separate mutable workspaces from immutable content-addressed artifacts.
- Authorize workspace handles, artifact IDs, resource URIs, metadata, previews, and transfer URLs on every use.
- Cap inline uploads and route larger data through a bounded, short-lived data plane.
- Verify declared size, SHA-256, MIME type, quota, expiry, and final byte count.
- Prevent cross-tenant artifact import, shared-cache disclosure, unsafe archive extraction, and symlink escape.
- Define cleanup for expired workspaces, partial uploads, artifacts, and unclaimed outputs.

## Network, URLs, and external handles

Status: Custom Application Pattern plus MCP Core Streamable HTTP controls

- Treat URL-taking tools as SSRF-sensitive.
- Validate schemes, hosts, ports, redirects, DNS results, and private/link-local/loopback targets according to product scope.
- Revalidate after redirects and address resolution changes.
- Bind temporary local services to localhost by default.
- Give callbacks, tunnels, download URLs, remote job links, and leases an owner, TTL, revocation path, and cleanup evidence.
- Avoid returning bearer URLs in logs, previews, trace baggage, notifications, or shared cacheable results.

## Commands and subprocesses

Status: Custom Application Pattern

- Prefer argument arrays over shell strings.
- If a shell is unavoidable, document the boundary and constrain every interpolated value.
- Apply deadlines, CPU/memory/file/process limits, process-group cleanup, and output limits.
- Preserve stdout and stderr separately unless merging is an explicit contract.
- Bind interactive-process handles to the principal and tenant on every operation.
- Keep unread-output tails bounded and spool large output to authorized artifacts.
- Preserve final unread output during close and verify that no orphan remains.
- Treat hard kill as implementation-specific; never equate `tasks/cancel` acknowledgment with process termination.

## Secrets

Status: Cross-cutting

- Prefer secret references, workload identity, or environment-bound credentials to raw secret parameters.
- Never echo credentials in tool descriptions, protocol results, errors, logs, events, notifications, trace baggage, artifacts, URLs, or Task state.
- Never annotate secrets, access tokens, passwords, PII, or bearer handles with `x-mcp-header`.
- Redact known sensitive patterns from previews and diagnostics.
- Treat generated logs, downloaded artifacts, request state, and external URLs as potentially sensitive.
- Scope secret access to the adapter and operation that requires it.

## Authentication and authorization

Status: MCP Core 2026-07-28 and deployment policy

- Do not assume transport privacy without an explicit deployment guarantee.
- Define authentication before publication when the server controls accounts, money, infrastructure, files, credentials, or user data.
- Derive the principal from verified authentication, never self-reported identity metadata.
- Perform authorization near each handle, Task, artifact, workspace, subscription, and adapter operation.
- Enforce tenant isolation and least privilege independently of tool discoverability.
- Audit sensitive allow/deny decisions without logging secrets.

## Explicit handles and Tasks

Status: MCP Core explicit-identifier requirement, Official MCP Extension Tasks, and Custom Application Pattern controls

- Authorize every handle and Task on every create, read, update, poll, cancel, close, list, or delete operation.
- Treat an opaque ID as a name, not authorization.
- Use adequate entropy and prevent global enumeration.
- Bind ownership to principal and tenant; reject cross-principal access uniformly.
- Define TTL, inactivity expiry, retention, revocation, and cleanup.
- Persist task state before exposing `taskId`.
- Bind task input updates and cancellation to the owner and outstanding input request.
- Ensure task results, errors, logs, previews, and artifacts inherit the Task's authorization.
- Keep terminal states immutable.
- Distinguish cooperative `tasks/cancel` from worker signals, remote cancellation, process-group kill, and administrative force termination.
- When cancellation or cleanup is not honored, retain accurate state and evidence.

## MRTR continuation state

Status: MCP Core 2026-07-28

- Treat `requestState` as attacker-controlled.
- Protect it with HMAC/AEAD or store it server-side behind an opaque nonce.
- Bind it to principal, tenant, original method, material arguments, requested input IDs, expiry, and policy version.
- Reject tampered, expired, replayed, cross-principal, cross-operation, or argument-mismatched state.
- Enforce server-side single-use when confirmation or redemption must occur at most once.
- Accept only input request types advertised by the client.
- Handle denial and cancellation without side effects.
- Do not execute irreversible work before required confirmation.
- Record denied, expired, replayed, or invalid continuations without exposing state contents or secrets.

## Streamable HTTP headers and transport

Status: MCP Core 2026-07-28

- Validate `Origin` on every incoming connection to prevent DNS rebinding; reject an invalid present origin with HTTP 403.
- Bind local services to `127.0.0.1` by default and authenticate remote services.
- Require `MCP-Protocol-Version` and `Mcp-Method`; require `Mcp-Name` for applicable named operations.
- Decode Base64 sentinel values and compare every recognized routing header with the body.
- Reject missing, malformed, injected, duplicated-conflicting, or mismatched headers with HTTP 400 and `HeaderMismatch` (`-32020`).
- Enforce CR/LF and HTTP field-name constraints.
- Accept `x-mcp-header` only on statically reachable string, integer, or boolean properties with valid unique annotation names.
- Never mirror secrets or PII; assume proxies log routing headers.
- Do not trust a gateway's routing decision as body validation at the server.
- Apply idempotency controls when a broken stream causes a retry with a new request ID.
- Do not implement `Last-Event-ID` or SSE redelivery as a native V2 security assumption.

## Caching

Status: MCP Core 2026-07-28

- Use `cacheScope: "private"` for identity-, tenant-, scope-, entitlement-, or authorization-dependent content.
- Use `public` only when shared intermediary caching cannot disclose or confuse protected state.
- Vary cache keys by principal/tenant where applicable, scopes, protocol version, extensions/settings, locale, and policy-relevant parameters.
- Do not let deterministic ordering expose filtered or hidden entries.
- Shorten TTL or invalidate when permissions, revocations, catalog policy, or sensitive resources change.
- Include artifact metadata, transfer URLs, Task results, and handle-backed resources in the privacy analysis.
- Test shared-cache leakage and downgrade/extension cache confusion.

## Subscriptions and notifications

Status: MCP Core 2026-07-28 plus optional Tasks notifications

- Authorize every requested notification family and resource URI.
- Bind the accepted subscription and ID to the principal and originating request.
- Send only explicitly requested and acknowledged notification types.
- Prevent cross-tenant list, resource, and Task updates.
- Limit concurrent streams, event rate, queue depth, retained events, and reconnect churn.
- Clean up cancellation, disconnect, graceful closure, timeout, and revoked authorization.
- Keep request-scoped progress/message notifications on the originating response stream.
- Do not put credentials, bearer URLs, PII, or secret handles in notifications.

## OAuth and metadata

Status: MCP Core 2026-07-28 plus optional authorization extensions

- Validate a present authorization-response `iss` against the recorded issuer before code redemption.
- Key persisted client credentials by issuer and never reuse them across authorization servers.
- Obtain new credentials when the issuer changes.
- Prefer Client ID Metadata Documents (CIMD).
- When Dynamic Client Registration remains for compatibility, send the appropriate OpenID Connect `application_type`.
- Validate authorization-server metadata, redirect URIs, and issuer transitions.
- Never use `clientInfo`, `serverInfo`, display names, or extension metadata as authentication.
- Apply extension-specific authorization requirements when using OAuth Client Credentials or Enterprise-Managed Authorization.

## Schema and resource exhaustion

Status: MCP Core 2026-07-28

- Validate schemas against the declared or default dialect.
- Bound schema depth, `$ref` count, subschema count, composition complexity, parser recursion, validation time, catalog size, page size, descriptions, and result size.
- Do not automatically fetch arbitrary external `$ref` targets.
- Keep optional network resolution disabled by default and restrict host, address range, time, redirects, and bytes.
- Reject unresolved references instead of treating them as permissive.
- Reject invalid or sensitive `x-mcp-header` annotations and exclude malformed tools as required by the transport behavior.
- Validate returned `structuredContent` against `outputSchema`.

## MCP Apps

Status: Official MCP Extension

When Apps are supported:

- sandbox iframe execution;
- use strict CSP and explicit origin allowlists;
- request least-privilege permissions;
- validate every `postMessage` origin and message shape;
- mediate tool calls and require appropriate user consent;
- prevent ambient host cookie, storage, DOM, and parent-navigation access;
- restrict external navigation and downloads;
- validate UI resource integrity, MIME type, size, and authorization;
- provide meaningful non-UI text and structured fallback;
- do not share custom subprocess or workflow handles with an App without explicit authorization and mediation.

## Observability

Status: MCP Core 2026-07-28 guidance

- Treat `traceparent`, `tracestate`, and `baggage` as untrusted.
- Validate formats, bound baggage size/count, and prevent baggage from changing authorization or policy.
- Redact credentials, PII, bearer handles, artifact URLs, Task input, MRTR state, headers, and command data.
- Control label and span cardinality.
- Separate diagnostics from protocol results.
- Use `stderr` for stdio diagnostics and OpenTelemetry for structured observability.
- Apply request-specific log behavior; do not rely on removed session-level controls.

## Error handling

Status: MCP Core 2026-07-28 error layers plus Custom Application Pattern taxonomy

Return enough information for repair without leaking secrets, raw stack traces, internal paths, tokens, existence of another tenant's objects, or credential state.

Use JSON-RPC/protocol errors for protocol failures and completed tool results with `isError: true` for execution failures. Stable application error types may include:

- `permission_denied`;
- `invalid_path`;
- `unsafe_url`;
- `missing_credential`;
- `unsupported_operation`;
- `unsupported_capability`;
- `dependency_missing`;
- `unknown_handle`;
- `expired_handle`;
- `revoked_handle`;
- `rate_limited`;
- `timeout`;
- `cancelled`;
- `cleanup_incomplete`.
