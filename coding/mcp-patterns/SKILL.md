---
name: mcp-patterns
description: "Design and implement local Model Context Protocol (MCP) servers, mainly in Python, using the official SDK and host-integration patterns. Use when building or refactoring MCP servers, choosing between tools/resources/prompts, wiring stdio or local HTTP transports, handling lifecycle and capability negotiation, connecting to Claude Desktop-class hosts, debugging Inspector/client issues, or packaging local servers for reuse and distribution."
license: MIT
compatibility: "Python-focused MCP guidance. Baseline: official Python SDK, local stdio servers, Inspector, and desktop-host integrations."
metadata:
  author: GitHub Copilot
  version: "1.0"
---

# MCP Patterns

Local-first guidance for building MCP servers without turning the protocol surface into a bag of random decorators.

## When to activate

- Building a new local MCP server, mainly in Python
- Refactoring an MCP server that mixed protocol glue with business logic
- Deciding whether a feature should be a tool, resource, prompt, root-aware flow, or sampling-assisted path
- Wiring a server into Claude Desktop or another local MCP host
- Debugging transport, lifecycle, capability, or host-integration issues
- Preparing a local server for packaging or distribution

## Outcome expectations

- The server uses the **official** MCP Python SDK as the default path.
- Protocol choices are explicit: tools vs resources vs prompts, stdio vs local HTTP, baseline vs optional capabilities.
- Local integrations are secure by default: least privilege, absolute paths, no stdout logging on stdio.
- Testing starts with Inspector, then a local client harness, then the target host.
- Packaging happens only after the manual local workflow is already stable.

## Core patterns

- Prefer the official `mcp` Python SDK and explicit imports such as `from mcp.server.fastmcp import FastMCP`.
- Keep **business logic** separate from **MCP wrappers**. The protocol layer should mostly validate inputs, call helpers, and shape outputs.
- Start with **stdio** unless you have a concrete reason to run a local HTTP service.
- Use **tools** for actions and parameterized computation, **resources** for read-only context, and **prompts** for reusable user-invoked workflows.
- Treat **roots** and **sampling** as optional, capability-gated features. Do not make a basic local server depend on them.
- For stdio servers, never write logs to stdout.
- Optimize for agent cognition: search/filter over dump-all, concise outputs first, rich details on demand.
- Pair with `python-patterns` for broader Python code quality, and with `systematic-debugging` when the failure source is unclear.

## Recommended workflow

1. Load [references/architecture.md](references/architecture.md) to lock in the host/client/server mental model.
2. Load [references/python-local-servers.md](references/python-local-servers.md) for the official Python baseline and project skeleton.
3. Load the specific capability reference you need:
   - [references/tools.md](references/tools.md)
   - [references/resources.md](references/resources.md)
   - [references/prompts.md](references/prompts.md)
4. Load [references/lifecycle-capabilities.md](references/lifecycle-capabilities.md) and [references/transports.md](references/transports.md) when wiring or debugging protocol behavior.
5. Load [references/local-host-integration.md](references/local-host-integration.md) before connecting the server to Claude Desktop or a similar host.
6. Load [references/debugging-testing.md](references/debugging-testing.md) before guessing at failures.
7. Load [references/security-boundaries.md](references/security-boundaries.md) before exposing broader local access, switching to HTTP, or preparing distribution.
8. Load [references/packaging-distribution.md](references/packaging-distribution.md) only after the server works locally.
9. Load [references/server-instructions.md](references/server-instructions.md) only if the server has cross-tool workflows that tool descriptions alone do not communicate well.

## Reference map

| Topic | File | Load when |
|---|---|---|
| Roles and control model | [references/architecture.md](references/architecture.md) | You need the host/client/server mental model or primitive-selection rules |
| Python baseline | [references/python-local-servers.md](references/python-local-servers.md) | You are creating the project, server skeleton, or local client harness |
| Lifecycle and capabilities | [references/lifecycle-capabilities.md](references/lifecycle-capabilities.md) | `initialize`, capability negotiation, notifications, errors, cancellation |
| Transports | [references/transports.md](references/transports.md) | Choosing stdio vs local HTTP or debugging transport-specific failures |
| Tools | [references/tools.md](references/tools.md) | Designing callable capabilities, schemas, outputs, and tool errors |
| Resources | [references/resources.md](references/resources.md) | Designing read-only context, URI templates, MIME types, annotations |
| Prompts | [references/prompts.md](references/prompts.md) | Building reusable prompt templates or prompt-returning workflows |
| Roots | [references/roots.md](references/roots.md) | Consuming client-provided workspace or path scope safely |
| Sampling | [references/sampling.md](references/sampling.md) | Considering server-initiated model calls or sampling callbacks |
| Host wiring | [references/local-host-integration.md](references/local-host-integration.md) | Registering and launching the server from a desktop host |
| Debugging and tests | [references/debugging-testing.md](references/debugging-testing.md) | Inspector, logs, local harnesses, capability mismatch diagnosis |
| Security | [references/security-boundaries.md](references/security-boundaries.md) | Least privilege, local-server compromise, auth/session pitfalls |
| Packaging | [references/packaging-distribution.md](references/packaging-distribution.md) | Moving from local dev to portable distribution |
| Server instructions | [references/server-instructions.md](references/server-instructions.md) | Adding concise workflow guidance beyond tool descriptions |

## Resources

Load the minimum reference file that matches the current task. Keep `SKILL.md` as the navigation layer; keep the heavy detail in `references/`.
