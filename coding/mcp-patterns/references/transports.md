# Transports

Load this file when choosing between stdio and local HTTP, or when transport behavior is the bug.

## Default choice

For a local Python server, start with **stdio**.

Why:

- simplest development path
- natural fit for desktop hosts
- lower local exposure surface
- no extra service lifecycle to manage

## Transport comparison

| Transport | Good default for | Watch out for |
|---|---|---|
| stdio | desktop-host local servers, quick iteration, one host launching one child process | stdout is reserved for protocol traffic; environment/working directory surprises |
| local HTTP / Streamable HTTP | service-style local daemons, browser-adjacent tools, multi-process consumers | session management, loopback security, auth, extra operational complexity |

## Stdio rules

- Never log to stdout.
- Log to stderr or a structured sink.
- Assume the client may launch the server from an unexpected working directory.
- Use absolute paths in config and `.env` references.
- Pass explicit environment variables when needed instead of assuming the shell environment.

## Local HTTP rules

- Bind to loopback unless you intentionally need broader reach.
- Require authentication if other local processes should not call the server.
- Treat session IDs as protocol state, not authentication.
- Plan for request/response tracing, headers, and session cleanup.

## HTTP-specific concepts worth remembering

- `MCP-Session-Id` matters for stateful flows.
- `MCP-Protocol-Version` matters for version-aware communication.
- Redirects, origin validation, and localhost binding become security-relevant much faster than on stdio.

## Choosing custom transports

Only go beyond the built-in paths when you have a concrete requirement. If you do, plan for:

- framing
- backpressure
- cancellation
- reconnect behavior
- cleanup on shutdown

## Decision checklist

Choose **stdio** if:

- one host launches the server
- the server is local-only
- you want the simplest debugging path

Choose **local HTTP** if:

- the server must outlive one host process
- multiple consumers need access
- browser or service-style integration is a real requirement

If the reason is only “it sounds more scalable,” stay on stdio until reality objects.
