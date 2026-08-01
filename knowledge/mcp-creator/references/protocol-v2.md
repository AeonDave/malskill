# MCP 2026-07-28 Protocol Baseline

Target revision: MCP `2026-07-28`  
Authority: Final MCP specification and official extension specifications  
Purpose: Normative baseline and migration guardrails; application design patterns live in [patterns.md](patterns.md)

## Contents

- [Status legend](#status-legend)
- [Stateless core](#stateless-core)
- [Explicit application handles](#explicit-application-handles)
- [Results, structured content, and errors](#results-structured-content-and-errors)
- [JSON Schema](#json-schema)
- [Multi Round-Trip Requests](#multi-round-trip-requests)
- [Streamable HTTP](#streamable-http)
- [Cacheable discovery, lists, and reads](#cacheable-discovery-lists-and-reads)
- [Subscriptions and notifications](#subscriptions-and-notifications)
- [Extensions framework](#extensions-framework)
- [Tasks](#tasks)
- [MCP Apps](#mcp-apps)
- [Authorization extensions](#authorization-extensions)
- [Authorization hardening](#authorization-hardening)
- [Observability](#observability)
- [Deprecated features](#deprecated-features)
- [Migration checklist](#migration-checklist)
- [Official sources](#official-sources)

## Status legend

Use these exact classifications:

- **MCP Core 2026-07-28**: normative core behavior.
- **Official MCP Extension**: optional negotiated behavior outside core.
- **Custom Application Pattern**: useful architecture not defined by MCP wire semantics.
- **Deprecated / Legacy**: still supported during a deprecation window or isolated for compatibility; not a new-design default.
- **Experimental / Incubating**: use only when official MCP material assigns that status.

## Stateless core

Status: MCP Core 2026-07-28

- Native `2026-07-28` operation has no `initialize` / `notifications/initialized` handshake.
- There is no `Mcp-Session-Id` or protocol-level session.
- Every request carries `_meta["io.modelcontextprotocol/protocolVersion"]` and `_meta["io.modelcontextprotocol/clientCapabilities"]`.
- Clients SHOULD include `_meta["io.modelcontextprotocol/clientInfo"]` on each request.
- Servers SHOULD include `_meta["io.modelcontextprotocol/serverInfo"]` in each result.
- Self-reported client or server information is display, logging, and debugging metadata, not an authenticated principal or an authorization input.
- Each request is self-contained and may be served by any instance. Do not infer context, capabilities, identity, or authorization from a connection or a previous call.
- Lists may vary by per-request authorization, protocol version, and negotiated extensions; they do not vary as hidden connection-affine state.
- Cross-call application state uses explicit identifiers carried as ordinary arguments.
- Servers MUST implement `server/discover`. Clients MAY call it before another RPC but may issue an ordinary RPC without prior discovery.
- `server/discover` is an MCP RPC, not a domain discovery tool. Its `DiscoverResult` includes `resultType: "complete"`, `supportedVersions`, `capabilities`, `_meta["io.modelcontextprotocol/serverInfo"]`, optional natural-language `instructions`, and cache metadata.
- An unsupported revision uses `UnsupportedProtocolVersionError` (`-32022`), not an application tool error. A server that requires a client capability the request did not advertise uses `MissingRequiredClientCapabilityError`.

## Explicit application handles

Status: MCP Core 2026-07-28 wire fact plus Custom Application Pattern controls

MCP defines no wire-level state-handle primitive. A handle is an ordinary result value and an ordinary argument. Design handle-backed state to be:

- opaque and non-enumerable;
- generated with adequate entropy when possession grants access;
- authorized against the authenticated principal and tenant on every use;
- bounded by documented expiry, retention, and cleanup;
- revocable, closable, or deletable when the lifecycle benefits from it;
- accessible from any server instance through an instance-independent backing store when horizontal handling is required;
- recoverable through actionable tool execution errors for unknown, expired, revoked, or unauthorized handles.

Treat the handle as a name, not proof of authorization, whenever an authenticated principal exists.

## Results, structured content, and errors

Status: MCP Core 2026-07-28

Every successful MCP result contains `resultType`:

- `"complete"` for ordinary completed results;
- `"input_required"` for an MRTR interim result;
- `"task"` only for a Tasks-enabled result under the negotiated extension.

Clients MUST treat a result from an earlier-protocol server that omits `resultType` as `"complete"`.

Keep three layers distinct:

1. JSON-RPC or protocol errors describe malformed requests, unsupported protocol behavior, invalid parameters, or server failures at the RPC layer.
2. Tool execution failures return a completed tool result with actionable content and `isError: true`.
3. Domain conventions may place stable application data inside `structuredContent`.

The original envelope remains a Custom Application Pattern inside a core result, not a replacement for it:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "{\"ok\":true,\"result\":{},\"warnings\":[],\"artifacts\":[],\"next\":[]}"
      }
    ],
    "structuredContent": {
      "ok": true,
      "result": {},
      "warnings": [],
      "artifacts": [],
      "next": []
    },
    "isError": false
  }
}
```

`structuredContent` may be any JSON value. When the tool declares `outputSchema`, the server MUST return structured data conforming to it; clients SHOULD validate it. Return serialized JSON in text content when broad compatibility benefits from a text fallback.

## JSON Schema

Status: MCP Core 2026-07-28

- Tool `inputSchema` and `outputSchema` default to JSON Schema 2020-12 when `$schema` is absent.
- Implementations MUST support 2020-12 and gracefully reject unsupported explicit dialects.
- A no-parameter tool should use an explicit object schema, preferably `{"type":"object","additionalProperties":false}`.
- Support composition and `$ref` only with bounded schema depth, subschema count, parser recursion, validation time, and result size.
- Do not automatically fetch network `$ref` targets. Any opt-in resolver stays disabled by default, uses allowlists, blocks local/private targets, and applies time and size limits.
- Reject unresolved external references rather than treating the schema as permissive.
- Validate returned `structuredContent` against `outputSchema`.

## Multi Round-Trip Requests

Status: MCP Core 2026-07-28

MRTR is a continuation/input pattern for supported requests (`prompts/get`, `resources/read`, and `tools/call`), not durable asynchronous execution. It replaces server-initiated requests (`roots/list`, `sampling/createMessage`, `elicitation/create`):

1. The client sends an ordinary RPC.
2. The server returns `resultType: "input_required"` with `inputRequests`, optional opaque `requestState`, or both.
3. The client obtains supported answers or confirmation.
4. The client retries the original method and material arguments with `inputResponses` and the exact returned `requestState`.
5. The retry uses a new JSON-RPC request ID.
6. Any server instance can process the retry from its contents.

Servers MUST NOT place a request type in `inputRequests` unless the client advertised that capability. Do not send unsolicited server-to-client requests outside the active client request. Missing information, destructive confirmation, elicitation, and other advertised client inputs can use MRTR.

Treat `requestState` as attacker-controlled. Authenticate or integrity-protect it, or store state server-side behind an opaque nonce. Bind it to the authenticated principal, originating method, material arguments, requested input IDs, expiry, and the required replay or one-time-use policy. Reject tampered, expired, cross-principal, replayed, or argument-mismatched state. Do not perform irreversible work before required confirmation.

## Streamable HTTP

Status: MCP Core 2026-07-28

- Expose one MCP endpoint accepting POST; send each JSON-RPC request or notification as its own POST.
- Include `MCP-Protocol-Version` and `Mcp-Method` on every request.
- Include `Mcp-Name` for named operations such as `tools/call` (`params.name`), `resources/read` (`params.uri`), and `prompts/get` (`params.name`).
- Validate required headers and body consistency. A mismatch or malformed required header returns HTTP 400 with `HeaderMismatch` (`-32020`).
- A schema property may use `x-mcp-header` to mirror a statically reachable primitive string, integer, or boolean into `Mcp-Param-{Name}`. The annotation name must be a valid, unique HTTP field-name token.
- Never annotate passwords, API keys, access tokens, secrets, bearer handles, or PII. Proxies and intermediaries commonly log headers.
- Use the exact `=?base64?{Base64EncodedValue}?=` sentinel for non-ASCII, control-containing, leading/trailing-whitespace, or sentinel-shaped values. Decode before comparing with the body.
- Validate `Origin` on all incoming connections; return HTTP 403 for an invalid present origin. Bind local servers to `127.0.0.1` by default.
- SSE, when used, is scoped to the originating request. Do not depend on `Last-Event-ID`, SSE event IDs, resumability, or event redelivery.
- A broken response stream loses the in-flight request. Retry as a new request with a new JSON-RPC request ID and apply operation-specific idempotency controls.

## Cacheable discovery, lists, and reads

Status: MCP Core 2026-07-28

`server/discover`, `tools/list`, `prompts/list`, `resources/list`, `resources/read`, and `resources/templates/list` use cache metadata. The latter five require `ttlMs` and `cacheScope`:

- `ttlMs` is a freshness hint in milliseconds.
- `cacheScope: "public"` permits shared caching only when the content is not identity- or authorization-dependent.
- `cacheScope: "private"` is required for identity-, tenant-, scope-, or authorization-varying content.
- Return deterministic ordering while the underlying set is unchanged.
- Include principal/tenant, scopes, protocol version, negotiated extensions, and other authorization-relevant dimensions in cache variation.
- `listChanged` notifications complement freshness metadata; they do not replace TTLs or safe cache keys.

## Subscriptions and notifications

Status: MCP Core 2026-07-28

- `subscriptions/listen` opens an opted-in long-lived change-notification stream.
- Clients request specific notification families. Servers MUST NOT send unrequested types.
- The first stream message is `notifications/subscriptions/acknowledged`; it reports the accepted filter and carries `_meta["io.modelcontextprotocol/subscriptionId"]`.
- Every notification on the stream carries the subscription ID for correlation.
- Authorize filters and resource URIs, limit streams and event rates, and clean up on cancel, closure, disconnect, or expiry.
- Request-scoped `notifications/progress` and `notifications/message` stay on the originating request's response stream.
- Tasks notifications use this mechanism when the extension supports them. Polling remains the Tasks baseline.

## Extensions framework

Status: MCP Core 2026-07-28 negotiation rules

- Extensions are optional, independently evolving, disabled by default, and require explicit implementation opt-in.
- Clients advertise extension support in each request's client capabilities.
- Servers advertise supported extensions in `server/discover`.
- Official identifiers use the `io.modelcontextprotocol` vendor prefix. Third-party identifiers use a reversed domain controlled by the publisher.
- Specify settings/version behavior and either a core fallback or an explicit error when a required extension is absent.
- Core conformance does not imply that an SDK implements any extension.

Relevant official families include Tasks, MCP Apps, OAuth Client Credentials, and Enterprise-Managed Authorization. A generic server implements only the extensions its product requires.

## Tasks

Status: Official MCP Extension — `io.modelcontextprotocol/tasks`

Negotiation: the client includes the extension in the current request's capabilities; the server advertises it through `server/discover`.

- The server decides whether a supported request returns an ordinary result or `resultType: "task"`.
- Never return a task when the current request does not advertise Tasks support.
- Persist task state durably before returning `taskId`.
- The lifecycle uses `tasks/get`, `tasks/update`, and `tasks/cancel`.
- Statuses are `working`, `input_required`, `completed`, `failed`, and `cancelled`.
- `completed`, `failed`, and `cancelled` are terminal and immutable.
- Respect `pollIntervalMs`; task IDs and state survive disconnect and restart.
- `tasks/update` supplies `inputResponses` for outstanding task input.
- `tasks/cancel` is cooperative. Acknowledgment does not prove the underlying work stopped.
- `notifications/tasks` is optional through an opted-in `subscriptions/listen` stream; polling is the default.
- There is no official `tasks/list`.

Worker registries, process associations, retention, hard-kill hooks, bounded logs, artifact spooling, orphan detection, and admin cleanup remain Custom Application Patterns. Map internal states deterministically to official Task states.

## MCP Apps

Status: Official MCP Extension

Use MCP Apps only when an embedded interactive UI materially improves a workflow beyond text and structured content:

- declare and serve UI resources through the extension's metadata and resource contract;
- provide meaningful non-UI text and structured fallback;
- treat host support as optional;
- sandbox UI execution, enforce CSP and origin allowlists, minimize permissions, validate messaging origins, and mediate tool calls with appropriate consent;
- do not confuse an App's UI lifecycle or `ui/initialize` dialect with MCP core transport state, protocol sessions, or custom interactive-process handles.

## Authorization extensions

Status: Official MCP Extension

OAuth Client Credentials supports machine-to-machine authentication. Enterprise-Managed Authorization supports centrally controlled enterprise access. Negotiate only the extension required by the deployment, publish fallback or rejection behavior, and do not imply that either is mandatory for generic MCP servers.

## Authorization hardening

Status: MCP Core 2026-07-28

- When an OAuth authorization response includes `iss`, validate it against the recorded issuer before redeeming the code.
- Key persisted client credentials by issuer. Never reuse them with another authorization server; obtain new credentials when the issuer changes.
- Prefer Client ID Metadata Documents (CIMD) to Dynamic Client Registration (DCR).
- When DCR remains for compatibility, send the OpenID Connect `application_type` appropriate to the client.
- Do not use self-reported `clientInfo` or `serverInfo` for authentication, tenant selection, or authorization.

## Observability

Status: MCP Core 2026-07-28 guidance

- Propagate documented W3C Trace Context keys (`traceparent`, `tracestate`, `baggage`) in `_meta` when supported.
- Treat every trace field and baggage item as untrusted input.
- Redact secrets, PII, bearer handles, and artifact URLs; bound baggage and label cardinality.
- Use OpenTelemetry for structured remote observability and `stderr` for stdio diagnostics.
- Configure request logging per request, including `_meta["io.modelcontextprotocol/logLevel"]` where supported; do not rely on removed session-level logging controls.

## Deprecated features

Status: Deprecated / Legacy

Deprecation is not removal, but new designs SHOULD NOT adopt these defaults:

- Roots: pass directories/files through tool parameters, resource URIs, or server configuration.
- Sampling: integrate directly with model-provider APIs.
- Logging: use `stderr` for stdio diagnostics and OpenTelemetry for observability.
- HTTP+SSE: use Streamable HTTP.
- `includeContext: "thisServer"` and `"allServers"`: omit `includeContext` or use `"none"` while compatibility remains necessary.
- Dynamic Client Registration: use Client ID Metadata Documents; retain DCR only as a hardened compatibility path.

Also removed from native `2026-07-28` behavior: `initialize`, `notifications/initialized`, protocol sessions, `Mcp-Session-Id`, `ping`, `logging/setLevel`, `notifications/roots/list_changed`, the HTTP GET stream, `resources/subscribe`, `resources/unsubscribe`, and SSE redelivery semantics.

## Migration checklist

Status: MCP Core 2026-07-28 plus Deprecated / Legacy isolation

- Remove native handshake and connection-affine state assumptions.
- Add required per-request metadata and server result identity metadata.
- Implement `server/discover` and standard unsupported-version behavior.
- Add `resultType` to every result.
- Replace server-initiated requests with MRTR on supported RPCs.
- Replace public detached-job contracts with negotiated Tasks where interoperability is required; keep stronger worker internals as custom implementation guidance.
- Replace hidden sessions with explicit authorized handles.
- Add Streamable HTTP routing headers, cache metadata, deterministic ordering, and subscription streams.
- Quarantine pre-2026 behavior in a compatibility adapter and test both paths.
- Document each custom application pattern as non-standard.

## Official sources

- [2026-07-28 release announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [2026-07-28 key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)
- [Discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Subscriptions](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Deprecated features](https://modelcontextprotocol.io/specification/2026-07-28/deprecated)
- [Extensions overview](https://modelcontextprotocol.io/extensions/overview)
- [Tasks overview](https://modelcontextprotocol.io/extensions/tasks/overview)
- [MCP Apps overview](https://modelcontextprotocol.io/extensions/apps/overview)
- [OAuth Client Credentials](https://modelcontextprotocol.io/extensions/auth/oauth-client-credentials)
- [Enterprise-Managed Authorization](https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization)
