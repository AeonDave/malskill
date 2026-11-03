---
name: mcp-creator
description: "Build, audit, debug, or integrate an MCP server. Use for protocol and SDK compatibility, tools/resources/prompts, transport, authorization, host setup, and interoperability testing."
license: MIT
metadata:
  author: AeonDave
  version: "1.2"
---

# MCP Creator

Build the smallest MCP surface that serves the active workflow. Preserve existing supported operations and deployment constraints when reviewing or extending a server.

Establish the project's installed SDK, target host, transport, and supported revisions first. For new servers, consider MCP `2026-07-28`; verify compatibility against the official specification and the selected SDK release. Do not migrate a working server merely to repair its launch configuration. Load [protocol-v2.md](references/protocol-v2.md) before changing wire behavior or making an MCP conformance claim. Distinguish:

- **MCP Core 2026-07-28** — normative core protocol requirement;
- **Official MCP Extension** — optional, negotiated, disabled by default;
- **Custom Application Pattern** — architecture built with ordinary tools, resources, and explicit handles;
- **Deprecated / Legacy** — retained only in an isolated compatibility path;
- **Experimental / Incubating** — only when an official MCP source assigns that status.

Never present a custom pattern as an MCP primitive, or an official extension as core behavior.

## Workflow

1. Define the server's job, users, external systems, authorization model, and data sensitivity. Inspect existing entrypoints, configuration, dependencies, and tests.
2. Reuse the repository's language and stack. Prefer an official MCP SDK that supports the selected revision and pin its version. Separate SDK-facing handlers from serialized protocol messages: the SDK may supply discovery, metadata, and result discriminators. Do not add wire fields to domain results or replace SDK transport logic to satisfy a text scan.
3. Choose stdio for a host-launched local process; use Streamable HTTP for a service or shared endpoint when the host supports it. Load [local-integration.md](references/local-integration.md) for launch configuration, SDK migration, local connection failures, or packaging.
4. Select tools for model-callable operations (including read-only search), resources for URI-addressed context, and prompts for user-selected workflow templates. Check what the target host actually exposes. Load [patterns.md](references/patterns.md) for these contracts or when catalog routing, state, artifacts, Apps, or adapters require design.
5. Classify each operation's execution class (wire names below are for `2026-07-28`):
   - short and bounded: synchronous `resultType: "complete"`;
   - needs more client input mid-call: MRTR `resultType: "input_required"`;
   - durable asynchronous work: Tasks extension `resultType: "task"` when negotiated;
   - arbitrary stdin, incremental output, REPL, debugger, or long-lived process: custom explicit-handle interactive lifecycle.
6. Model required cross-call state with explicit server-minted handles. Add workspaces, artifacts, large-output handoff, or lifecycle tools only when the workflow needs them.
7. Implement only the capabilities and extensions the workflow needs; define a bounded fallback or explicit unsupported case when host or SDK support is absent. Use [protocol-v2.md](references/protocol-v2.md) for their wire contract, not as a requirement to implement every feature.
8. Load [security.md](references/security.md) before exposing file, network, command, credential, UI, destructive, stateful, asynchronous, or external-handle capabilities.
9. Keep MCP transport code thin. Isolate domain APIs, SDKs, subprocesses, storage, and external jobs in testable adapters.
10. Load [testing.md](references/testing.md), select checks for the implemented features and deployment, then test through the configured transport with an independent MCP-aware client and the target host before claiming host compatibility.

## Default Design Guidance

The wire-specific rules below apply to `2026-07-28`. For an older supported revision, keep its SDK lifecycle and test that contract; do not manually remove a required handshake or session mechanism.

- **Direct surface**: expose stable operations directly; use `server/discover` for protocol capabilities and application tools such as `list_catalog`, `get_tool`, and `run_tool` only for product-level discovery and routing.
- **Explicit state**: never rely on a connection, process, or removed protocol session as the continuity boundary.
- **Optional state and data planes**: when the workflow needs mutable state or large durable output, use authorized explicit handles and choose the smallest fitting workspace, artifact, or handoff pattern.
- **Lifecycle visibility**: make only the stateful objects the server actually exposes recoverable and cleanable without inventing MCP primitives.
- **Policy visibility**: when a router hides internal operations, expose a safe routing selector through `x-mcp-header`, or use direct tools when infrastructure policy cannot distinguish operations safely.
- **Compatibility**: isolate pre-`2026-07-28` behavior in an adapter. Modern `2026-07-28` flows do not require `initialize`, `notifications/initialized`, `Mcp-Session-Id`, or connection-affine state.

## Deliverables

For a plan or review, include only applicable items. Mark unsupported categories explicitly instead of designing speculative machinery:

- core RPCs, supported official extensions, and fallback behavior;
- direct tools/resources and any custom catalog families;
- operation execution classes;
- explicit-handle, workspace, artifact, and retention design when state or large data requires it;
- applicable result, error, cache, subscription, and transport-header contracts;
- authorization and safety controls;
- real-transport validation and, when publishing, publication checks;
- material open questions and explicit unsupported cases.

For implementation, make the smallest cohesive change that establishes these contracts, then verify it with repository-native tooling and a real transport.

## Resources

Load the narrowest reference that matches the current subtask. Keep `SKILL.md` as the navigation layer; keep heavy detail in `references/`.

| Reference | Load when |
|---|---|
| [protocol-v2.md](references/protocol-v2.md) | Wire-level implementation, migration, or any MCP conformance claim |
| [patterns.md](references/patterns.md) | Surface design: tools/resources/prompts, instructions, catalogs, execution, state, artifacts, Apps, adapters |
| [local-integration.md](references/local-integration.md) | SDK/version selection or migration, host launch configuration, local connection failures, packaging |
| [security.md](references/security.md) | Exposing sensitive, stateful, asynchronous, destructive, UI, file, network, command, or credential behavior |
| [testing.md](references/testing.md) | Before claiming implementation readiness or publication quality |

### Scripts

Deterministic helper under [scripts/](scripts/):

| Script | Run when |
|---|---|
| `scripts/check_mcp_conformance.py` | Review raw `2026-07-28` handlers or migration notes with `python scripts/check_mcp_conformance.py <path> [--strict]`. It checks textual hints only: SDK-managed fields, client code, and older-version adapters can produce false positives. Run against server code, not this skill's references; neither findings nor a clean scan establish conformance. |
