---
name: mcp-creator
description: "Create, implement, scaffold, migrate, or review Model Context Protocol (MCP) servers against modern MCP 2026-07-28. Use for server architecture, tool/resource/prompt contracts, stdio or Streamable HTTP transports, MRTR, optional extensions, authorization, security, and real-transport validation. Also use to isolate legacy initialization or session behavior. Do not use merely to configure an MCP client or invoke an existing server."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
---

# MCP Creator

Create, implement, migrate, and review generic, agent-friendly, production-grade Model Context Protocol servers for databases, files, SaaS APIs, developer tools, automation, analysis systems, and operations workflows.

Target modern MCP `2026-07-28` unless the project or host requires another revision. Verify the selected revision against the official specification, then load [protocol-v2.md](references/protocol-v2.md) before implementing wire behavior or making an MCP conformance claim. Classify every behavior explicitly:

- **MCP Core 2026-07-28** — normative core protocol requirement;
- **Official MCP Extension** — optional, negotiated, disabled by default;
- **Custom Application Pattern** — architecture built with ordinary tools, resources, and explicit handles;
- **Deprecated / Legacy** — retained only in an isolated compatibility path;
- **Experimental / Incubating** — only when an official MCP source assigns that status.

Never present a custom pattern as an MCP primitive, or an official extension as core behavior.

## Workflow

1. Define the server's job, users, workflows, external systems, authorization model, and data sensitivity.
2. Load [protocol-v2.md](references/protocol-v2.md). Establish the stateless per-request contract, `server/discover`, result and error layers, transport headers, cache metadata, and supported extensions.
3. Reuse the repository's language and stack. Prefer an official MCP SDK that explicitly supports the selected revision and pin its version. Hand-roll wire or transport behavior only when no adequate SDK exists and the protocol test burden is justified.
4. Choose the smallest useful direct tool/resource surface. Use catalog routing only when the domain surface is large or dynamic.
5. Classify each operation's execution class:
   - short and bounded: synchronous `resultType: "complete"`;
   - needs more client input mid-call: MRTR `resultType: "input_required"`;
   - durable asynchronous work: Tasks extension `resultType: "task"` when negotiated;
   - arbitrary stdin, incremental output, REPL, debugger, or long-lived process: custom explicit-handle interactive lifecycle.
6. Model required cross-call state with explicit server-minted handles. Add workspaces, artifacts, large-output handoff, or lifecycle tools only when the workflow needs them.
7. Load [patterns.md](references/patterns.md) only for the applicable catalog, state, artifact, lifecycle, Apps, or adapter decision.
8. Load [security.md](references/security.md) before exposing file, network, command, credential, UI, destructive, stateful, asynchronous, or external-handle capabilities.
9. Keep MCP transport code thin. Isolate domain APIs, SDKs, subprocesses, storage, and external jobs in testable adapters.
10. Load [testing.md](references/testing.md), test through the real configured transport with an independent MCP-aware client, and verify applicable security, cleanup, compatibility, and publication cases before claiming readiness.

## Default Design Guidance

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
| [patterns.md](references/patterns.md) | Architecture decisions: catalog routing, execution classes, state, artifacts, Apps, adapters |
| [security.md](references/security.md) | Exposing sensitive, stateful, asynchronous, destructive, UI, file, network, command, or credential behavior |
| [testing.md](references/testing.md) | Before claiming implementation readiness or publication quality |

### Scripts

Deterministic helper under [scripts/](scripts/):

| Script | Run when |
|---|---|
| `scripts/check_mcp_conformance.py` | Heuristically scan server source/docs for suspicious `2026-07-28` patterns. Run `python scripts/check_mcp_conformance.py <path> [--strict]` against server code, not this skill's references. Findings require review; a clean scan never proves conformance or readiness. |
