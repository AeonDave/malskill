# Teamserver API for extenders

This reference covers plugin-relevant ports and their ownership semantics. It is intentionally selective. Read the complete interface at the pinned module revision:

```bash
go -C AdaptixServer doc github.com/Adaptix-Framework/axc2/v2.Teamserver
rg -n "func \(.*\) Ts[A-Z]" AdaptixServer/core/server
```

Use the implementation, not only the interface, when success, cancellation, cleanup, or concurrency matters.

## Contents

- [Acquire a narrow port](#acquire-a-narrow-port)
- [Agent creation and data](#agent-creation-and-data)
- [Payload build](#payload-build)
- [Tasks and console output](#tasks-and-console-output)
- [Listener lifecycle](#listener-lifecycle)
- [Service calls and UI delivery](#service-calls-and-ui-delivery)
- [Extender storage](#extender-storage)
- [Endpoints](#endpoints)
- [Event hooks](#event-hooks)
- [Specialized families](#specialized-families)

## Acquire a narrow port

The loader passes `ts` as `any`; check it once in `InitPlugin`. Keep `adaptix.Teamserver` at the outer adapter, then inject small local interfaces into domain components:

```go
type AgentIngress interface {
    TsAgentCreate(agentCRC string, uid, beat []byte, listenerName, externalIP string, async bool) (adaptix.AgentData, error)
    TsAgentProcessData(agentID int64, body []byte) error
}
```

This documents which capabilities a component owns and makes failure paths testable.

## Agent creation and data

```go
TsAgentGenID() int64
TsAgentGetById(agentID int64) (adaptix.AgentData, bool)
TsAgentIsExists(agentID int64) bool
TsAgentIdByUID(uid []byte) (int64, bool)
TsAgentCreate(agentCRC string, uid, beat []byte, listenerName, externalIP string, async bool) (adaptix.AgentData, error)
TsAgentUpdateData(data adaptix.AgentData) error
TsAgentUpdateDataPartial(agentID int64, update any) error
TsAgentProcessData(agentID int64, body []byte) error
TsAgentSetTick(agentID int64, listenerName string) error
TsAgentTerminate(agentID, terminateTaskID int64) error
TsAgentRemove(agentID int64) error
```

`AgentData.Id` is `int64`. Verify UID uniqueness and frame authenticity before creation. For an existing session, resolve the trusted server-side agent and pass only validated protocol data to `TsAgentProcessData`.

Apply the canonical [agent state machine](architecture-and-lifecycle.md#agent) when calling `TsAgentCreate` or restoring persisted sessions.

Hosted task retrieval returns both data and accounting:

```go
TsAgentBuildEmptyTasks(agentID int64) ([]byte, error)
TsAgentGetHostedAll(agentID int64, maxDataSize int) ([]byte, adaptix.StatTasks, error)
TsAgentGetHostedTasks(agentID int64, maxCount, maxDataSize int) ([]byte, adaptix.StatTasks, error)
```

Honor size limits and propagate the returned task statistics according to the transport protocol.

## Payload build

```go
TsAgentBuildSyncOnce(agentName, config string, listeners []string, creator string, saveToStore bool, description string) ([]byte, string, error)
TsAgentBuildCreateChannel(buildData string, ws adaptix.WebSocketConn, creator string) error
TsAgentBuildExecute(builderID, workingDir string, env []string, program string, args ...string) error
TsAgentBuildLog(builderID string, status int, message string) error
TsAgentBuildSendFile(builderID, filename string, content []byte) error
TsAgentBuildClose(builderID string)
```

Inside `PluginAgent.BuildPayload`, use only the execution/logging calls assigned by the canonical [build ownership](architecture-and-lifecycle.md#build-ownership). The other methods above belong to the outer pipeline.

For `TsAgentBuildExecute`, `env == nil` inherits the Teamserver environment. A non-nil slice replaces it; the framework does not merge it with `os.Environ()` for the plugin.

## Tasks and console output

Selected methods:

```go
TsTaskGenID() int64
TsTaskCreate(agentID int64, cmdline, client string, task adaptix.TaskData)
TsTaskUpdate(agentID int64, task adaptix.TaskData)
TsTaskGetAvailableAll(agentID int64, availableSize int) ([]adaptix.TaskData, error)
TsTaskGetAvailableTasks(agentID int64, maxCount, availableSize int) ([]adaptix.TaskData, int, error)
TsTaskCancel(agentID, taskID int64) error
TsTaskSave(task adaptix.TaskData) error

TsAgentConsoleOutput(agentID int64, client string, messageType int, message, clearText string, store bool)
TsAgentConsoleOutputClient(agentID int64, client string, messageType int, message, clearText string)
TsAgentConsoleErrorCommand(agentID int64, client, cmdline, message, hookID, handlerID string)
```

Keep task IDs and agent IDs as `int64`. Do not emit success console output before the protocol confirms the corresponding state transition. Use client-only output only when the result is intentionally private to that operator.

## Listener lifecycle

```go
TsListenerGet(listenerName string) (adaptix.ListenerData, bool)
TsListenerCatalog() (string, error)
TsListenerStart(listenerName, configType, config string, createTime int64, watermark string, customData []byte, tags string) error
TsListenerEdit(listenerName, configType, config, tags string) error
TsListenerStop(listenerName, configType string) error
TsListenerPause(listenerName, configType string) error
TsListenerResume(listenerName, configType string) error
TsListenerGetProfile(listenerName string) (string, []byte, error)
TsListenerInteralHandler(watermark string, data []byte) (int64, error)
TsListenerConnector(listenerName string, data []byte) (int64, error)
```

`TsListenerInteralHandler` is spelled `Interal` in the current public interface. Do not silently correct the symbol in code.

Use the canonical [listener state machine](architecture-and-lifecycle.md#listener) for start-result verification and pause/resume behavior.

Current listener types include internal, external, bind, and cloud. Confirm type-specific routing in the pinned source.

## Service calls and UI delivery

```go
TsServiceLoad(configPath string) error
TsServiceUnload(serviceName string) error
TsPluginServiceCall(serviceName, operator, function, args string)
TsPluginServiceCallWait(serviceName, operator, function, args string, timeoutMs int) (string, error)
TsPluginServiceSendDataAll(serviceName, data string)
TsPluginServiceSendDataClient(operator, serviceName, data string)
```

Use `SendDataClient` for request-specific results. Include the caller-supplied request ID inside the JSON payload; the transport does not correlate it for the plugin.

Apply the [failure contract](architecture-and-lifecycle.md#failure-contract) to wait calls and the [service state machine](architecture-and-lifecycle.md#service) to runtime removal.

Agent/listener auxiliary UI uses parallel calls:

```go
TsPluginAgentSendDataClient(operator string, agentID int64, data string)
TsPluginAgentSendDataAll(agentID int64, data string)
TsPluginListenerSendDataClient(operator, listenerName, data string)
TsPluginListenerSendDataAll(listenerName, data string)
```

## Extender storage

```go
TsExtenderDataSave(extenderName, key string, data []byte) error
TsExtenderDataLoad(extenderName, key string) ([]byte, error)
TsExtenderDataDelete(extenderName, key string) error
TsExtenderDataKeys(extenderName string) ([]string, error)
TsExtenderDataDeleteAll(extenderName string) error
```

Use a compile-time constant extender name. Version values, bound key/value size, and distinguish not-found from corrupt/incompatible data. The caller chooses `extenderName`; it is a namespace, not access control.

## Endpoints

Authenticated routes:

```go
TsEndpointRegister(method, path string, handler func(username string, body []byte) (int, []byte)) error
TsEndpointRegisterRaw(method, path string, handler func(http.ResponseWriter, *http.Request, string)) error
TsEndpointUnregister(method, path string) error
TsEndpointExists(method, path string) bool
```

Public variants are `TsEndpointRegisterPublic`, `TsEndpointRegisterPublicRaw`, `TsEndpointUnregisterPublic`, and `TsEndpointExistsPublic`.

Namespace every path under the extender. Prefer raw handlers when request size, streaming, headers, or cancellation matter; non-raw handlers receive a fully buffered body. Public routes need a real unauthenticated protocol requirement plus plugin-owned authentication/anti-replay where applicable.

The route registry is shared and a later registration can replace an existing handler. Check existence, reject collisions, and unregister only routes owned by the plugin.

## Event hooks

```go
TsEventHookRegister(eventType, name string, phase, priority int, handler func(any) error) string
TsEventHookOnPre(eventType, name string, handler func(any) error) string
TsEventHookOnPost(eventType, name string, handler func(any) error) string
TsEventHookUnregister(hookID string) bool
TsEventHookUnregisterByName(name string) int
```

Verified core event names include `agent.new`, `agent.generate`, `agent.terminate`, `listener.start`, and `listener.stop`. Inspect the exact emitter before using one: pre hooks are generally synchronous and may cancel, while post-hook timing and mutability differ by event. Concrete event structs are Teamserver-internal, not stable public `axc2/v2` types.

Store returned hook IDs and unregister them during teardown. Do not present an assertion against an internal event type as a portable extender pattern.

## Logging and observability

```go
TsLogAdd(status adaptix.LogStatus, level int, source, category, format string, args ...any)
TsLogWriter(status adaptix.LogStatus, source, category string) io.Writer
```

Use stable source/category values. Include operation, request/build/agent/listener ID, elapsed time, and terminal state; exclude passwords, keys, tokens, raw credentials, and payload content.

## Specialized families

The interface also exposes payload-store, transfers, tunnels, terminals, pivots, frames, credentials, targets, GUI listings, chat, and client synchronization. Load only the family required by the extender, then inspect both its declaration and current `ts_*.go` implementation. In particular:

- pair every tunnel/terminal pipe with close/error handling;
- use frame methods as a coordinated state machine, not independent byte helpers;
- preserve transfer accounting and close reason on every path;
- treat credential/target writes as sensitive, explicitly authorized operations.

Do not copy a complete interface snapshot into an extender: it becomes stale and obscures the few capabilities the component should own.
