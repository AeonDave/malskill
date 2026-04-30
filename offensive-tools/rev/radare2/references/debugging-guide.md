# Radare2 — Debugging & ESIL Emulation

## Debug Mode

```bash
# Open in debug mode
r2 -d ./binary                  # Spawn process
r2 -d -p myproject ./binary     # Spawn + save project
r2 -d pid:1234                  # Attach to PID
r2 -d gdb://192.168.1.100:1234  # Remote GDB stub
```

## Debug Commands Reference

### Control flow

| Command | Purpose |
|---------|---------|
| `db ADDR` | Set breakpoint |
| `db sym.main` | Breakpoint on symbol |
| `dbl` | List breakpoints |
| `dbc ADDR CMD` | Breakpoint with command |
| `dbx ADDR` | Delete breakpoint |
| `dc` | Continue |
| `ds` | Step into (instruction) |
| `dso` | Step over (instruction) |
| `dsu ADDR` | Step until address |
| `dss` | Step skip (don't enter calls) |
| `dk 9` | Send SIGKILL |
| `drr` | Show registers (formatted) |
| `dr rax=0` | Set register |

### Memory inspection

| Command | Purpose |
|---------|---------|
| `dm` | List memory maps |
| `dmi libc` | Imports of a module |
| `px 64 @ rsp` | Hex dump 64 bytes at RSP |
| `ps @ rdi` | Print string at RDI |
| `pf <fmt> @ addr` | Print formatted struct |
| `pxj 32 @ rdi` | JSON hex dump |

### Watchpoints

```
# Hardware watchpoint: break on memory write
dr? rax          # Check register value first
dbw 0x404040     # Watchpoint on write to address
```

## Malware Debugging Workflows

### Find and analyze anti-debug (ptrace)

```
# Set catchpoint for ptrace syscall
r2 -d malware
> aaa
> dcs ptrace       # Continue until ptrace syscall
> drr              # Check return value (rax)
> dr rax=0         # Patch return value to 0 (success)
> dc               # Continue
```

### Unpack in memory (find OEP)

```
# Strategy: break on mprotect/mmap when RWX memory is created
r2 -d packed_malware
> aaa
> dcs mprotect      # Break on every mprotect call
> dc
# When hit, check rdx (flags):
> dr rdx            # 7 = PROT_READ|PROT_WRITE|PROT_EXEC (RWX)
# When RWX mprotect found:
> db [rdi + rsi]    # Break at end of allocated region (jump target area)
> dc
# Usually lands at OEP. Dump:
> wtf unpacked.bin [rdi] @ rdi
```

### Dump decrypted region

```
# After malware decrypts shellcode/payload:
> db 0x12345678     # Break after decryption
> dc
# Now dump the decrypted region:
> dm                # Find the RWX region
> wtf decrypted.bin SIZE @ ADDR

# Or dump all executable regions:
> dm~rwx            # Filter writable+exec regions
```

### Trace API calls (function trace)

```
# Trace with format string at each call
r2 -d malware
> doo               # Reopen in debug mode with analysis
> dtf connect rdi:ip rsi:len  # Trace 'connect', show rdi and rsi

# Simple trace of all calls:
> e dbg.trace=true
> dc
# All instructions traced to output
```

### Dynamic call tracing via commands

```
# Set breakpoint + auto-command (log + continue)
> db sym.imp.connect
> dbc sym.imp.connect "dr rdi; dc"   # Print rdi, then continue
> dc

# More verbose: print registers on each call
> dbc sym.imp.send "drr; dc"
```

## ESIL Emulation

ESIL (Evaluable Strings Intermediate Language) — CPU-agnostic emulation without running the binary.

### Basic ESIL emulation

```
r2 ./binary
> aaa
> aei           # Initialize ESIL VM
> aeim           # Initialize memory and stack
> aeip           # Set PC to current position (or use: s 0x401000; aeip)
> aes            # Step one instruction
> aeso           # Step over (skip call)
> aer            # Show all ESIL registers
> aer rax=0x41  # Set ESIL register
> aec            # Continue emulation until breakpoint/invalid
```

### Emulate a function to extract output

```python
# r2pipe + ESIL to emulate decryption function
import r2pipe

r2 = r2pipe.open('malware.exe')
r2.cmd('aaa')
r2.cmd('e io.cache = true')    # Don't modify actual file

# Initialize ESIL
r2.cmd('aei')
r2.cmd('aeim')

# Seek to decrypt function
r2.cmd('s sym.decrypt')
r2.cmd('aeip')                  # Set ESIL PC here

# Set up arguments (e.g., pointer to encrypted buffer)
r2.cmd('aer rdi = 0x404000')   # Pointer to data
r2.cmd('aer rsi = 0x20')       # Length

# Emulate until ret
r2.cmd('aesu 0')               # Step until return (addr 0 = ret)

# Read result
result_ptr = int(r2.cmd('aer rax'), 16)
decrypted = r2.cmd(f'ps @ {result_ptr:#x}')
print(f"Decrypted: {decrypted}")

r2.quit()
```

### ESIL tracing for taint analysis

```
> aef sym.main   # Emulate entire function
# This traces execution and marks tainted data
# Useful for understanding data flow without running malware
```

### Emulate shellcode

```bash
# Load raw shellcode
r2 -b 64 -m 0x10000 shellcode.bin
> aaa
> e asm.bits=64
> aei
> aeim 0x10000 0x1000  # Init stack at 0x10000
> s 0                   # Seek to start
> aeip
> aes                   # Step through
> aer                   # Check registers
```

## ESIL Hooks (Callbacks on Instructions)

```
# Break ESIL on specific memory access
> aebs 0x404040   # Break on read/write to 0x404040
> aec             # Emulate until breakpoint
```

## Remote Debugging

```bash
# GDB stub (e.g., QEMU, OpenOCD, gdbserver)
r2 -d gdb://localhost:1234

# WinDbg stub (Windows kernel via serial/pipe)
r2 -d windbg://\\.\pipe\com_1

# LLDB / macOS
r2 -d lldb://com.example.app   # iOS app bundle ID (via iProxy)
```

## Visual Debugging Mode

```
r2 -d ./binary
> db main
> dc
> V!                # Visual! (best for debugging)
# In V! mode:
#   p = step (over)
#   s = step into
#   c = continue
#   ? = help
#   q = quit visual
```
