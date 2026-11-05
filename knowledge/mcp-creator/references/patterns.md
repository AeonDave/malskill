# MCP Server Design Patterns

## Contents

- [Status legend](#status-legend)
- [Protocol primitives versus application tools](#protocol-primitives-versus-application-tools)
- [Tool surface](#tool-surface)
- [Resources, prompts, and instructions](#resources-prompts-and-instructions)
- [Catalog pattern](#catalog-pattern)
- [Router and HTTP policy visibility](#router-and-http-policy-visibility)
- [Tool contracts and error layers](#tool-contracts-and-error-layers)
- [Execution decision tree](#execution-decision-tree)
- [MRTR pattern](#mrtr-pattern)
- [Tasks extension pattern](#tasks-extension-pattern)
- [Background worker implementation pattern](#background-worker-implementation-pattern)
- [Administrative job tools](#administrative-job-tools)
- [Interactive process handle pattern](#interactive-process-handle-pattern)
- [Explicit state and workspace pattern](#explicit-state-and-workspace-pattern)
- [Artifact and data-plane pattern](#artifact-and-data-plane-pattern)
- [Large-output handoff](#large-output-handoff)
- [Cacheable discovery pattern](#cacheable-discovery-pattern)
- [Subscription pattern](#subscription-pattern)
- [Extension negotiation pattern](#extension-negotiation-pattern)
- [MCP Apps decision pattern](#mcp-apps-decision-pattern)
- [External handle pattern](#external-handle-pattern)
- [Adapter pattern](#adapter-pattern)
- [Legacy compatibility](#legacy-compatibility)

## Status legend

- **MCP Core 2026-07-28**: required or defined by the core protocol.
- **Official MCP Extension**: optional negotiated behavior outside core.
- **Custom Application Pattern**: server architecture implemented through ordinary MCP features.
- **Deprecated / Legacy**: compatibility-only behavior, not a new-design default.
- **Experimental / Incubating**: use only when an official source assigns this status.

## Protocol primitives versus application tools

Status: MCP Core 2026-07-28 and Official MCP Extension boundary

- Core RPCs/patterns include `server/discover`, `tools/list`, `tools/call`, MRTR, and `subscriptions/listen`.
- Tasks RPCs (`tasks/get`, `tasks/update`, `tasks/cancel`) belong to the optional `io.modelcontextprotocol/tasks` extension.
- `list_catalog`, `search_catalog`, `get_tool`, `run_tool`, workspace tools, artifact tools, interactive-process tools, and administrative lifecycle tools are Custom Application Patterns.
- Do not expose protocol RPC names as domain tools merely to imitate MCP.
- Do not use `list_capabilities` for generic protocol discovery. Retain a product capability tool only when it returns product-specific information, and name it accordingly.

## Tool surface

Status: Custom Application Pattern

Start with the smallest useful direct surface:

- expose a small, stable domain surface directly;
- use `server/discover` for protocol versions, capabilities, identity, and extensions;
- add `list_catalog`, optional `search_catalog`, and `get_tool` only for product/catalog discovery;
- add `run_tool` when the product surface is large or dynamic;
- add workspace, artifact, state, or lifecycle tools only when the user workflow requires them.

Keep high-risk tools visible with accurate warnings and policy classes. Hiding a tool is not an authorization control.

## Resources, prompts, and instructions

Choose by interaction model and host support, not solely by whether an operation writes data:

| Need | Surface |
|---|---|
| Model chooses an operation with arguments, including search or computation | Tool, with accurate side-effect annotations |
| Host/application fetches identifiable context | Resource or URI template |
| User selects reusable task framing | Prompt with explicit arguments and message output |
| A constraint spans several server features | Short server instructions, only for that shared constraint |

- Give resources stable URI semantics, correct text/binary content and MIME types, bounded reads, and authorization on both listing and retrieval. Validate template parameters before resolving paths or remote URLs.
- Use pagination for list methods that support it; make large content retrievable in bounded pieces rather than dumping it all into context. A linked resource need not appear in `resources/list`; test that the target client can retrieve it.
- Check whether the host browses resources, resolves templates, or exposes prompts. Return useful tool content when the workflow needs a tool-only host; do not assume resource publication automatically inserts it into model context.
- Keep prompts focused on reusable framing and required inputs; validate arguments and resource access. Retrieving a prompt must not perform the mutation it describes.
- Use server instructions for cross-tool ordering, prerequisites, or capability-dependent fallbacks. Put per-operation meaning in the tool/resource description. Instructions do not enforce policy; reject forbidden operations in code.
- Treat resource, prompt, and upstream content as untrusted task data; preserve the trust boundary in [security.md](security.md).

Contracts: [Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources), [Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts). For callable operations, define the [tool contract and error layers](#tool-contracts-and-error-layers).

## Catalog pattern

Status: Custom Application Pattern  
Protocol dependency: `tools/call` and JSON Schema from MCP Core 2026-07-28

A catalog entry should include:

- stable `name`, concise `description`, `family` or phase, and product `domain`;
- JSON Schema 2020-12 input and output contracts;
- relevant ToolAnnotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`);
- required core capability or extension and fallback behavior;
- execution class: synchronous, MRTR, Tasks-capable, or custom interactive;
- confirmation/input behavior;
- supported output modes;
- infrastructure routing key, policy class, or risk tier where useful;
- examples or hints only when the schema is insufficient.

Return deterministic catalog ordering. Reject unknown operation names with safe search suggestions.

Prefer negotiated Tasks for interoperable asynchronous execution. If the supported SDK or host lacks it, use a bounded synchronous path, an explicit unsupported result, or a documented application job API when the product needs one. Label custom handles and polling as application behavior; do not claim Tasks support or silently start work the client cannot track.

## Router and HTTP policy visibility

Status: Custom Application Pattern using MCP Core 2026-07-28 header routing

`run_tool` reduces direct tool count but hides the internal operation from HTTP infrastructure: `Mcp-Name` identifies `run_tool`, not the catalog entry.

When gateways, WAFs, audit systems, tenancy controls, or rate limiters need the internal operation:

1. Make the operation selector a safe primitive schema property.
2. Annotate it with `x-mcp-header`, for example `"x-mcp-header": "Operation"`.
3. Expect `Mcp-Param-Operation` on Streamable HTTP.
4. Validate the header against the body before dispatch.
5. Apply policy to the internal operation, not only the public router.

```json
{
  "name": "run_tool",
  "inputSchema": {
    "type": "object",
    "properties": {
      "operation": {
        "type": "string",
        "x-mcp-header": "Operation"
      },
      "arguments": {
        "type": "object"
      }
    },
    "required": ["operation", "arguments"]
  }
}
```

Never mirror secrets, tokens, credentials, PII, queries containing sensitive data, or bearer handles. Use a small set of direct tools when separate infrastructure policy cannot be expressed safely through one router.

## Tool contracts and error layers

Use the [protocol result/error contract](protocol-v2.md#results-structured-content-and-errors). Check the SDK's exception-to-result mapping: a domain failure must not accidentally become a protocol error, or vice versa.

Declare stable input/output schemas, bound returned data, and use accurate `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint` annotations. Hints describe behavior; they do not authorize it. An optional application envelope belongs inside `structuredContent`, only when downstream consumers need it. Do not add empty `warnings`, `artifacts`, or `next` fields to every result by convention.

## Execution decision tree

Status: Mixed — MCP Core, Official MCP Extension, and Custom Application Pattern

```text
Short, bounded, no additional input
→ MCP Core: synchronous resultType "complete"

Needs user/client/model input before completion
→ MCP Core: MRTR resultType "input_required"

Long-running and must survive timeout, disconnect, or restart
→ Official MCP Extension: Tasks when negotiated

Requires arbitrary stdin, incremental output, REPL, shell, debugger,
or long-lived interactive process
→ Custom Application Pattern: explicit-handle interactive lifecycle
```

Patterns may compose: a Task can enter `input_required`; an interactive process can launch background work; any class may hand large output to an artifact.

## MRTR pattern

Use the [MRTR contract](protocol-v2.md#multi-round-trip-requests) for required supported client input, not a job queue. Request only missing information, give input requests understandable keys, and handle refusal without inventing consent or unsafe defaults.

Apply [continuation-state controls](security.md#mrtr-continuation-state) before resuming side effects. If the client cannot supply required input, use an authorized non-interactive path or return an actionable unsupported case.

## Tasks extension pattern

Use the [Tasks contract](protocol-v2.md#tasks) only when the SDK, server, and client support the extension. Keep the [worker implementation](#background-worker-implementation-pattern) distinct from the wire lifecycle.

Publish retention, expiry, cancellation semantics, unsupported-client fallback, and whether cancellation can leave external work running. Authorize each Task and inherited result/artifact through [security.md](security.md#explicit-handles-and-tasks).

## Background worker implementation pattern

Status: Custom Application Pattern  
Protocol dependency: may back the Tasks extension but is not defined by it

Maintain a concurrency-safe registry or durable store with:

- internal ID and mapped Task ID;
- operation name and redacted argument summary;
- worker/thread/process/external-job association;
- internal state and explicit mapping to official Task status;
- creation, update, start, finish, expiry, and elapsed timestamps;
- result, structured error, bounded status history, and artifact references;
- condition variable/event mechanism for efficient polling;
- cooperative cancel hook and optional hard `kill_fn`;
- bounded retention, cleanup state, and orphan-detection evidence.

Persist durable state before returning the public Task handle. Bound logs in memory and spool large output to authorized artifacts. If termination or cleanup fails, retain visible evidence rather than reporting success.

Hard process termination is implementation-specific. It is stronger than, and distinct from, cooperative `tasks/cancel`.

## Administrative job tools

Status: Custom Application Pattern

Allow `list_jobs`, `delete_job`, force-cancel, cleanup, or diagnostics only as explicit application/admin tools:

- require least-privilege authorization and principal/tenant scoping;
- use non-enumerable IDs and pagination;
- audit reads and mutations;
- distinguish cleanup from Task protocol operations;
- never claim these tools implement `tasks/list`;
- do not delete evidence while underlying work or cleanup remains unresolved.

## Interactive process handle pattern

Status: Custom Application Pattern  
MCP provides no interactive-process primitive; Tasks does not replace this lifecycle.

Expose only the operations the product needs:

- create/start and return an explicit handle;
- send input;
- read unread output with an optional bounded wait;
- signal;
- list handles authorized to the caller;
- close and clean up.

Require principal binding, tenant isolation, TTL, revocation, instance-independent lookup, process-group cleanup, and final unread-output preservation. Reads return unread output rather than the full history. Use bounded in-memory tails and authorized artifact spooling for large output.

A custom long-poll read is not `subscriptions/listen`, Tasks polling, or request-scoped progress. Name and document it as application behavior.

## Explicit state and workspace pattern

Status: Custom Application Pattern built on MCP Core explicit identifiers

Use:

- explicit application/workflow state;
- a visible workflow handle;
- a principal-scoped workspace;
- an instance-independent backing store;
- an explicit lifecycle with expiry and cleanup.

Mutable workspace files support active work. Immutable content-addressed artifacts support durable or large data. Validate ownership, tenant, handle state, and paths on every operation. Never infer the workspace from a protocol connection or call it session-local.

## Artifact and data-plane pattern

Status: Custom Application Pattern

MCP does not provide a generic artifact store or presigned transfer protocol. When the product needs large byte transfer:

1. Cap inline data.
2. Negotiate expected byte size, SHA-256, MIME type, and filename metadata.
3. Return a short-lived, principal-bound upload token or URL.
4. Transfer bytes over the separate data plane.
5. Verify size and checksum before committing.
6. Return an artifact ID or resource URI.

Reverse the pattern for download: authorize the artifact, mint a short-lived URL/token, and return size, checksum, MIME type, expiry, and fetch instructions. Prevent token replay and cross-tenant import.

## Large-output handoff

Status: Custom Application Pattern

For logs, reports, exports, traces, query results, and generated files, support only the modes the product needs:

- `inline`: explicit small response;
- `artifact`: forced artifact handoff;
- `auto`: threshold-based selection.

These mode names are not MCP-standardized. Fit the response inside an ordinary complete tool result and, where useful, expose the artifact as an MCP resource. Return preview, truncation indicator, byte size, checksum, MIME type, retention, authorization scope, and fetch instructions.

## Cacheable discovery pattern

Use the [cache contract](protocol-v2.md#cacheable-discovery-lists-and-reads) and [cache isolation controls](security.md#caching); test invalidation and authorization changes.

Caching provider metadata or a custom catalog behind application tools is separate application behavior. Define its own freshness and invalidation policy.

## Subscription pattern

Use the [subscription contract](protocol-v2.md#subscriptions-and-notifications) and authorize each filter. Keep change notifications, request-scoped progress/logs, Tasks status, and custom process-output reads distinct. Add subscriptions only when clients need change delivery; bounded queues and cleanup belong to the implementation.

## Extension negotiation pattern

Use the [extension contract](protocol-v2.md#extensions-framework). Check actual SDK/host support, declare required settings, and test the documented fallback or rejection with the extension absent.

## MCP Apps decision pattern

Status: Official MCP Extension

Choose MCP Apps only when embedded interactivity materially improves the workflow:

- declare and serve the UI resource through extension metadata;
- retain useful text and structured output for non-Apps clients;
- treat host and permission support as optional;
- minimize requested permissions and external origins;
- define mediated tool calls and consent boundaries;
- separate App UI state from core transport behavior and custom subprocess handles.

Do not make core server functionality depend on UI support.

## External handle pattern

Status: Custom Application Pattern

URLs, sockets, callback endpoints, temporary files, remote job links, dashboards, tunnels, and leases need:

- an owning principal/tenant and external-service ownership check;
- opaque, non-enumerable identifiers where applicable;
- TTL, revocation, retention, and cleanup;
- access instructions without secret disclosure;
- evidence when remote revocation or cleanup fails.

Usually return metadata and client hints rather than embedding a protocol-specific client in the MCP server unless that client is the product.

## Adapter pattern

Status: Custom Application Pattern

Keep the MCP boundary thin:

- request metadata, capability negotiation, transport headers, schemas, auth context, routing, result normalization, and extension mapping stay near MCP;
- external APIs, SDK wrappers, subprocesses, databases, storage, artifacts, and external jobs stay in adapters;
- unit-test adapters without starting the server;
- run live tests through the full MCP transport.

Adapters return explicit readiness failures: missing binary, missing credential, unsupported operation, dependency missing, permission denied, rate limited, or remote service unavailable.

## Legacy compatibility

Status: Deprecated / Legacy

Modern MCP targets `2026-07-28`. If older peers are required:

- isolate handshake, older transport, session, or detached-job compatibility in an adapter;
- keep native and legacy tests separate;
- never let compatibility reintroduce hidden connection-affine state into the modern domain design;
- label custom `detach=true`, `job_id`, `poll_job`, and old status vocabulary as server-specific compatibility contracts;
- prefer negotiated Tasks for interoperable new asynchronous designs.
