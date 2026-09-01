# Architecture and lifecycle

Load this reference before changing a boundary, lifecycle, concurrency model, or failure contract.

## Contents

- [Runtime map](#runtime-map)
- [Boundary contracts](#boundary-contracts)
- [State machines](#state-machines)
- [Build ownership](#build-ownership)
- [Failure contract](#failure-contract)
- [Concurrency and capacity](#concurrency-and-capacity)
- [Security boundaries](#security-boundaries)
- [Review record](#review-record)

## Runtime map

```text
agent/service .axs -- command metadata -----------------> Teamserver Goja
        |
        +-- GenerateUI / InitService --------------------> Qt QJSEngine
listener .axs -- ListenerUI -----------------------------> Qt QJSEngine
                                                              |
                                                              v
                                                        bridge method
                                                              |
                                                              v
Client <==== WebSocket / HTTP ==== Teamserver registry ==== Go plugin
                                      |                        |
                                      +-- build/lifecycle -----+-- domain logic
                                      +-- event hooks          +-- owned resources
```

Agent and service scripts share source text across the two JavaScript runtimes, not capabilities. Server Goja extracts command/service metadata and exposes stubs for client-only APIs; listener scripts are client-only on the verified baseline. The client executes real form, menu, event, and bridge calls. Keep top-level registration declarative and place UI/network/file effects inside the appropriate client lifecycle function.

## Boundary contracts

Keep four layers explicit:

1. **AxScript adapter** — gathers UI values, displays state, calls a named bridge method.
2. **Adaptix adapter** — implements `PluginAgent`, `PluginListener`, or `PluginService`; validates framework values and translates errors.
3. **Domain component** — owns build, protocol, transport, or service behavior without global Teamserver state.
4. **Infrastructure port** — narrow wrapper around the Teamserver methods actually required.

Prefer a small local interface over passing `adaptix.Teamserver` through the entire plugin:

```go
type BuildReporter interface {
    TsAgentBuildLog(builderID string, status int, message string) error
}

type ArtifactBuilder struct {
    report BuildReporter
}
```

This makes ownership testable and prevents unrelated Teamserver capabilities from becoming accidental dependencies.

## State machines

### Agent

```text
new data -> CreateAgent -> persisted agent -> AgentRestore -> active callbacks
persisted data on boot ---------------------> AgentRestore -> active callbacks
```

On the verified baseline, callbacks returned by `CreateAgent` are not retained by the creation path; `AgentRestore` supplies the active callbacks. Return valid callbacks from both methods for contract compatibility, but reconstruct all required state from `AgentData` and persisted custom data in `AgentRestore`.

Define behavior for missing or incompatible restored data. `AgentRestore` has no error return: log the incompatibility immediately and return a complete set of callbacks that reject work with the same contextual error; never return silent partial/nil behavior. Treat an agent ID as `int64` in Go and as an opaque string in JavaScript when it may exceed JavaScript's safe-integer range.

### Listener

```text
Create -> registered/stopped -> Start -> running
                              | failure
                              v
                         registered/stopped

running -> Pause (calls Stop) -> paused/retained -> Resume (calls Start) -> running
running -> full Stop (calls Stop) -> removed; a new Create is required
```

The Teamserver registers the listener instance before `Start`. A start error is logged and the instance remains stopped; the outer operation can still appear successful. Expose a meaningful stopped/error state and verify the catalog after activation.

`Start` must tolerate a previous partial start and a later resume. The plugin's `Stop` method serves both pause and full removal, so it must be idempotent and leave the instance restartable until the framework removes it. Pair every listener, goroutine, timer, route, file, and channel with one explicit owner and cleanup action.

### Service

```text
load -> register -> calls/hooks/routes running -> registry unload
                                                != process unload
```

Go's plugin runtime does not close an opened plugin. Removing a service from a registry does not stop plugin-owned goroutines, hooks, endpoints, or other resources. If runtime removal is required, expose and invoke an idempotent plugin-owned teardown before registry removal; otherwise require a Teamserver restart.

## Build ownership

Both build paths call the same plugin-owned core:

```text
listener profiles -> GenerateProfiles -> BuildPayload -> artifact bytes/name
```

The callers differ:

```text
synchronous HTTP: optional payload store -> return artifact
WebSocket builder: open channel -> pre hook -> core -> post hook
                   -> optional payload store -> send artifact -> close channel
```

The agent plugin owns only profile generation and artifact production. It must not deliver the final file or close a channel. Build into a unique per-request directory and remove it with `defer`; never mutate a shared source tree or fixed output filename. Hooks currently apply to the WebSocket path, not `TsAgentBuildSyncOnce`.

`TsAgentBuildExecute` inherits the process environment when `env == nil`; a non-nil slice replaces the complete environment. If a controlled environment is required, construct the full allowlisted environment deliberately.

## Failure contract

For each operation define:

| Concern | Required decision |
|---|---|
| Input | schema, maximum size, enum/path allowlist |
| Success | returned value and visible UI/catalog state |
| Failure | typed/plugin error and operator-visible message |
| Timeout | caller deadline and whether work is cancelled |
| Retry | safe, unsafe, or idempotency-key protected |
| Cleanup | owner and observable completion |

Do not equate transport acknowledgement with completed work. In particular:

- asynchronous service calls discard the immediate plugin result and need a correlated callback;
- synchronous service wait returns an envelope and its timeout does not cancel plugin work;
- listener start errors may surface only through logs/status;
- a running Teamserver may have skipped a failed extender and continued startup.

## Concurrency and capacity

Assume one plugin instance serves many users and agents concurrently. Protect mutable maps, avoid package globals, and place bounds on queues, goroutines, build processes, request bodies, and retained results. Include `request_id`, operator, operation, and extender name in structured diagnostics without logging secrets.

Late results need a policy: discard after deadline, cache for explicit retrieval, or deliver as an asynchronous event. Never allow an expired synchronous request to create an unbounded orphan job.

## Security boundaries

- Treat AxScript JSON, task arguments, callback frames, listener configuration, uploaded files, and package specs as untrusted input.
- Check byte lengths before indexing, slicing, decoding, or allocating.
- Use a constant storage namespace; `extenderName` is routing input, not an authorization boundary.
- Namespace dynamic routes. Prefer raw handlers with explicit body limits and authentication; later registrations can otherwise replace a route.
- Authorize sensitive service operations explicitly even when the caller has a valid framework session.
- Keep server-only secrets out of generated agent profiles. Minimize required bootstrap/keying material, treat the resulting profile as sensitive, and keep all secrets out of command output, build logs, and install-state provenance.

## Review record

For a material change, record a short decision:

```text
Context: source revision, user-visible outcome, failure being avoided
Decision: boundary owner, state transition, concurrency and cleanup policy
Alternatives: only credible options considered
Consequences: operational limit, verification evidence, rollback/restart need
```

Reject designs whose success cannot be observed independently of the request that initiated them.
