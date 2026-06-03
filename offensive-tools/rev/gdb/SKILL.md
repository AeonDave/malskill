---
name: gdb
description: "Auth/lab ref: GDB with pwndbg/GEF for dynamic binary analysis, malware debugging, exploitability research, and reverse engineering on Linux/WSL."
license: MIT
compatibility: "C; Linux/WSL/macOS."
metadata:
  author: AeonDave
  version: "1.1"
---

# GDB

GNU debugger enhanced with pwndbg or GEF — the primary dynamic analysis tool for ELF binaries.

## Installation

```bash
# GDB
sudo apt-get install -y gdb

# pwndbg (recommended for RE/malware)
git clone https://github.com/pwndbg/pwndbg ~/pwndbg
cd ~/pwndbg && ./setup.sh

# OR GEF (lighter)
bash -c "$(curl -fsSL https://gef.blah.cat/sh)"

# OR portable pwndbg tarball (no git needed)
# Download from https://github.com/pwndbg/pwndbg/releases
tar -xf pwndbg_*.tar.xz
./pwndbg/bin/pwndbg ./binary
```

## Quick Start

```bash
# Open binary
gdb -q ./binary

# With pwndbg:
pwndbg> start            # Run to main
pwndbg> disass main      # Disassemble main
pwndbg> info functions   # List all functions
pwndbg> context          # Show registers, code, stack, backtrace
```

## Essential Commands

### Navigation and Execution

| Command | Purpose |
|---------|---------|
| `start` | Start and break at `main` |
| `starti` | Start and break at first instruction |
| `run [args]` | Run with arguments |
| `continue` / `c` | Continue execution |
| `nexti` / `ni` | Step over (instruction level) |
| `stepi` / `si` | Step into (instruction level) |
| `next` / `n` | Step over (source level) |
| `finish` | Run until current function returns |
| `until *ADDR` | Run until address |

### Breakpoints

| Command | Purpose |
|---------|---------|
| `break main` | Break at function |
| `break *0x401234` | Break at address |
| `break connect` | Break on libc call |
| `rbreak regex` | Break on all functions matching regex |
| `catch syscall ptrace` | Catch specific syscall |
| `watch *0xADDR` | Hardware watchpoint (data bp) |
| `info breakpoints` | List breakpoints |
| `delete N` | Delete breakpoint N |
| `condition N expr` | Conditional breakpoint |

### Inspection

| Command | Purpose |
|---------|---------|
| `info registers` / `regs` | All registers |
| `x/20gx $rsp` | Examine 20 qwords at RSP |
| `x/s $rdi` | Print string at RDI |
| `x/10i $pc` | Disassemble 10 instructions at PC |
| `telescope $rsp 30` | pwndbg: smart stack dump |
| `vmmap` | pwndbg: memory map |
| `hexdump $rsp 0x80` | pwndbg: hex dump |
| `search --string "http"` | pwndbg: search memory |
| `bt` | Backtrace (call stack) |
| `info proc mappings` | Process memory layout |

### Memory and Data

| Command | Purpose |
|---------|---------|
| `set {int}0xADDR = VALUE` | Write to memory |
| `set $rax = 0` | Modify register |
| `dump binary memory out.bin ADDR1 ADDR2` | Dump memory range to file |
| `find /b ADDR1, ADDR2, 0x4d, 0x5a` | Find byte pattern |

## Malware Analysis Workflows

### Anti-debug bypass (ptrace)

```bash
# Most Linux malware uses ptrace(PTRACE_TRACEME) to detect debuggers
catch syscall ptrace
run
# When caught:
set $rax = 0           # Fake success
continue
```

### Anti-debug bypass (/proc/self/status)

```bash
# Malware reads TracerPid from /proc/self/status
catch syscall openat
run
# When openat for /proc/self/status is caught, let it proceed
# and break on read to patch the result
```

### Unpacking in memory

```bash
# Break when malware changes memory permissions (RWX = unpacked code)
catch syscall mprotect
run
# When hit: check arguments
x/s $rdi     # address
p/x $rsi     # length
p/x $rdx     # prot flags (7 = RWX)
# After mprotect returns, dump the unpacked region:
dump binary memory unpacked.bin $rdi ($rdi + $rsi)
```

### Network activity tracing

```bash
break connect
break send
break recv
break sendto
break getaddrinfo
run
# On hit:
bt                     # See call chain
x/s $rdi              # Examine args
```

### Full execution trace (pwndbg)

```bash
# Trace all calls with arguments
pwndbg> set logging on
pwndbg> break *entry_point
pwndbg> commands
> silent
> bt 1
> continue
> end
pwndbg> run
```

## Python Scripting

```python
# GDB Python API — run with: gdb -q -x script.py ./binary
import gdb

class MalwareTracer(gdb.Breakpoint):
    def __init__(self, func):
        super().__init__(func, gdb.BP_BREAKPOINT)
        self.func = func
        self.silent = True

    def stop(self):
        frame = gdb.selected_frame()
        rdi = int(frame.read_register("rdi"))
        rsi = int(frame.read_register("rsi"))
        print(f"[TRACE] {self.func}(rdi=0x{rdi:x}, rsi=0x{rsi:x})")
        return False  # Don't stop, just log

for f in ["connect", "send", "recv", "write", "execve", "mprotect"]:
    try:
        MalwareTracer(f)
    except Exception:
        pass

gdb.execute("run")
```

## pwndbg-specific Commands

| Command | Purpose |
|---------|---------|
| `context` | Show full context (regs, code, stack, bt) |
| `telescope ADDR N` | Dereference pointer chains |
| `vmmap` | Virtual memory map with permissions |
| `procinfo` | Process details |
| `got` | GOT table entries |
| `plt` | PLT entries |
| `canary` | Show stack canary value |
| `retaddr` | Return addresses on stack |
| `search --string STR` | Search memory for string |
| `search --qword VAL` | Search memory for value |
| `patch ADDR 'nop; nop'` | Patch instructions |
| `heap` | Heap chunk listing (glibc) |
| `bins` | Arena bin contents |
| `vis_heap_chunks` | Visual heap layout |
| `xinfo ADDR` | Offset info for address |
| `cymbol` | Define custom C structs |
| `entry` | Run to entry point |

## GEF-specific Commands

| Command | Purpose |
|---------|---------|
| `gef config` | Configure GEF |
| `checksec` | Binary security features |
| `elf-info` | ELF header details |
| `xfiles` | List all loaded libraries |
| `scan` | Search for patterns |
| `format-string-helper` | Format string exploit aid |
| `pattern create N` | De Bruijn pattern for offset finding |
| `pattern offset VAL` | Find offset from pattern value |

## Resources

| File | When to load |
|------|--------------|
| [references/malware-debugging.md](references/malware-debugging.md) | Step-by-step malware debugging workflows |
| [references/scripting.md](references/scripting.md) | GDB Python API patterns for automation |
