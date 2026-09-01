# Teamserver API Reference

Complete method signatures for the `Teamserver` interface (`axc2/v2 v2.0.13`).
Type-assert from `ts any` in `InitPlugin`: `Ts = ts.(adaptix.Teamserver)`.

---

## Table of Contents
1. [Agent Methods](#agent-methods)
2. [Build Methods](#build-methods)
3. [Task Methods](#task-methods)
4. [Transfer Methods](#transfer-methods)
5. [Tunnel Methods](#tunnel-methods)
6. [Terminal Methods](#terminal-methods)
7. [Pivot Methods](#pivot-methods)
8. [Plugin-to-Plugin Communication](#plugin-to-plugin-communication)
9. [Event Hook Methods](#event-hook-methods)
10. [Custom HTTP Endpoints](#custom-http-endpoints)
11. [Extender Persistent Storage](#extender-persistent-storage)
12. [Credentials & Targets](#credentials--targets)
13. [Logging](#logging)
14. [Frame / Reassembly](#frame--reassembly-chunked-protocols)
15. [Data Types](#data-types)

---

## Agent Methods

```go
TsAgentGenID() int64

// agentUid = raw UID bytes from implant; agentCrc = sha256(watermarkHex)[:8]
TsAgentCreate(agentCrc string, agentUid []byte, beat []byte, listenerName string, ExternalIP string, Async bool) (AgentData, error)
TsAgentGetById(agentId int64) (AgentData, bool)
TsAgentIdByUID(uid []byte) (int64, bool)
TsAgentIsExists(agentId int64) bool
TsAgentUpdateData(newAgentData AgentData) error
TsAgentUpdateDataPartial(agentId int64, updateData interface{}) error
TsAgentSetTick(agentId int64, listenerName string) error
TsAgentTerminate(agentId int64, terminateTaskId int64) error
TsAgentRemove(agentId int64) error
TsAgentProcessData(agentId int64, bodyData []byte) error
// Returns packed bytes, task stats, and error — always capture all three
TsAgentGetHostedAll(agentId int64, maxDataSize int) ([]byte, StatTasks, error)
TsAgentGetHostedTasks(agentId int64, maxCount int, maxDataSize int) ([]byte, StatTasks, error)
TsAgentBuildEmptyTasks(agentId int64) ([]byte, error)
TsAgentEncryptData(agentId int64, data []byte) ([]byte, error)
TsAgentDecryptData(agentId int64, data []byte) ([]byte, error)
TsAgentCommandGroupSet(agentId int64, groupId string, enabled bool) error
TsAgentCommandGroupList(agentId int64) ([]map[string]interface{}, error)
TsAgentCommand(agentName string, agentId int64, clientName string, hookId string, handlerId string, cmdline string, ui bool, args map[string]any) error
TsAgentConsoleOutput(agentId int64, client string, messageType int, message string, clearText string, store bool)
TsAgentConsoleOutputClient(agentId int64, client string, messageType int, message string, clearText string)
TsAgentConsoleErrorCommand(agentId int64, client string, cmdline string, message string, HookId string, HandlerId string)
TsAgentConsoleLocalCommand(agentId int64, client string, cmdline string, message string, text string)
```

---

## Build Methods

```go
TsAgentBuildCreateChannel(buildData string, wsconn WebSocketConn, creator string) error
// env: extra KEY=VALUE pairs merged with os.Environ(); pass nil for default env
TsAgentBuildExecute(builderId string, workingDir string, env []string, program string, args ...string) error
// status: BUILD_LOG_NONE=0 INFO=1 ERROR=2 SUCCESS=3
TsAgentBuildLog(builderId string, status int, message string) error
TsAgentBuildSendFile(builderId string, filename string, content []byte) error
TsAgentBuildClose(builderId string)  // always call; even on error
TsAgentBuildSyncOnce(agentName string, config string, listenersName []string, creator string, saveToStore bool, description string) ([]byte, string, error)
```

---

## Task Methods

```go
TsTaskGenID() int64
TsTaskCreate(agentId int64, cmdline string, client string, taskData TaskData)
TsTaskUpdate(agentId int64, data TaskData)
TsTaskGetAvailableAll(agentId int64, availableSize int) ([]TaskData, error)
TsTaskCancel(agentId int64, taskId int64) error
TsTaskDelete(agentId int64, taskId int64) error
TsTaskRunningExists(agentId int64, taskId int64) bool
```

---

## Transfer Methods

### Downloads (agent → server)

```go
TsFileGenID() int64
// fileSize int64; fileId from TsFileGenID()
TsDownloadAdd(AgentId int64, fileId int64, fileName string, fileSize int64) error
// state: TRANSFER_STATE_RUNNING=1 STOPPED=2 FINISHED=3 CANCELED=4
TsDownloadUpdate(fileId int64, state int, data []byte) error
TsDownloadClose(fileId int64, reason int) error    // reason = state constant
TsDownloadSave(AgentId int64, fileId int64, filename string, content []byte) error
TsDownloadDelete(fileId []int64) error
```

### Uploads (server → agent)

```go
TsUploadAdd(agentId int64, fileId int64, localPath string, remotePath string) error
// kind: TRANSFER_KIND_FILE=0 MEMORY=1
TsUploadAddContent(agentId int64, fileId int64, remotePath string, content []byte, canceled bool, kind int, artname string, arttype string) error
TsUploadGetChunk(fileId int64, chunkSize int, needApprove bool) ([]byte, error)
TsUploadApprove(fileId int64, approvedBytes int) error
TsUploadClose(fileId int64, reason int) error
```

---

## Tunnel Methods

```go
TsTunnelCreateSocks4(AgentId int64, Info string, Lhost string, Lport int) (int64, error)
TsTunnelCreateSocks5(AgentId int64, Info string, Lhost string, Lport int, UseAuth bool, Username string, Password string) (int64, error)
TsTunnelCreateLportfwd(AgentId int64, Info string, Lhost string, Lport int, Thost string, Tport int) (int64, error)
TsTunnelCreateRportfwd(AgentId int64, Info string, Lport int, Thost string, Tport int) (int64, error)
TsTunnelStart(TunnelId int64) (int64, error)
TsTunnelDeactivate(TunnelId int64, clientName string) error
TsTunnelStop(TunnelId int64) error
TsTunnelGetPipe(AgentId int64, channelId int64) (*io.PipeReader, *io.PipeWriter, error)
TsTunnelConnectionData(channelId int64, data []byte)
TsTunnelConnectionClose(channelId int64, writeOnly bool)
TsTunnelConnectionHalt(channelId int64, errorCode byte)   // SOCKS5_* error constants
TsTunnelConnectionResume(AgentId int64, channelId int64, ioDirect bool)
TsTunnelConnectionAccept(tunnelId int64, channelId int64)
TsTunnelConnectionBindReply(channelId int64, phase int, atyp int, addr []byte, port int)
TsTunnelChannelExists(channelId int64) bool
TsTunnelPause(channelId int64)
TsTunnelResume(channelId int64)
TsTunnelStopSocks(AgentId int64, Port int)
TsTunnelStopLportfwd(AgentId int64, Port int)
TsTunnelStopRportfwd(AgentId int64, Port int)
```

---

## Terminal Methods

```go
TsTerminalGetPipe(AgentId int64, terminalId int64) (*io.PipeReader, *io.PipeWriter, error)
TsTerminalConnResume(AgentId int64, terminalId int64, ioDirect bool)
TsTerminalConnExists(terminalId int64) bool
TsTerminalConnData(terminalId int64, data []byte)
TsTerminalConnClose(terminalId int64, status string) error
TsAgentTerminalCreateChannel(terminalData string, wsconn WebSocketConn) error
TsAgentTerminalCloseChannel(terminalId int64, status string) error
```

---

## Pivot Methods

```go
TsPivotCreate(pivotId string, pAgentId int64, chAgentId int64, pivotName string, isRestore bool) error
TsGetPivotInfoByName(pivotName string) (pivotId string, parentId int64, childId int64)
TsGetPivotInfoById(pivotId string) (pivotId string, parentId int64, childId int64)
TsPivotDelete(pivotId string) error
```

---

## Plugin-to-Plugin Communication

```go
// Service: fire-and-forget
TsPluginServiceSendDataClient(operator string, service string, data string)
TsPluginServiceSendDataAll(service string, data string)
// Service: sync RPC (blocks up to timeoutMs)
TsPluginServiceCallWait(serviceName, operator, function, args string, timeoutMs int) (string, error)

// Agent → agent plugin Call()
TsPluginAgentCall(agentId int64, operator string, function string, args string)
TsPluginAgentSendDataAll(agentId int64, data string)
TsPluginAgentSendDataClient(operator string, agentId int64, data string)

// Listener plugin Call()
TsPluginListenerCall(listenerName string, operator string, function string, args string)
TsPluginListenerSendDataAll(listenerName string, data string)
TsPluginListenerSendDataClient(operator string, listenerName string, data string)
```

> v1 names `TsServiceSendDataClient/All` do not exist in v2; use `TsPluginServiceSendDataClient/All`.

---

## Event Hook Methods

```go
// phase: 0=pre, 1=post; lower priority = earlier. Returns hookID string (not error)
TsEventHookRegister(eventType string, name string, phase int, priority int, handler func(event any) error) string
TsEventHookOnPre(eventType string, name string, handler func(event any) error) string
TsEventHookOnPost(eventType string, name string, handler func(event any) error) string
TsEventHookUnregister(hookID string) bool
TsEventHookUnregisterByName(name string) int
TsEventHookSetEnabled(hookID string, enabled bool) error
TsEventEmit(eventType string, text string) error
TsEventEmitFrom(eventType string, source string, text string) error
```

### Common event types

| Event | Phase | Notes |
|-------|-------|-------|
| `agent.create` | post | AgentData available |
| `agent.generate` | pre/post | BuildProfile + payload; pre can rewrite |
| `agent.terminate` | pre | |
| `listener.create` | post | ListenerData available |
| `listener.start` | post | |
| `listener.stop` | pre | |

---

## Custom HTTP Endpoints

```go
// Authenticated (requires valid session)
TsEndpointRegister(method, path string, handler func(username string, body []byte) (int, []byte)) error
TsEndpointUnregister(method, path string) error
// Public (no auth)
TsEndpointRegisterPublic(method, path string, handler func(body []byte) (int, []byte)) error
TsEndpointUnregisterPublic(method, path string) error
```

---

## Extender Persistent Storage

```go
// Scoped to extenderName; survives server restart
TsExtenderDataSave(extenderName, key string, data []byte) error
TsExtenderDataLoad(extenderName, key string) ([]byte, error)
TsExtenderDataDelete(extenderName, key string) error
TsExtenderDataKeys(extenderName string) ([]string, error)
TsExtenderDataDeleteAll(extenderName string) error
```

---

## Credentials & Targets

```go
TsCredGenID() int64
TsCredentilsAdd(creds []map[string]interface{}) error
TsCredentilsEdit(credId int64, username, password, realm, credType, tag, storage, host string) error
TsCredentilsDelete(credsId []int64) error

TsTargetGenID() int64
TsTargetsAdd(targets []map[string]interface{}) error
TsTargetsCreateAlive(agentData AgentData) (int64, error)
TsTargetsEdit(targetId int64, computer, domain, address string, os int, osDesk, tag, info string, alive bool) error
TsTargetDelete(targetsId []int64) error
```

---

## Logging

```go
// status: LogStatusDebug=0 Info=1 Success=2 Warn=3 Error=4
TsLogAdd(status LogStatus, level int, source, category string, format string, args ...any)
TsLogWriter(status LogStatus, source, category string) io.Writer
```

---

## Frame / Reassembly (Chunked Protocols)

For HTTP/DNS transports that split large payloads into chunks:

```go
TsFrameHasPending(sessionId int64) bool
// Returns: assembled bool, totalSize, chunkCount, nextIndex, assembled []byte
TsFramePut(sessionId int64, index uint32, data []byte, totalSize uint32, chunkCount uint16) (bool, uint32, uint32, uint32, []byte)
TsFramePutDecoded(..., decode func([]byte) ([]byte, error)) (bool, uint32, uint32, uint32, []byte)
TsFramePutStream(sessionId int64, seqNum uint32, data []byte, isLast bool) (bool, []byte)
// Returns: reqOffset, totalSize, chunkData, nextChunkOffset, hasMore
TsFrameGetChunk(sessionId int64, reqOffset uint32, maxChunkSize int, encode func([]byte) []byte) (uint32, uint32, []byte, uint32, bool)
TsFrameGetChunkSticky(...) (uint32, uint32, []byte, uint32, bool)
TsFrameTakeStatTasks(sessionId int64) (StatTasks, int, bool)
TsFrameAckDelivery(sessionId int64, ackOffset uint32, ackNonce uint32)
TsFrameResetUpstream(sessionId int64)
TsFrameResetDownstream(sessionId int64)
```

---

## Data Types

### AgentData

```go
type AgentData struct {
    Crc        string   // sha256(watermarkHex)[:8]
    Id         int64    // Unique ID — int64, NOT string (v1 was string)
    UID        []byte   // Raw implant UID bytes
    Name       string
    SessionKey []byte
    Listener   string
    Async      bool
    ExternalIP string
    InternalIP string
    GmtOffset  int
    Sleep      uint     // seconds — NOT a string (v1 difference)
    Jitter     uint
    Pid        string   // string, not int
    Tid        string
    Arch       string
    Elevated   bool
    Process    string
    Os         int      // OS_UNKNOWN=0 OS_WINDOWS=1 OS_LINUX=2 OS_MAC=3
    OsDesc     string
    Domain     string
    Computer   string
    Username   string
    CreateTime int64
    LastTick   int
    Tags       string
    CustomData []byte
}
```

### TaskData

```go
type TaskData struct {
    Type        int      // TASK_TYPE_LOCAL=0 TASK=1 BROWSER=2 JOB=3 TUNNEL=4 PROXY_DATA=5
    TaskId      int64
    AgentId     int64
    Client      string
    CommandLine string
    MessageType int      // MESSAGE_INFO=5 ERROR=6 SUCCESS=7
    Message     string
    ClearText   string
    Data        []byte   // Serialized wire payload
    Completed   bool
    Priority    uint
    Sync        bool
    OnDispatch  func(ts any, task *TaskData)  // not serialized
    OnComplete  func(ts any, task *TaskData)  // not serialized
}
```

### BuildProfile

```go
type BuildProfile struct {
    BuilderId        string
    AgentConfig      string             // JSON from ax_config.axs container.toJson()
    ListenerProfiles []TransportProfile // [{Watermark, Profile}] per listener
}

type TransportProfile struct {
    Watermark string
    Profile   []byte  // Listener-serialized crypto+config blob
}
```

### AgentFunctions

```go
type AgentFunctions struct {
    CreateCommand func(AgentData, map[string]any) (TaskData, ConsoleMessageData, error)
    ProcessData   func(AgentData, []byte) error
    PackTasks     func(AgentData, []TaskData) ([]byte, error)
    Encrypt       func([]byte, []byte) ([]byte, error)
    Decrypt       func([]byte, []byte) ([]byte, error)
    PivotPackData func(pivotId string, data []byte) (TaskData, error)
    Delivery      DeliveryFunc    // optional direct delivery bypass
    TunnelCB      TunnelCallbacks
    TerminalCB    TerminalCallbacks
}
```

### TunnelCallbacks

```go
type TunnelCallbacks struct {
    ConnectTCP func(channelId int64, tunnelType, addressType int, address string, port int) TaskData
    ConnectUDP func(channelId int64, tunnelType, addressType int, address string, port int) TaskData
    WriteTCP   func(channelId int64, data []byte) TaskData
    WriteUDP   func(channelId int64, data []byte) TaskData
    Pause      func(channelId int64) TaskData
    Resume     func(channelId int64) TaskData
    Close      func(channelId int64) TaskData
    Reverse    func(tunnelId int64, port int) TaskData
    BindTCP    func(channelId int64, addressType int, address string, port int) TaskData
}
```

### TerminalCallbacks

```go
type TerminalCallbacks struct {
    Start func(terminalId int64, program string, sizeH, sizeW, oemCP int) TaskData
    Write func(terminalId int64, oemCP int, data []byte) TaskData
    Close func(terminalId int64) TaskData
}
```

### Constants

```go
OS_UNKNOWN = 0; OS_WINDOWS = 1; OS_LINUX = 2; OS_MAC = 3  // never OS_MACOS

TASK_TYPE_LOCAL = 0; TASK_TYPE_TASK = 1; TASK_TYPE_BROWSER = 2
TASK_TYPE_JOB = 3; TASK_TYPE_TUNNEL = 4; TASK_TYPE_PROXY_DATA = 5

MESSAGE_INFO = 5; MESSAGE_ERROR = 6; MESSAGE_SUCCESS = 7

BUILD_LOG_NONE = 0; BUILD_LOG_INFO = 1; BUILD_LOG_ERROR = 2; BUILD_LOG_SUCCESS = 3

TRANSFER_STATE_RUNNING = 1; TRANSFER_STATE_STOPPED = 2
TRANSFER_STATE_FINISHED = 3; TRANSFER_STATE_CANCELED = 4
TRANSFER_KIND_FILE = 0; TRANSFER_KIND_MEMORY = 1

TUNNEL_TYPE_SOCKS4 = 1; TUNNEL_TYPE_SOCKS5 = 2; TUNNEL_TYPE_SOCKS5_AUTH = 3
TUNNEL_TYPE_LOCAL_PORT = 4; TUNNEL_TYPE_REVERSE = 5; TUNNEL_TYPE_SOCKS_BIND = 6
```

### Helper functions (adaptix package)

```go
// Use these in CreateCommand instead of raw type assertions
adaptix.GetStringArg(args map[string]any, key string) (string, error)
adaptix.GetIntArg(args map[string]any, key string) (int, error)     // float64 → int
adaptix.GetFloatArg(args map[string]any, key string) (float64, error)
adaptix.GetBoolArg(args map[string]any, key string) bool            // never errors
// File args arrive as base64 from ax widget; this decodes automatically
adaptix.GetFileArg(args map[string]any, key string) ([]byte, error)
// Default variants
adaptix.GetStringArgDefault(args map[string]any, key, defaultValue string) string
adaptix.GetFloatArgDefault(args map[string]any, key string, defaultValue float64) float64
// Build a proxy/tunnel task
adaptix.MakeProxyTask(packData []byte, priority uint) TaskData
```

// Process decrypted data from an agent callback
TsAgentProcessData(agentId string, bodyData []byte) error

// Replace the full agent data (must be complete)
TsAgentUpdateData(newAgentData adaptix.AgentData) error

// Partial update — pass a struct with only the fields to change
TsAgentUpdateDataPartial(agentId string, updateData interface{}) error

// Terminate session
TsAgentTerminate(agentId string, terminateTaskId string) error

// Check if agent exists
TsAgentIsExists(agentId string) bool

// Update last-seen tick
TsAgentSetTick(agentId string, listenerName string) error

// Get all hosted payloads/tasks for agent (for callback response)
TsAgentGetHostedAll(agentId string, maxDataSize int) ([]byte, error)

// Send console output to client
TsAgentConsoleOutput(agentId string, result adaptix.ConsoleMessageData) error
```

## Task Methods

```go
// Queue a new task for the agent
TsTaskCreate(agentId string, cmdline string, client string, data adaptix.TaskData)

// Update task status/output
TsTaskUpdate(agentId string, data adaptix.TaskData)

// Get pending tasks up to available size
TsTaskGetAvailableAll(agentId string, availableSize int) ([]adaptix.TaskData, error)
```

## Download Methods

```go
// Register a new download
TsDownloadAdd(agentId string, fileId string, fileName string, totalSize int) error

// Append data chunk to download
TsDownloadUpdate(agentId string, fileId string, data []byte) error

// Mark download complete
TsDownloadClose(agentId string, fileId string) error
```

## Screenshot Methods

```go
// Add a screenshot image
TsScreenshotAdd(agentId string, data []byte, note string) error
```

## Tunnel Methods

```go
// Start a SOCKS/port-forward tunnel
TsTunnelStart(tunnelId string) (string, error)

// Get pipe for tunnel I/O
TsTunnelGetPipe(name string) (*io.PipeReader, *io.PipeWriter, error)

// Send data to channel within tunnel
TsTunnelConnectionData(tunnelId string, channelId int, data []byte) error

// Close a channel
TsTunnelConnectionClose(tunnelId string, channelId int) error
```

## Terminal Methods

```go
// Get pipe for interactive terminal session
TsTerminalGetPipe(agentId string, terminalId string) (*io.PipeReader, *io.PipeWriter, error)
```

## Pivot Methods

```go
// Register a linked/pivoted listener
TsPivotCreate(pivotName string, agentName string, listenerName string) error

// Remove pivot
TsPivotDelete(pivotName string) error
```

## Build Methods

```go
// Execute external build tool (go build, make, cargo, etc.)
TsAgentBuildExecute(builderId string, workingDir string, program string, args ...string) error

// Log build progress
TsAgentBuildLog(builderId string, status int, message string) error
```

## Service Methods

```go
// Send data to specific client's service handler
TsServiceSendDataClient(serviceName string, client string, function string, args string) error

// Send data to all connected clients
TsServiceSendDataAll(serviceName string, function string, args string) error

// Get/set persistent extender data
TsExtenderDataGet(extenderName string, key string) (string, error)
TsExtenderDataSet(extenderName string, key string, value string) error
```

## Event Methods

```go
// Register event hook (phase: 0=pre, 1=post; lower priority = earlier)
TsEventHookRegister(event string, phase int, priority int, handler func(...)) (string, error)
```

### Available events

| Event | Phase | Payload |
|-------|-------|---------|
| `agent.create` | pre/post | AgentData |
| `agent.generate` | pre/post | BuildProfile, payload bytes |
| `agent.terminate` | pre/post | AgentData |
| `listener.create` | pre/post | ListenerData |
| `listener.start` | pre/post | ListenerData |
| `listener.stop` | pre/post | ListenerData |

## AxScript Methods

```go
// Execute AxScript (for plugins registering via ax_config.axs)
TsAxScriptRegister(axFile string, moduleDir string) error
```

---

## Data Types

### AgentData

```go
type AgentData struct {
    Id             string  // Unique agent ID (UUID)
    Crc            string  // sha256(watermarkHex)[:8]
    Name           string  // Agent display name
    SessionKey     []byte  // Per-session encryption key
    Listener       string  // Listener name that created this agent
    ExternalIP     string  // External IP from listener
    InternalIP     string  // Internal IP reported by agent
    GatewayIP      string  // Gateway IP from implant
    Domain         string  // Domain name
    Computer       string  // Hostname
    Username       string  // Current user
    Impersonated   string  // Impersonated user (if any)
    Process        string  // Process name
    Pid            string  // Process ID (string, not int!)
    Tid            string  // Thread ID
    ParentPid      string  // Parent PID
    Arch           string  // x86 / x64
    Os             int     // adaptix.OS_WINDOWS=1, OS_LINUX=2, OS_MAC=3
    OsDesc         string  // Detailed OS string
    Sleep          uint    // Sleep interval in seconds (not string!)
    Jitter         float64 // Jitter percentage 0.0-1.0
    Tags           string  // Comma-separated tags
    Mark           string  // Custom mark
    Color          string  // Display color
    IsElevated     bool    // Admin/root
    IsEncrypted    bool    // Session is encrypted
    Async          bool    // Async callback model
    CreateTime     int64   // Unix timestamp
    LastTick       int     // Last callback tick
}
```

### TaskData

```go
type TaskData struct {
    TaskId      string  // Unique task ID (UUID)
    AgentId     string  // Owning agent
    Type        int     // TASK_TYPE_TASK=0, TASK_TYPE_JOB=1, TASK_TYPE_TUNNEL=2, TASK_TYPE_BROWSER=3
    CommandLine string  // Displayed in UI
    Message     string  // Result message (HTML supported)
    ClearText   string  // Plain text output
    Client      string  // Operator who created
    StartDate   int64
    FinishDate  int64
    Completed   bool
    Sync        bool    // If true, hold response until complete
    Data        []byte  // Serialized command for wire
}
```

### ListenerData

```go
type ListenerData struct {
    RegName    string  // Registration name (e.g. "BeaconHTTP")
    BindHost   string
    BindPort   string
    AgentAddr  string  // Advertised address for agents
    Status     string  // "Running", "Stopped"
    Config     string  // JSON config
    CreateTime int64
}
```

### BuildProfile

```go
type BuildProfile struct {
    BuilderId        string            // Unique build ID (for TsAgentBuildLog)
    AgentName        string            // Agent type name
    AgentConfig      string            // JSON from UI form
    ListenerProfiles []ListenerProfile // Embedded listener configs
}

type ListenerProfile struct {
    Name    string
    Config  []byte  // Serialized profile from listener
}
```

### ConsoleMessageData

```go
type ConsoleMessageData struct {
    Type    int    // CONSOLE_OUT_INFO=0, CONSOLE_OUT_ERROR=1, CONSOLE_OUT_SUCCESS=2
    Message string // HTML content for the console
}
```

### TunnelCallbacks / TerminalCallbacks

```go
type TunnelCallbacks interface {
    TunnelCreateCallback(taskData adaptix.TaskData, agentData adaptix.AgentData) error
    TunnelWriteCallback(tunnelId string, channelId int, data []byte) (adaptix.TaskData, error)
    TunnelCloseCallback(tunnelId string, channelId int) (adaptix.TaskData, error)
    TunnelNoJobCallback(tunnelId string) (adaptix.TaskData, error)
}

type TerminalCallbacks interface {
    TerminalCreateCallback(taskData adaptix.TaskData, agentData adaptix.AgentData) error
    TerminalWriteCallback(agentData adaptix.AgentData, terminalId string, data []byte) (adaptix.TaskData, error)
    TerminalCloseCallback(agentData adaptix.AgentData, terminalId string) (adaptix.TaskData, error)
    TerminalNoJobCallback(agentData adaptix.AgentData, terminalId string) (adaptix.TaskData, error)
}
```

### OS Constants

```go
const (
    OS_WINDOWS = 1
    OS_LINUX   = 2
    OS_MAC     = 3  // NOT OS_MACOS
)
```

### Arch Constants

```go
const (
    ARCH_X86   = "x86"
    ARCH_X64   = "x64"
    ARCH_ARM   = "arm"
    ARCH_ARM64 = "arm64"
)
```
