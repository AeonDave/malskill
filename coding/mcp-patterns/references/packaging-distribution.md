# Packaging and Distribution

Load this file after the manual local workflow already works.

## Recommended order

1. stable local stdio server
2. Inspector and harness checks
3. host integration
4. security review
5. packaging or publishing

Do not begin with packaging. Package the thing that already works.

## Distribution options

### 1. Source + host config

Best for private/internal use or early iteration.

### 2. Python package

Useful when consumers are comfortable installing Python dependencies and launching with the official SDK tooling.

### 3. MCP Bundle (`.mcpb`)

Useful when you want portable, one-click local-server installation across compatible clients.

The MCP Bundle format packages:

- the server
- a `manifest.json`
- dependencies/runtime material
- optional assets such as icons

## MCPB guidance

- treat `.mcpb` as a distribution layer, not the development loop
- keep bundle permissions and configuration minimal
- document what the server can access and why
- validate the unbundled server first

## Release checklist

- baseline server works with stdio
- required env vars are documented clearly
- privilege boundaries are explicit
- no debug prints to stdout
- host config or bundle manifest uses absolute, reviewable launch paths where relevant
- one representative install/run path is tested on the target platform

## Common mistakes

- bundling an unstable server to “solve” debugging problems
- hiding privilege requirements in packaging metadata only
- assuming distribution format fixes poor capability design
- treating registry/public release as the first validation step
