# MCP Architecture for Local Servers

Load this file when the main question is **what belongs where**.

## Core mental model

- **Host**: the application the user interacts with. It owns trust, UX, approvals, and client policy.
- **Client**: the host-side protocol connection to a specific server.
- **Server**: the capability provider. It exposes tools, resources, prompts, and optional features.

For local work, the host should be treated as the **security broker**. The server provides capabilities; the host decides how those capabilities are surfaced and approved.

## Control hierarchy

- **Prompts** are primarily **user-controlled** workflow templates.
- **Resources** are primarily **application-controlled** read-only context.
- **Tools** are primarily **model-controlled** callable actions.
- **Roots** are **client-provided** scope hints.
- **Sampling** is **client-owned** model invocation requested by the server only when supported.

When in doubt, preserve this hierarchy instead of collapsing everything into tools.

## Local-first server shape

Prefer this split:

1. **Core logic** — plain Python helpers or service objects
2. **MCP surface** — decorators, schemas, URI templates, prompt wrappers
3. **Host config** — Claude Desktop or other client registration files

The protocol layer should stay thin. If a decorator body contains business logic, retries, caching, filesystem traversal, and response formatting all at once, the design is drifting.

## Primitive selection guide

| Need | Primitive |
|---|---|
| Trigger an action, run a query with parameters, or perform side effects | Tool |
| Expose stable read-only data addressed by URI | Resource |
| Offer a reusable user-invoked workflow template | Prompt |
| Narrow filesystem/workspace scope supplied by the client | Roots |
| Ask the client to perform a model call on the server’s behalf | Sampling |
| Communicate cross-tool workflow guidance | Server instructions |

## Thin-server patterns

- Let helpers do domain work; let MCP wrappers do validation and shaping.
- Normalize external data before returning it to the model.
- Prefer one clearly named server over many tiny servers until you actually need process isolation.
- Keep host-specific configuration out of protocol handlers.

## Common architecture mistakes

- Treating the server as the UX layer instead of the capability layer
- Encoding approval logic inside the server instead of respecting host mediation
- Turning every API endpoint into a tool without a task-oriented abstraction
- Using resources for mutable operations or tools for stable read-only context
- Assuming optional client capabilities like sampling or roots always exist

## Local-default recommendation

For most Python projects:

1. Start with one stdio server.
2. Expose only the minimum useful tools/resources/prompts.
3. Test in Inspector.
4. Register with the host.
5. Add optional capabilities only after the baseline works.
