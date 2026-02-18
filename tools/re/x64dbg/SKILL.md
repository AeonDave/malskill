---
name: x64dbg
description: "User-mode debugger for Windows x64/x86 with plugin ecosystem for malware analysis, unpacking, and vulnerability research. Use when dynamically analyzing PE malware, unpacking obfuscated executables, or tracing Windows API calls."
license: MIT
compatibility: "Windows x86/x64; GUI; x64dbg.com"
metadata:
  author: AeonDave
  version: "1.0"
---

# x64dbg

Windows debugger for dynamic malware analysis, unpacking, and API tracing.

## Quick Start

1. Download from x64dbg.com → extract → run `x96dbg.exe` (launcher auto-selects x32/x64)
2. **File > Open** → target executable
3. Set breakpoint: `F2` on instruction, or `bp CreateRemoteThread`
4. **Run**: `F9` | **Step over**: `F8` | **Step into**: `F7`
5. **Plugins**: load ScyllaHide (anti-anti-debug), xAnalyzer

## Key Panels

| Panel | Purpose |
|-------|---------|
| CPU | Disassembly + registers + stack + hex |
| Log | API calls, plugin output |
| Breakpoints | Manage all BPs |
| Memory Map | Virtual memory regions |
| References | XREFs to selected |
| Symbols | Module imports/exports |

## Common Commands

| Action | Key / Command |
|--------|--------------|
| Run / Pause | F9 |
| Step Over | F8 |
| Step Into | F7 |
| Execute till return | Ctrl+F9 |
| Set breakpoint | F2 |
| Breakpoint on API | `bp VirtualAlloc` in command bar |
| Follow in dump | Ctrl+D on address |
| Search strings | Ctrl+F in disassembly |

## Common Workflows

**Unpack malware:**
1. Open sample → run until OEP (watch for `jmp eax/rax` after decryption loop)
2. Dump process with Scylla plugin → fix imports → save

**Find C2 callback:**
```
bp WS2_32.connect
bp WS2_32.send
F9 → examine stack args
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Plugin list and unpack methodology |
