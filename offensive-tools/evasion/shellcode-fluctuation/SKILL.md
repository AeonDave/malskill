---
name: shellcode-fluctuation
description: "C++ shellcode fluctuation technique that encrypts injected shellcode between C2 sleep intervals to evade EDR memory scans. Use when implants are being detected by memory-scanning EDR products during sleep."
license: MIT
compatibility: "C++; Windows x64; MSVC or MinGW; github.com/mgeeky/ShellcodeFluctuation"
metadata:
  author: AeonDave
  version: "1.0"
---

# Shellcode Fluctuation

C++ in-memory evasion — XOR-encrypts shellcode in RX pages during C2 sleep to defeat memory scanners.

## Quick Start

```bash
# Clone and build with MSVC
git clone https://github.com/mgeeky/ShellcodeFluctuation
# Open in Visual Studio, build Release x64

# Or MinGW
x86_64-w64-mingw32-g++ -O2 -o fluctuator.exe main.cpp -lntdll
```

## Core Mechanism

```
[Shellcode in memory]
  Awake:  → Decrypt → Execute → Sleep
  Asleep: → Encrypt (XOR) → change PROT to RW → Scanner sees garbage
  Wake:   → change PROT to RX → Decrypt → Resume
```

## Configuration (main.cpp)

```cpp
#define SHELLCODE_FLUCTUATE   true
#define XOR_KEY               0xdeadbeef
#define SLEEP_INTERVAL_MS     5000
```

## Common Workflows

**Integrate into Cobalt Strike BOF loader:**
1. Generate raw shellcode from CS listener
2. Embed in fluctuator loader source
3. Call `FluctuateShellcode()` wrapper before Sleep()

**Combine with indirect syscalls:**
```cpp
// Replace VirtualProtect with direct NtProtectVirtualMemory
// via syscall stub to avoid API hooks
```

## Resources

| File | When to load |
|------|--------------|
| `references/` | Hook evasion and memory protection patterns |
