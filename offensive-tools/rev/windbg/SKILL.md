---
name: windbg
description: "Auth/lab ref: Microsoft's debugger for user-mode and kernel-mode Windows debugging, crash dump analysis, driver reversing, and rootkit analysis."
license: MIT
compatibility: "Windows; Microsoft Store (WinDbg Preview) or Windows SDK; supports x86/x64/ARM64."
metadata:
  author: AeonDave
  version: "1.1"
---

# WinDbg

Microsoft's debugger — kernel-mode debugging, crash dump analysis, driver reversing, and advanced user-mode debugging.

## Installation

```powershell
# WinDbg Preview (recommended — modern UI, TTD support)
winget install --id Microsoft.WinDbg --accept-source-agreements

# Classic WinDbg (part of Windows SDK)
# Download from https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

# Symbol server setup (critical for useful debugging)
# In WinDbg:
.sympath srv*C:\Symbols*https://msdl.microsoft.com/download/symbols
.reload
```

## Quick Start — User Mode

```
# Open executable
File -> Open Executable -> select target.exe

# Or attach to running process
File -> Attach to a Process -> select PID

# Set breakpoint and run
bp kernel32!CreateFileW
g                           # Go (run)
```

## Quick Start — Kernel Mode

```powershell
# Enable kernel debugging on target
bcdedit /debug on
bcdedit /dbgsettings net hostip:192.168.1.100 port:50000

# In WinDbg: File -> Kernel Debug -> Net -> enter key from target
# Or: File -> Open Crash Dump -> load .dmp file
```

## Essential Commands

### Execution Control

| Command | Purpose |
|---------|---------|
| `g` | Go (continue) |
| `p` | Step over |
| `t` | Step into (trace) |
| `pt` | Step to next return |
| `pc` | Step to next call |
| `gu` | Step out (go up) |
| `bp ADDR` | Set breakpoint |
| `bp MODULE!FUNC` | Breakpoint on function |
| `bu MODULE!FUNC` | Deferred breakpoint (module not yet loaded) |
| `ba r4 ADDR` | Hardware breakpoint (read 4 bytes at ADDR) |
| `ba w4 ADDR` | Hardware breakpoint (write 4 bytes) |
| `bl` | List breakpoints |
| `bc *` | Clear all breakpoints |
| `.restart` | Restart debugging session |

### Inspection

| Command | Purpose |
|---------|---------|
| `r` | Show registers |
| `r rax=0` | Set register value |
| `db ADDR` | Display bytes |
| `dd ADDR` | Display DWORDs |
| `dq ADDR` | Display QWORDs |
| `da ADDR` | Display ASCII string |
| `du ADDR` | Display Unicode string |
| `dps ADDR` | Pointer-sized values with symbols |
| `u ADDR` | Unassemble (disassemble) |
| `uf FUNC` | Unassemble function |
| `k` | Stack trace |
| `kP` | Stack trace with parameters |
| `~` | List threads |
| `~Ns` | Switch to thread N |
| `.frame N` | Switch to stack frame N |

### Memory Search

| Command | Purpose |
|---------|---------|
| `s -a RANGE "string"` | Search ASCII string |
| `s -u RANGE L1000 "string"` | Search Unicode string |
| `s -b RANGE 4D 5A` | Search byte pattern (MZ header) |
| `.writemem FILE ADDR L SIZE` | Dump memory to file |

### Module and Symbol

| Command | Purpose |
|---------|---------|
| `lm` | List loaded modules |
| `lm m ntdll` | Module info for ntdll |
| `x ntdll!Nt*` | List symbols matching pattern |
| `ln ADDR` | Nearest symbol to address |
| `.reload /f` | Force reload symbols |

### Process and Thread

| Command | Purpose |
|---------|---------|
| `!process 0 0` | List all processes (kernel) |
| `!process ADDR 7` | Full process info |
| `.process /i ADDR` | Switch context to process (kernel) |
| `!peb` | Process Environment Block |
| `!teb` | Thread Environment Block |
| `!handle` | List handles |
| `!dlls` | Loaded DLL list with details |

## Crash Dump Analysis

```
# Open dump file
File -> Open Crash Dump -> select .dmp

# First commands after loading a dump:
!analyze -v              # Automated crash analysis (start here)
.ecxr                    # Switch to exception context record
k                        # Stack trace at crash
lm                       # Loaded modules
!process 0 0             # Process list
```

### BSOD Analysis

```
# After !analyze -v:
.bugcheck                # Bug check code and params
!pool ADDR               # Pool analysis for pool corruption
!verifier                # Driver verifier info
!irp ADDR                # IRP analysis
dt nt!_DRIVER_OBJECT ADDR  # Inspect driver object
```

## Kernel Mode Malware Analysis

### Driver/rootkit analysis

```
# List all drivers
lm t n                   # List all modules by type

# Find suspicious drivers
!object \Driver          # List driver objects
!drvobj \Driver\suspect 7  # Full driver object listing

# Inspect driver dispatch routines
dt nt!_DRIVER_OBJECT ADDR
dps ADDR+0x70 L1C        # MajorFunction table (IRP handlers)

# SSDT hook detection
dps nt!KiServiceTable L100
# Compare each entry — hooks point outside ntoskrnl range

# IDT analysis
!idt                     # Interrupt Descriptor Table
```

### Process hiding detection

```
# Cross-reference process lists
!process 0 0             # Active process list (via PsActiveProcessList)
!for_each_process "r $t0 = @$proc; .printf \"%p %s\\n\", @$t0, @@c++(@$t0->ImageFileName)"
# Compare with direct EPROCESS walk for hidden processes
```

## User Mode Malware Analysis

### Injection detection

```
bp kernel32!VirtualAllocEx
bp kernel32!WriteProcessMemory
bp kernel32!CreateRemoteThread
bp ntdll!NtMapViewOfSection
g
# On hit: inspect target process handle and injected data
dd @rcx                  # Buffer being written
```

### API monitoring with breakpoint commands

```
# Log all CreateFile calls without stopping
bp kernel32!CreateFileW ".printf \"CreateFile: %mu\\n\", @rcx; gc"

# Log registry operations
bp advapi32!RegOpenKeyExW ".printf \"RegOpen: %mu\\n\", poi(@rsp+8); gc"

# Log network connections
bp ws2_32!connect "dd @rdx L4; gc"
```

## Time Travel Debugging (TTD)

```
# Record execution (WinDbg Preview)
File -> Launch Executable (Advanced) -> check "Record with Time Travel Debugging"

# After recording — navigate backwards:
g-                      # Reverse continue
p-                      # Reverse step over
t-                      # Reverse step into

# Find when memory was written:
ba w4 ADDR             # Set write watchpoint
g-                      # Go backwards until write

# TTD queries (LINQ-style):
dx @$cursession.TTD.Calls("kernel32!CreateFileW")
dx @$cursession.TTD.Calls("ntdll!NtCreateThreadEx").Count()
```

## WinDbg Scripting

```
# Conditional breakpoint with logging
bp kernel32!VirtualAlloc "j (@r8==0x40) '.printf \"RWX alloc: size=%x\\n\",@rdx; gc' ; 'gc'"

# Walk a linked list
!list -t nt!_LIST_ENTRY.Flink -x "dt nt!_EPROCESS @$extret" ADDR

# Extension commands
.load C:\path\to\extension.dll
!mex.help                # MEX extension commands
```

## Resources

| File | When to load |
|------|--------------|
| [references/kernel-debugging.md](references/kernel-debugging.md) | Kernel driver analysis and rootkit detection workflows |
| [references/crash-dump-analysis.md](references/crash-dump-analysis.md) | BSOD and crash dump triage methodology |
