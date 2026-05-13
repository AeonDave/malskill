# Lifecycle and Capability Negotiation

Load this file when debugging initialization, notifications, or optional features.

## Session lifecycle

The baseline flow is:

1. client opens transport
2. client sends `initialize`
3. server returns version + capabilities + server info
4. client sends `initialized`
5. normal requests and notifications begin

Do not send capability-dependent behavior before initialization finishes.

## Capability negotiation

Treat capabilities as a contract.

- The **server** declares what it offers.
- The **client** declares what it supports.
- Each side must avoid calling into features the other side never announced.

Examples:

- do not send sampling requests if the client did not declare sampling
- do not assume roots support exists just because the server could use it
- do not emit logging flows that the client cannot interpret unless you also log elsewhere

## Server-side implications

- Keep the base server useful without optional capabilities.
- Branch cleanly when a capability is present vs absent.
- Prefer explicit “feature not available on this host” behavior over magical fallback guesses.

## Notifications

Use notifications when the host needs to know that discoverable state changed.

Typical cases:

- `tools/list_changed`
- `resources/list_changed`
- resource update notifications when subscriptions matter
- log message notifications for observability

Only emit them when they communicate real state changes.

## Errors: protocol vs execution

Separate two kinds of failure:

- **Protocol errors**: invalid method, invalid params, lifecycle misuse, transport failures
- **Execution errors**: the tool ran correctly but the business task failed or produced a recoverable problem

Use `isError`-style execution results for recoverable tool-level failures the model can react to. Use protocol errors when the request itself is invalid or the session is broken.

## Cancellation and timeouts

- Long-running tools should expect cancellation.
- Timeouts should be explicit in helper code and host/client expectations.
- Partial progress belongs in logs or notifications, not in blocking silence.

## Versioning mindset

- Negotiate the protocol version during `initialize`.
- Fail clearly on unsupported versions.
- Avoid silent behavior changes across versions or capability sets.

## Common mistakes

- Sending optional client requests before verifying support
- Treating `-32602` as “random host weirdness” instead of a params/capability issue
- Changing discoverable server behavior without notifications
- Hiding lifecycle bugs behind blanket exception handlers
