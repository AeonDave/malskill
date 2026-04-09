# Teamserver API Reference

Complete method signatures for the Teamserver interface (axc2 v1.2.0).
The `Teamserver` object is obtained by type-asserting the `ts any` parameter in `InitPlugin`.

---

## Agent Methods

```go
// Create a new agent session. agentCrc = sha256(watermarkHex)[:8]
TsAgentCreate(agentCrc string, agentId string, beat []byte, listenerName string, externalIP string, async bool) (adaptix.AgentData, error)

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
