---
name: x64dbg
description: "Auth/lab ref: User-mode debugger for Windows x64/x86 with plugin ecosystem for malware analysis, unpacking, API tracing, and anti-anti-debug."
license: MIT
compatibility: "Windows x86/x64; GUI; x64dbg.com."
metadata:
  author: AeonDave
  version: "1.1"
---

# x64dbg

Windows debugger for dynamic malware analysis, unpacking, and API tracing.

## Installation

```
# Download from https://x64dbg.com or https://github.com/x64dbg/x64dbg/releases
# Extract → run x96dbg.exe (launcher auto-selects x32dbg/x64dbg)

# Essential plugins (copy to plugins/ directory):
# - ScyllaHide: anti-anti-debug (hide debugger from malware)
# - Scylla: import reconstruction for dumping
# - xAnalyzer: automatic API parameter annotation
# - SwissArmyKnife: assembler/label shortcuts
# - TitanHide: kernel-mode anti-anti-debug
```

## Quick Start

1. **File → Open** → target executable
2. Program breaks at system entrypoint
3. Set breakpoints: `F2` on instruction, or `bp CreateRemoteThread` in command bar
4. **Run**: `F9` | **Step over**: `F8` | **Step into**: `F7`

## Key Panels

| Panel | Purpose |
|-------|---------|
| CPU | Disassembly + registers + stack + hex dump |
| Log | Debug events, API calls, plugin output |
| Breakpoints | All breakpoints with conditions |
| Memory Map | Virtual memory regions and permissions |
| Call Stack | Current thread call stack |
| Symbols | Module imports/exports/labels |
| Threads | All process threads |
| Handles | Open handles |
| References | Search results / XREFs |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F2` | Toggle breakpoint |
| `F7` | Step into |
| `F8` | Step over |
| `F9` | Run |
| `Ctrl+F9` | Execute till return |
| `Ctrl+G` | Go to address/expression |
| `Ctrl+F` | Find pattern in module |
| `Ctrl+B` | Search binary pattern |
| `Space` | Assemble instruction |
| `Ctrl+E` | Edit bytes |
| `F4` | Run to cursor |
| `Ctrl+D` | Follow in dump |
| `Alt+B` | Breakpoints window |

## Command Bar Commands

| Command | Purpose |
|---------|---------|
| `bp VirtualAlloc` | Breakpoint on API |
| `bp ADDR` | Breakpoint on address |
| `bphws ADDR, "w", 4` | Hardware write breakpoint |
| `bpc ADDR` | Conditional breakpoint |
| `SetBreakpointCondition ADDR, "rax==0"` | Set condition |
| `log "msg: {rax}"` | Log with register values |
| `dump ADDR` | Follow address in dump |
| `disasm ADDR` | Follow in disassembly |

## Common Workflows

### Unpack malware

```
1. Open sample → reaches system entrypoint
2. Look for unpacking patterns:
   a. VirtualAlloc with PAGE_EXECUTE_READWRITE (0x40)
   b. Large memcpy/memmove to allocated region
   c. Jump to allocated region (jmp reg / call reg / ret to new region)
3. Set breakpoint: bp VirtualAlloc → F9
4. When hit: check r8 (or stack arg) for 0x40 (RWX)
5. Execute till return (Ctrl+F9) → follow rax in dump
6. Set hardware execute breakpoint on new allocation: bphws rax, "x"
7. F9 → program jumps to unpacked code (OEP)
8. Plugins → Scylla → IAT Autosearch → Get Imports → Dump → Fix Dump
```

### Find C2 communication

```
bp ws2_32.connect
bp ws2_32.send
bp ws2_32.recv
bp wininet.InternetConnectW
bp wininet.HttpSendRequestW
bp winhttp.WinHttpConnect
F9
# On hit: examine stack/registers for URLs, IPs, ports
# Follow buffer pointers in dump to see HTTP requests/responses
```

### Anti-debug bypass (manual)

```
# PEB.BeingDebugged
# In dump: follow PEB address, set byte at offset +2 to 0
dump fs:[30]            # 32-bit: PEB address
# Or dump gs:[60]       # 64-bit

# NtGlobalFlag
# PEB offset +0x68 (32-bit) or +0xBC (64-bit) → set to 0

# Heap flags
# PEB → ProcessHeap → Flags/ForceFlags → set to expected values

# Better: use ScyllaHide plugin (Plugins → ScyllaHide → Options)
# Enable: PEB BeingDebugged, NtGlobalFlag, HeapFlags, NtQueryInformationProcess,
# GetTickCount, QueryPerformanceCounter, NtSetInformationThread
```

### Trace execution

```
# Conditional trace: log all API calls
Trace → Trace Over → set stop condition
# Or use command bar:
TraceOverConditionalLog                 # Trace + log each instruction
TraceIntoConditionalLog                 # Step into + log

# Breakpoint logging (non-stop):
bp kernel32.CreateFileW
SetBreakpointCommand ADDR, "log \"CreateFile: {s:utf16@rcx}\"; run"
```

### Memory patching

```
# Patch instruction at runtime:
1. Select instruction → Space → type new instruction → OK
2. Or: Ctrl+E on bytes → edit hex directly

# Patch jump condition:
# je → jmp: change 0x74 to 0xEB (short) or 0x0F84 to 0x0F85 (near)
# je → nop: fill with 0x90

# Save patches:
Patches → right-click → Export → save to file
```

### Scripting (x64dbg script)

```
// x64dbg script language
bp VirtualAlloc
loop:
  run
  cmp r8, 0x40        // Check if PAGE_EXECUTE_READWRITE
  jne loop
  rtr                  // Run to return
  bphws rax, "x"      // HW execute BP on allocated memory
  run                  // Hit = OEP reached
  msg "OEP found"
```

## Plugin Ecosystem

| Plugin | Purpose |
|--------|---------|
| ScyllaHide | Anti-anti-debug (kernel + user mode) |
| Scylla | Import reconstruction for dumps |
| xAnalyzer | Auto-annotate API calls with parameters |
| SwissArmyKnife | Quick assembler, label management |
| TitanHide | Kernel-mode debugger hiding |
| OllyDumpEx | Dump process memory |
| Multiline Ultimate Assembler | Edit multiple instructions |

## Resources

| File | When to load |
|------|--------------|
| [references/unpacking-guide.md](references/unpacking-guide.md) | Step-by-step unpacking methodology for common packers |
| [references/plugin-setup.md](references/plugin-setup.md) | Plugin installation and configuration |
