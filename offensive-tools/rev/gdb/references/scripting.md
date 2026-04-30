# GDB — Python Scripting Reference

## Basics

```python
# Run script: gdb -q -x script.py ./binary
# Or load in session: source script.py
import gdb

# Execute GDB command
gdb.execute("run", to_string=False)
output = gdb.execute("info registers", to_string=True)

# Parse output
gdb.execute("break main")
gdb.execute("continue")
```

## Breakpoints API

```python
class MyBreakpoint(gdb.Breakpoint):
    def __init__(self, location, condition=None):
        super().__init__(location, gdb.BP_BREAKPOINT)
        self.silent = True
        if condition:
            self.condition = condition

    def stop(self):
        """Return True to stop, False to continue."""
        frame = gdb.selected_frame()
        # Access registers
        rdi = int(frame.read_register("rdi"))
        rsi = int(frame.read_register("rsi"))
        print(f"[BP] {self.location}: rdi={rdi:#x} rsi={rsi:#x}")
        return False  # Non-stop: log and continue

# Usage
MyBreakpoint("connect")
MyBreakpoint("send", condition="$rdx > 100")  # Only if len > 100

gdb.execute("run")
```

### Watchpoints (data breakpoints)

```python
# Break when memory address is written
class WatchBreakpoint(gdb.Breakpoint):
    def __init__(self, expr):
        super().__init__(expr, gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE)
        self.silent = True

    def stop(self):
        frame = gdb.selected_frame()
        print(f"[WATCH] Value at {self.expression} was written")
        print(f"  PC: {frame.pc():#x}")
        return True  # Stop here

WatchBreakpoint("*(int*)0x404040")
```

### Finish breakpoints (catch return value)

```python
class ReturnBreakpoint(gdb.FinishBreakpoint):
    """Break when function returns, log return value."""
    def __init__(self, func_name):
        self.func_name = func_name
        super().__init__(internal=True)

    def out_of_scope(self):
        pass

    def stop(self):
        rax = int(gdb.selected_frame().read_register("rax"))
        print(f"[RET] {self.func_name} returned {rax:#x}")
        return False

class CallBreakpoint(gdb.Breakpoint):
    def __init__(self, func_name):
        super().__init__(func_name)
        self.func_name = func_name
        self.silent = True

    def stop(self):
        # Install finish breakpoint to catch return
        ReturnBreakpoint(self.func_name)
        return False

CallBreakpoint("malloc")
CallBreakpoint("VirtualAlloc")
```

## Frame and Register Access

```python
frame = gdb.selected_frame()

# Read registers
rax = int(frame.read_register("rax"))
rip = int(frame.read_register("rip"))
rsp = int(frame.read_register("rsp"))

# Modify registers
gdb.execute("set $rax = 0")
gdb.execute(f"set $rip = {0x401234:#x}")

# Read memory
addr = 0x401000
mem = gdb.selected_inferior().read_memory(addr, 64)
# mem is memoryview, convert to bytes:
data = bytes(mem)

# Write memory
gdb.selected_inferior().write_memory(addr, b'\x90\x90\x90')

# Read string at address
def read_string(addr, max_len=256):
    try:
        mem = bytes(gdb.selected_inferior().read_memory(addr, max_len))
        null = mem.find(b'\x00')
        return mem[:null].decode('utf-8', errors='replace') if null != -1 else mem[:max_len]
    except Exception:
        return "<unreadable>"
```

## Backtrace and Frames

```python
# Current call stack
for frame in gdb.selected_thread().unwind():
    print(f"  #{frame.level()} {frame.pc():#x} {frame.name() or '?'}")

# Specific frame
frame = gdb.selected_frame()
older = frame.older()   # Caller frame
newer = frame.newer()   # Callee frame

# Local variables
try:
    block = frame.block()
    for sym in block:
        if sym.is_variable:
            try:
                val = sym.value(frame)
                print(f"  {sym.name} = {val}")
            except Exception:
                pass
except Exception:
    pass
```

## Inferior and Process Management

```python
inf = gdb.selected_inferior()

# Process ID
print(f"PID: {inf.pid}")

# Memory map
for mapping in inf.architecture().registers():
    pass  # Not direct — use info proc mappings

# Read multiple memory regions
def dump_region(start, size, filename):
    data = bytes(inf.read_memory(start, size))
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Dumped {size} bytes to {filename}")
```

## Event Handlers

```python
# Stop event (any breakpoint/stop)
def on_stop(event):
    if isinstance(event, gdb.BreakpointEvent):
        for bp in event.breakpoints:
            print(f"[STOP] BP {bp.number} at {bp.location}")
    elif isinstance(event, gdb.SignalEvent):
        print(f"[SIGNAL] {event.stop_signal}")

gdb.events.stop.connect(on_stop)

# Exit event
def on_exit(event):
    print(f"[EXIT] Process exited with code {event.exit_code if hasattr(event, 'exit_code') else '?'}")

gdb.events.exited.connect(on_exit)

# New object file loaded
def on_new_objfile(event):
    if event.new_objfile:
        print(f"[LOAD] {event.new_objfile.filename}")

gdb.events.new_objfile.connect(on_new_objfile)
```

## Complete Malware Tracing Script

```python
#!/usr/bin/env python3
# GDB script: comprehensive malware tracer
# Usage: gdb -q -x this_script.py ./malware

import gdb, json, time

LOG_FILE = "/tmp/malware_trace.json"
events = []

def log(event_type, data):
    events.append({"time": time.time(), "type": event_type, **data})

# Anti-debug bypass
class PtracePatch(gdb.Breakpoint):
    def __init__(self):
        super().__init__("ptrace", type=gdb.BP_CATCHPOINT)
        self.silent = True
    def stop(self):
        gdb.execute("set $rax = 0")
        return False

# Network tracer
class ConnectTracer(gdb.Breakpoint):
    def __init__(self):
        super().__init__("connect")
        self.silent = True
    def stop(self):
        frame = gdb.selected_frame()
        sa_ptr = int(frame.read_register("rsi"))
        try:
            sa = bytes(gdb.selected_inferior().read_memory(sa_ptr, 16))
            family = int.from_bytes(sa[0:2], 'little')
            if family == 2:  # AF_INET
                port = int.from_bytes(sa[2:4], 'big')
                ip = '.'.join(str(b) for b in sa[4:8])
                log("connect", {"ip": ip, "port": port})
        except Exception:
            pass
        return False

class SendTracer(gdb.Breakpoint):
    def __init__(self):
        super().__init__("send")
        self.silent = True
    def stop(self):
        frame = gdb.selected_frame()
        buf = int(frame.read_register("rsi"))
        length = int(frame.read_register("rdx"))
        try:
            data = bytes(gdb.selected_inferior().read_memory(buf, min(length, 256)))
            log("send", {"length": length, "data": data.hex(), "printable": data[:64].decode('utf-8', errors='replace')})
        except Exception:
            pass
        return False

class ExecTracer(gdb.Breakpoint):
    def __init__(self):
        super().__init__("execve")
        self.silent = True
    def stop(self):
        frame = gdb.selected_frame()
        path_ptr = int(frame.read_register("rdi"))
        try:
            path = bytes(gdb.selected_inferior().read_memory(path_ptr, 256))
            path = path[:path.find(b'\x00')].decode()
            log("execve", {"path": path})
        except Exception:
            pass
        return False

def on_exit(event):
    with open(LOG_FILE, 'w') as f:
        json.dump(events, f, indent=2)
    print(f"\n[*] Trace log: {LOG_FILE} ({len(events)} events)")

# Install hooks
gdb.events.exited.connect(on_exit)
try:
    PtracePatch()
    ConnectTracer()
    SendTracer()
    ExecTracer()
except Exception as e:
    print(f"[!] Setup error: {e}")

gdb.execute("set pagination off")
gdb.execute("run")
```

## Useful .gdbinit Snippets

```gdb
# ~/.gdbinit
set disassembly-flavor intel       # Intel syntax
set pagination off                  # No "press enter" prompts
set logging on                      # Log to gdb.txt
set confirm off                     # No confirmations
set follow-fork-mode child          # Follow child process on fork

# Load pwndbg or GEF automatically
# source ~/pwndbg/gdbinit.py       # pwndbg
# source ~/.gdbinit-gef.py          # GEF
```
