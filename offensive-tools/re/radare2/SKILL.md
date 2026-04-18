---
name: radare2
description: "CLI reverse engineering framework with disassembly, decompilation (r2ghidra/r2dec), debugging, ESIL emulation, scripting, and binary patching. Use when analyzing binaries headlessly, scripting RE tasks via r2pipe, patching executables, diffing firmware, emulating code, or working in resource-constrained/headless environments."
license: MIT
compatibility: "C; Linux/macOS/Windows; apt install radare2 or github.com/radareorg/radare2"
metadata:
  author: AeonDave
  version: "1.0"
---

# Radare2

CLI RE framework — disassemble, decompile, debug, emulate, patch, and script binary analysis.

## Installation

```bash
# Linux/macOS
git clone https://github.com/radareorg/radare2 && cd radare2 && sys/install.sh
# OR: apt install radare2

# Windows: download from https://github.com/radareorg/radare2/releases

# Decompiler plugins
r2pm -ci r2ghidra       # Ghidra decompiler in r2
r2pm -ci r2dec          # Alternative decompiler
```

## Quick Start

```bash
# Open binary (read-only)
r2 ./binary

# Analyze all (auto-analysis)
> aaa

# List functions
> afl

# Disassemble function
> pdf @ main

# Decompile function (requires r2ghidra or r2dec)
> pdg @ main

# Print strings
> iz

# Quit
> q
```

## Essential Commands

### Analysis and Navigation

| Command | Purpose |
|---------|---------|
| `aaa` | Full auto-analysis |
| `aaaa` | Experimental deep analysis |
| `afl` | List all functions |
| `afn NAME ADDR` | Rename function |
| `s ADDR` | Seek to address |
| `pdf @ FUNC` | Disassemble function |
| `pdg @ FUNC` | Decompile function (r2ghidra) |
| `pdd @ FUNC` | Decompile function (r2dec) |
| `V` | Visual mode |
| `VV` | Visual graph mode |
| `p` | Cycle view in visual mode |

### Information

| Command | Purpose |
|---------|---------|
| `i` | File info (format, arch, bits) |
| `iS` | List sections |
| `ii` | List imports |
| `iE` | List exports |
| `iz` | Strings in data sections |
| `izz` | Strings in whole binary |
| `ir` | Relocations |
| `il` | Libraries (linked) |
| `iH` | Binary header info |
| `ie` | Entrypoints |

### Searching

| Command | Purpose |
|---------|---------|
| `/ STRING` | Search string |
| `/x HEXBYTES` | Search hex pattern |
| `/R OPCODE` | Search ROP gadgets |
| `/r ADDR` | Find references to address |
| `axt ADDR` | Cross-references to address |
| `axf ADDR` | Cross-references from address |

### Debugging

| Command | Purpose |
|---------|---------|
| `ood [args]` | Reopen in debug mode |
| `db ADDR` | Set breakpoint |
| `dc` | Continue |
| `ds` | Step into |
| `dso` | Step over |
| `dr` | Show registers |
| `dr rax=0` | Set register |
| `dm` | Memory map |
| `dmi libc` | Symbols in module |
| `dtf FUNC FMT` | Trace function with format |
| `dts+` | Create trace session |
| `dk %SIGNAL` | Send signal |

### Memory and Patching

| Command | Purpose |
|---------|---------|
| `px N @ ADDR` | Hex dump N bytes |
| `ps @ ADDR` | Print string |
| `pf FMT @ ADDR` | Print formatted (struct) |
| `wa INSTR @ ADDR` | Write assembly |
| `wx BYTES @ ADDR` | Write hex bytes |
| `wt FILE SIZE @ ADDR` | Write to file |

### ESIL Emulation

| Command | Purpose |
|---------|---------|
| `aei` | Initialize ESIL VM |
| `aeim` | Initialize ESIL memory/stack |
| `aeip` | Set ESIL PC to entrypoint |
| `aes` | Step one instruction in ESIL |
| `aeso` | Step over in ESIL |
| `aer` | Show ESIL registers |
| `ae EXPR` | Evaluate ESIL expression |

## Common Workflows

### Quick static triage

```
r2 malware.exe
> aaa
> afl~main        # Grep for main in function list
> iz~http          # Grep strings for http
> ii~Crypt         # Grep imports for crypto
> pdf @ sym.main
> pdg @ sym.main   # Decompile
```

### Binary diffing

```bash
# Compare two versions of a binary
radiff2 -g main original.exe patched.exe | xdot -
# Or inside r2:
r2 -m 0x10000 original.exe
> o patched.exe 0x20000
> c 256 @ 0x10000
```

### Malware debugging

```bash
r2 -d malware.exe
> aaa
> db sym.main
> dc                # Continue to main
> db 0x401234       # Break at interesting address
> dc
> dr                # Inspect registers
> px 64 @ rsp       # Stack dump
> dm                # Check memory map for injected regions
```

### Patch binary

```bash
r2 -w ./binary
> s 0x401234
> pd 3              # Print 3 instructions to verify location
> wa nop; nop; nop  # Patch with NOPs
> wa jmp 0x401300   # Or redirect flow
> wt patched.bin    # Save to new file
> q
```

### r2pipe scripting (Python)

```python
import r2pipe

r2 = r2pipe.open('./malware')
r2.cmd('aaa')

# Get function list as JSON
funcs = r2.cmdj('aflj')
for f in funcs:
    print(f"{f['offset']:#x}: {f['name']} ({f['size']} bytes)")

# Get strings and filter
strings = r2.cmdj('izj')
for s in strings:
    if any(kw in s['string'].lower() for kw in ['http', 'exec', 'cmd']):
        print(f"  {s['vaddr']:#x}: {s['string']}")

# Disassemble function as JSON
main_ops = r2.cmdj('pdfj @ main')
for op in main_ops.get('ops', []):
    if 'call' in op.get('type', ''):
        print(f"  CALL at {op['offset']:#x}: {op.get('disasm', '')}")

r2.quit()
```

### Project persistence

```
r2 -p myproject ./binary
> aaa
> Ps myproject     # Save project
> q
# Later:
r2 -p myproject     # Reopen with all analysis intact
```

## Resources

| File | When to load |
|------|--------------|
| [references/r2pipe-recipes.md](references/r2pipe-recipes.md) | r2pipe Python scripting recipes |
| [references/debugging-guide.md](references/debugging-guide.md) | Debugging and ESIL emulation workflows |
