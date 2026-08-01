---
name: mcp-creator
description: "Create, implement, scaffold, migrate, or review production-grade Model Context Protocol (MCP) servers targeting the stateless MCP 2026-07-28 specification. Use when building or refactoring an MCP server; choosing a tool/resource/prompt surface; implementing server/discover, resultType results, Multi Round-Trip Requests (MRTR), Streamable HTTP header routing, cacheable lists, or subscriptions; negotiating official extensions (Tasks, MCP Apps, OAuth Client Credentials, Enterprise-Managed Authorization); designing explicit handles, catalog routing, workspace/artifact/data-plane patterns; hardening MCP server security; migrating a pre-2026-07-28 server off the initialize handshake and Mcp-Session-Id; or validating an MCP server through a real transport before publication."
license: MIT
metadata:
  author: AeonDave
  version: "1.0"
---

# MCP Creator

Create, implement, migrate, and review generic, agent-friendly, production-grade Model Context Protocol servers for databases, files, SaaS APIs, developer tools, automation, analysis systems, and operations workflows.

Target MCP `2026-07-28` by default. Load [protocol-v2.md](references/protocol-v2.md) before implementing wire behavior or making an MCP conformance claim. Classify every behavior explicitly:

- **MCP Core 2026-07-28** — normative core protocol requirement;
- **Official MCP Extension** — optional, negotiated, disabled by default;
- **Custom Application Pattern** — architecture built with ordinary tools, resources, and explicit handles;
- **Deprecated / Legacy** — retained only in an isolated compatibility path;
- **Experimental / Incubating** — only when an official MCP source assigns that status.

Never present a custom pattern as an MCP primitive, or an official extension as core behavior.

## Workflow

1. Define the server's job, users, workflows, external systems, authorization model, and data sensitivity.
2. Load [protocol-v2.md](references/protocol-v2.md). Establish the stateless per-request contract, `server/discover`, result and error layers, transport headers, cache metadata, and supported extensions.
3. Choose the smallest useful direct tool/resource surface. Use catalog routing only when the domain surface is large or dynamic.
4. Classify each operation's execution class:
   - short and bounded: synchronous `resultType: "complete"`;
   - needs more client input mid-call: MRTR `resultType: "input_required"`;
   - durable asynchronous work: Tasks extension `resultType: "task"` when negotiated;
   - arbitrary stdin, incremental output, REPL, debugger, or long-lived process: custom explicit-handle interactive lifecycle.
5. Model cross-call application/workflow state with explicit server-minted handles. Preserve principal-scoped workspaces, immutable artifacts, large-output handoff, and visible cleanup where the product needs them.
6. Load [patterns.md](references/patterns.md) for catalog routing, execution, workspace/artifact, output, lifecycle, Apps, and adapter decisions.
7. Load [security.md](references/security.md) before exposing file, network, command, credential, UI, destructive, stateful, asynchronous, or external-handle capabilities.
8. Keep MCP transport code thin. Isolate domain APIs, SDKs, subprocesses, storage, and external jobs in testable adapters.
9. Load [testing.md](references/testing.md), test through the real configured transport, and verify cleanup, horizontal handling, negative security cases, extension fallback, and publication metadata before claiming readiness.

## Default Design Guidance

- **Direct surface**: expose stable operations directly; use `server/discover` for protocol capabilities and application tools such as `list_catalog`, `get_tool`, and `run_tool` only for product-level discovery and routing.
- **Explicit state**: never rely on a connection, process, or removed protocol session as the continuity boundary.
- **Storage planes**: use mutable principal-scoped workspaces for active work and immutable content-addressed artifacts for large or durable data.
- **Output handoff**: support custom `inline`, `artifact`, and `auto` modes when output can exceed safe MCP response bounds.
- **Lifecycle visibility**: make custom handles, tasks, artifacts, workspaces, subprocesses, and external leases recoverable and cleanable without inventing MCP primitives.
- **Policy visibility**: when a router hides internal operations, expose a safe routing selector through `x-mcp-header`, or use direct tools when infrastructure policy cannot distinguish operations safely.
- **Compatibility**: isolate pre-`2026-07-28` behavior in an adapter. Native V2 flows do not require `initialize`, `notifications/initialized`, `Mcp-Session-Id`, or connection-affine state.

## Deliverables

For a plan or review, provide:

- core RPCs, supported official extensions, and fallback behavior;
- direct tools/resources and any custom catalog families;
- operation execution classes;
- explicit-handle, workspace, artifact, and retention design;
- result, error, cache, subscription, and transport-header contracts;
- authorization and safety controls;
- real-transport validation and publication checks;
- material open questions and explicit unsupported cases.

For implementation, make the smallest cohesive change that establishes these contracts, then verify it with repository-native tooling and a real transport.

## Resources

Load the narrowest reference that matches the current subtask. Keep `SKILL.md` as the navigation layer; keep heavy detail in `references/`.

| Reference | Load when |
|---|---|
| [protocol-v2.md](references/protocol-v2.md) | Wire-level implementation, migration, or any MCP conformance claim |
| [patterns.md](references/patterns.md) | Architecture decisions: catalog routing, execution classes, state, artifacts, Apps, adapters |
| [security.md](references/security.md) | Exposing sensitive, stateful, asynchronous, destructive, UI, file, network, command, or credential behavior |
| [testing.md](references/testing.md) | Before claiming implementation readiness or publication quality |

### Scripts

Deterministic helpers under [scripts/](scripts/):

| Script | Run when |
|---|---|
| `scripts/scaffold_mcp_server.py` | Bootstrap a dependency-free stateless server skeleton (core + stdio + Streamable HTTP + adapters + smoke test) that already implements `server/discover`, `resultType`, cache metadata, MRTR, and header routing. Run `python scripts/scaffold_mcp_server.py <target> --name <server-name> [--transport stdio\|http\|both]`, then `python <target>/smoke_test.py`. |
| `scripts/check_mcp_conformance.py` | Statically lint server source/docs for `2026-07-28` violations (removed sessions/`Last-Event-ID`, `tasks/list`, deprecated handshake/roots/sampling defaults, missing `resultType`/cache metadata/`server/discover`, sensitive `x-mcp-header`). Run `python scripts/check_mcp_conformance.py <path> [--strict]`. Point it at server code, not this skill's references. |

For language-level SDK skeletons and code structure (mainly Python), pair with `coding/mcp-patterns`; when its guidance conflicts with this skill's `2026-07-28` protocol baseline (handshake, sessions, roots, sampling, HTTP+SSE), this baseline is authoritative.
