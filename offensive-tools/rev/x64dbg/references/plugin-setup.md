# x64dbg — Plugin Setup & Configuration

## Plugin Installation

```
# Plugin location:
# x64dbg/  (install dir)
# ├── x64/plugins/    ← 64-bit plugins (.dp64)
# ├── x32/plugins/    ← 32-bit plugins (.dp32)
# └── plugins/        ← shared (some)

# Load: restart x64dbg, Plugins menu appears
# Or: Plugins → Manage Plugins (if plugin manager installed)
```

## Essential Plugins

### ScyllaHide (anti-anti-debug)

**Most important plugin for malware analysis.**

```
# Download: https://github.com/x64dbg/ScyllaHide/releases
# Install: copy ScyllaHide.dp64 + HookLibraryx64.dll to x64/plugins/

# Usage:
Plugins → ScyllaHide → Options

# Enable everything for maximum coverage:
☑ PEB.BeingDebugged           # Clears debugger flag in PEB
☑ NtGlobalFlag                # Clears debug heap flags
☑ HeapFlags                   # Normalizes heap flags
☑ NtQueryInformationProcess   # Hooks NTQIP to hide debugger
☑ NtSetInformationThread      # Prevents thread hiding tricks
☑ GetTickCount                # Spoofs timing (anti-timing attacks)
☑ QueryPerformanceCounter     # Spoofs QPC
☑ OutputDebugString           # Silences IsDebuggerPresent via ODS
☑ NtQuerySystemInformation    # Hides from system process queries
☑ NtYieldExecution            # Prevents NTYP anti-debug tricks
☑ SwitchDesktop               # Prevents desktop switch detection
☑ BlockInput                  # Prevents input block
☑ NtUserFindWindowEx          # Hides debugger window
☑ NtUserBuildHwndList         # Hides debugger in window list
☑ NtUserQueryWindow           # Hides debugger from window queries
☑ NtSetDebugFilterState       # Prevents debug filter manipulation
☑ TLS Callbacks               # Enable TLS callback interception

# Kernel mode protection (requires admin):
☑ NtSetInformationThread (Kernel)
☑ NtQueryObject (Kernel)
```

### Scylla (import reconstruction)

```
# Pre-installed in recent x64dbg builds, or:
# Download: https://github.com/NtQuery/Scylla
# Install: copy Scylla.dp64 to x64/plugins/

# Usage: Plugins → Scylla (or Ctrl+I shortcut in some builds)
# See unpacking-guide.md for full workflow
```

### xAnalyzer

Automatically annotates API calls with parameter names and types.

```
# Download: https://github.com/ThunderCls/xAnalyzer
# Install: copy xAnalyzer.dp64 + xAnalyzer/ folder to x64/plugins/

# Usage:
Plugins → xAnalyzer → Analyze Section   # Analyze current function
Plugins → xAnalyzer → Analyze All       # Analyze entire binary

# Results: API calls in disassembly get annotated:
# call CreateFileW  →  ; lpFileName: "C:\malware\config.dat"
```

### OllyDumpEx / Titan Dumper

```
# OllyDumpEx (ports to x64dbg):
# Download: https://low-priority.appspot.com/ollydumpex/

# Titan Dumper (alternative):
# Built into some x64dbg versions

# Usage: Plugins → OllyDumpEx → Dump Process
# For PE reconstruction after manual OEP finding
```

### SwissArmyKnife

Quick access to assembler, label creation, data operations.

```
# Download: https://github.com/horsicq/x64dbg-Plugin-SwissArmyKnife
# Install: copy to plugins/

# Features:
# - Quick assemble/disassemble
# - String search with regex
# - Breakpoint management shortcuts
```

### LordPE / PE Editor

```
# Integrated PE editor (some x64dbg versions)
# Or run separately: lordpe.exe
# Use for: header fixing after dump, section permissions, EP modification
```

## Recommended Configuration

### Options → Preferences

```
Events tab:
☑ Break on TLS Callbacks      # Catch TLS-based packers
☑ Break on Entry Breakpoint   # Standard behavior
☑ Break on DLL Load/Unload    # Track library loading
☑ System Breakpoint           # Break at ntdll init (early start)

Engine tab:
☑ Enable Hardware Breakpoints # Required for ScyllaHide to work fully
Thread Priority: Normal
```

### Options → Appearance

```
# Color scheme: dark theme recommended for long sessions
# Highlight colors: customize to distinguish code/data/imports
```

### Keyboard Shortcuts (Options → Shortcuts)

| Action | Recommended Key |
|--------|----------------|
| Toggle Breakpoint | `F2` (default) |
| Step Over | `F8` (default) |
| Step Into | `F7` (default) |
| Run | `F9` (default) |
| Execute Till Return | `Ctrl+F9` |
| Go to Address | `Ctrl+G` |
| Search Pattern | `Ctrl+B` |
| Follow in Dump | `Ctrl+D` |
| Assemble | `Space` |

## Anti-Anti-Debug Techniques (Manual + ScyllaHide)

### PEB.BeingDebugged (manual)

```
# In x64dbg:
Follow in Dump → GS:[0x60]          # 64-bit PEB address
# PEB+0x02 = BeingDebugged byte
# Change from 0x01 to 0x00
```

### NtGlobalFlag (manual)

```
# PEB+0xBC (64-bit) or PEB+0x68 (32-bit)
# Normal value: 0x00000000
# Debugged: 0x00000070 (FLG_HEAP_ENABLE_TAIL_CHECK | FLG_HEAP_ENABLE_FREE_CHECK | FLG_HEAP_VALIDATE_PARAMETERS)
# Set to 0x00
```

### Heap flags (manual)

```
# ProcessHeap = [PEB+0x30] (64-bit)
# ProcessHeap+0x70 = Flags (should be 0x00000002)
# ProcessHeap+0x74 = ForceFlags (should be 0x00000000)
# Debugged: Flags=0x40000062, ForceFlags=0x40000060
# Fix: set both to normal values
```

### Timing attacks

```
# GetTickCount, QueryPerformanceCounter — ScyllaHide handles
# Manual: bp GetTickCount → set return value via:
SetHardwareBreakpoint GetTickCount, "x"
# On return: r rax=<spoofed_time>
```

## Conditional Breakpoints (bpcnd)

```
# bpcnd <address> <condition>
# Condition uses x64dbg expression evaluator

# Break VirtualAlloc only when size > 0x10000
bpcnd VirtualAlloc,rcx>10000

# Break WriteProcessMemory on any call
bpcnd WriteProcessMemory,1

# Break when register matches value
bpcnd 0x401234,[rax]==deadbeef

# Break when memory at address contains value
bpcnd 0x401234,[0x404010]==1

# Combine conditions
bpcnd VirtualAlloc,[rcx]>0x1000 && [rdx]!=0

# Logging BP (non-stop): log arg then continue
SetBreakpointCommand VirtualAlloc,"log \"VirtualAlloc size={rcx}\"; ret"

# FastResume: don't stop if condition false (performance)
SetBreakpointFastResume VirtualAlloc,1
```

## Memory Dump Commands

```
# savedata: dump memory region to file
# savedata <filename>,<address>,<size>

savedata dump.bin,mem.base(rax),mem.size(rax)   # Dump region containing rax
savedata out.bin,401000,1000                     # Dump 0x1000 bytes from 0x401000

# Helper expressions:
# mem.base(<addr>)  → start of memory region containing <addr>
# mem.size(<addr>)  → size of that region
# mem.iscode(<addr>) → 1 if region is executable

# Dump all executable anonymous regions (injected shellcode):
# Use script loop — see unpacking-guide.md

# Dump via Scylla: Plugins → Scylla → Dump
# (reconstructs PE headers + fixes IAT)
```

## x64dbg Automate (Python Automation)

Python client library for scripting x64dbg at scale.

```bash
# Install:
pip install x64dbg-automate

# Requires x64dbg running with automate plugin loaded
```

```python
from x64dbg_automate import X64DbgClient

client = X64DbgClient()
client.connect()

# Run to VirtualAlloc, dump each allocation
client.set_breakpoint("VirtualAlloc")
while True:
    client.go()
    state = client.get_registers()
    size = state['rcx']
    if size > 0x1000:
        client.go()  # run through call, rax = return address
        alloc_base = client.get_registers()['rax']
        data = client.read_memory(alloc_base, size)
        with open(f"dump_{alloc_base:x}.bin", "wb") as f:
            f.write(data)
        print(f"Dumped {size:#x} bytes @ {alloc_base:#x}")
```

## Useful Command Bar Commands

```
# Logging without stopping (non-breaking BP):
SetBreakpointCommand <addr>, "log \"{addr}:{dis}\"; run"

# Break on specific DLL load:
SetBreakpointDLLEntry malware.dll

# Memory search from command bar:
findallmem 0, "4D 5A"           # Find all MZ headers in memory

# Hardware memory access breakpoint:
bphws <addr>, "r"                # Break on read
bphws <addr>, "w"                # Break on write
bphws <addr>, "x"                # Break on execute

# Export current labels/comments:
savedb                           # Save to <file>.dd64 (x64dbg database)
```

## Verification After Analysis

```
# Export database (labels, comments, BPs):
File → Database → Save Database

# Export patches:
Patches → right-click → Export Patch

# Load clean binary + database in new session:
File → Open → patched.exe
File → Database → Load → select .dd64 file
# All labels and comments restored
```
