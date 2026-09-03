---
name: adaptixc2-dev
description: "Build, review, debug, package, and activate AdaptixC2 v2 extenders and AxScript UI: agent payload builders, listeners, services, plugin calls, lifecycle, axtool specs, source-contract checks, and verification. Use for authorized extension development, not live C2 operation."
license: MIT
metadata:
  author: AeonDave
  version: "2.1"
---

# AdaptixC2 v2 Extender Development

Develop against the checked-out source, not remembered v1 APIs or the public GitBook. Adaptix v2 is pre-release: pin the exact source revision and re-run the contract gate for every new task.

Verified baseline for this guidance: AdaptixC2 commit `72f20075` on `testing-v2.0`, `github.com/Adaptix-Framework/axc2/v2` v2.0.13, Go 1.26.5.

## Start with the contract gate

From `<adaptix-root>`:

```bash
git status --short --branch
git rev-parse HEAD
go -C AdaptixServer list -m github.com/Adaptix-Framework/axc2/v2
go -C AdaptixServer env GOVERSION
go -C AdaptixServer doc github.com/Adaptix-Framework/axc2/v2.PluginAgent
go -C AdaptixServer doc github.com/Adaptix-Framework/axc2/v2.PluginListener
go -C AdaptixServer doc github.com/Adaptix-Framework/axc2/v2.PluginService
```

Then inspect the implementation that owns the behavior being changed:

```bash
rg -n "InitPlugin|plugin.Open|LoadPlugin" AdaptixServer
rg -n "GenerateUI|ListenerUI|InitService|data_handler" AdaptixClient AdaptixServer
rg -n "TsAgentBuild|BuildPayload|GenerateProfiles" AdaptixServer
rg -n "plugin_service_(command|wait)|plugin_(agent|listener)_command" AdaptixClient AdaptixServer
```

If the revision or module version differs from the baseline, treat every signature and lifecycle statement below as a hypothesis until re-verified.

## Choose one extender boundary

| Extender | Owns | Does not own |
|---|---|---|
| Agent | payload configuration/build, task encoding, beat processing, restored session behavior | client transport, build-channel close, final artifact delivery |
| Listener | transport instance lifecycle and inbound agent traffic | agent protocol semantics beyond delegation to its agent plugin |
| Service | auxiliary server behavior, optional dock/dialog UI, service messages and bounded RPC | core agent/listener lifecycle or implicit authorization |

Keep the dependency direction one-way:

```text
AxScript UI -> named bridge call -> plugin boundary -> domain logic -> explicit Teamserver port
```

Do not let UI JSON, listener configuration, task arguments, or callback bytes select filesystem paths, programs, routes, or storage namespaces without validation. Keep Adaptix types at the boundary and ordinary Go types in domain code.

For boundary ownership, lifecycle state machines, failure semantics, and concurrency, load [architecture-and-lifecycle.md](references/architecture-and-lifecycle.md).

## Route to the narrowest reference

| Task | Load when |
|---|---|
| [plugin-patterns.md](references/plugin-patterns.md) | Implementing Go interfaces, agent restore/build, listener start/stop, service calls, or safe boundary adapters |
| [axscript-patterns.md](references/axscript-patterns.md) | Building payload forms, listener forms, service docks/dialogs, event handlers, or UI-to-plugin interactions |
| [axscript-api.md](references/axscript-api.md) | Checking an exact client bridge method, argument order, return shape, or server stub parity |
| [teamserver-api.md](references/teamserver-api.md) | Selecting Teamserver calls and checking ownership, errors, hooks, endpoints, storage, or messaging semantics |
| [generator-details.md](references/generator-details.md) | Creating templates/specs, building, installing, activating, or auditing `axtool` behavior |

Load the parent first, then only the references required by the current subtask.

## Implement a thin vertical slice

1. Define the user-visible outcome and the failure state before coding.
2. Record the exact Adaptix revision, axc2 module version, Go toolchain, build flags, and shared dependency versions.
3. Isolate protocol/build/service logic from `Plugin*`, `Teamserver`, and AxScript adapters.
4. Implement one end-to-end path: UI input -> validation -> plugin call -> result/error -> observable UI state.
5. Add lifecycle cleanup and concurrency bounds before adding more commands.
6. Verify activation from server logs and runtime catalogs; process readiness alone does not prove the extender loaded.

Use explicit schemas at every JSON boundary. Reject unknown operations, missing required fields, oversized inputs, invalid enum values, unsafe paths, and malformed byte frames. Return errors with operation context; never turn an unknown command into a successful zero value.

## Non-negotiable runtime rules

- Agent and service `.axs` files are evaluated by server-side Goja for command metadata and by the Qt client for real UI behavior; listener `.axs` is client-only on the verified baseline. Keep top-level code declarative and place UI effects in `GenerateUI`, `ListenerUI`, or `InitService`.
- Agent state must be reconstructible by `AgentRestore`. The current server does not retain the callbacks returned by `CreateAgent` when creating a session.
- `BuildPayload` returns artifact bytes and a filename to its caller. The WebSocket path sends/closes the build channel; the synchronous path returns the artifact directly.
- Listener `Start` can fail while the API call still completes with a stopped instance. Make `Start` restart-safe, `Stop` idempotent, and verify runtime status.
- Plugin instances are shared. Assume `Call`, `CallRPC`, task handlers, hooks, and build callbacks can overlap.
- A service RPC timeout does not cancel plugin work. Bound work independently and correlate asynchronous replies with a request ID.
- Go plugins cannot be safely unloaded from the process. Registry removal is not resource teardown; design cleanup before supporting runtime unload.
- Treat extender binaries and `axtool` specs as trusted code. Do not run unreviewed packages or mutable build inputs.

### Wrong-type traps (axc2/v2 v2.0.13)

Verified against `axc2/v2@v2.0.13/adaptix_struct.go`. Common misuses that compile but corrupt runtime state:

| Field / constant | Real type | Trap |
|---|---|---|
| `AgentData.Sleep`, `AgentData.Jitter` | `uint` (seconds) | Do not parse from a duration string in-plugin; convert once at the boundary. |
| `AgentData.Pid`, `AgentData.Tid` | `string` | Format from numeric sources with `fmt.Sprintf("%v", ...)`; do not cast. |
| `AgentData.Id` and every `agentId` on `Teamserver`/`Call`/`InternalHandler` | `int64` | Never a string. In JavaScript treat it as opaque string when it may exceed `Number.MAX_SAFE_INTEGER`. |
| `OS_MAC` (constant `3`) | `int` | No `OS_MACOS` symbol exists. |
| `PluginService` | interface with `Call` **and** `CallRPC` | An implementation with only `Call` will not satisfy the loader type assertion. |
| `config.yaml` -> `extender_file` | filename string | Must equal the Makefile `.so` output byte-for-byte; a mismatch loads nothing and the server log is the only signal. |

## Verification gates

Run focused tests for pure domain code, then compile with the exact Teamserver toolchain and dependency graph. At minimum, exercise:

- valid and malformed boundary input;
- short/truncated frames before indexing or slicing;
- concurrent builds/calls under the race detector where supported;
- create/start -> pause -> resume -> full stop for listeners, plus partial-start failure cleanup;
- create and restored-session behavior for agents;
- success, plugin error, timeout, late result, and disconnect for service UI;
- build failure cleanup and absence of duplicate artifact delivery;
- cold-start activation and runtime catalog/UI visibility.

Before claiming completion:

```bash
go test ./...
go test -race ./...
go vet ./...
rg -n "panic\(|log\.Fatal|os\.Exit" .
```

Use the race gate for Go/domain packages on a supported native target; it does not prove races across the host/plugin boundary. Also inspect the built `.so`, server profile entry, load logs, command catalogs, and the intended UI in a real client. Report skipped gates and upstream source failures separately from extender failures.

Baseline limitation: commit `72f20075` contains no Go test files, so its `go test` runs are compile gates only; `beacon_listener_dns` currently fails that gate at `pl_transport.go:375` (`undefined: total`). Recheck both facts on a newer revision before attributing the failure to an extender change.

## Delivery record

Record:

- pinned Adaptix revision, axc2 version, Go version, build flags, and target OS/architecture;
- extender type, init signature, owned resources, cleanup path, and concurrency policy;
- AxScript entry points and bridge calls used;
- package/spec provenance and activation path;
- tests run, runtime evidence, known source limitations, and rollback/restart procedure.

Do not claim transactional install, safe hot reload, automatic timeout cancellation, or UI delivery without direct evidence from the pinned source and a runtime check.
