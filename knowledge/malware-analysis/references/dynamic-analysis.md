# Dynamic Analysis Reference

GDB, x64dbg, strace, and other dynamic analysis workflows. Load this reference when the user explicitly requests dynamic analysis in an isolated lab environment.

## Prerequisites

- **Isolated lab only** — disposable VM with no real credentials, not connected to production networks
- Snapshot the VM before analysis — restore after each run
- Use network simulation (fakenet-ng, inetsim) to capture traffic without real connectivity

## GDB — Linux / WSL

GDB is the primary dynamic analysis tool for ELF binaries on Linux and WSL. Enhanced with `pwndbg` or `gef` for malware analysis.

### Setup

```bash
# Install gdb
sudo apt-get install -y gdb

# Install pwndbg (recommended for malware work)
git clone https://github.com/pwndbg/pwndbg ~/pwndbg
cd ~/pwndbg && ./setup.sh

# OR install gef
# bash -c "$(curl -fsSL https://gef.blah.cat/sh)"

# Verify
gdb --version
```

### Malware analysis workflow with GDB

```bash
# Start with the sample
gdb -q ./sample.elf

# Set breakpoints on key operations BEFORE running
(gdb) break main
(gdb) break connect           # Network connections
(gdb) break send              # Data transmission
(gdb) break recv              # Data reception
(gdb) break execve            # Process execution
(gdb) break fork              # Process creation
(gdb) break ptrace            # Anti-debug (catch it!)
(gdb) break mprotect          # Memory permission changes (unpacking)
(gdb) break dlopen            # Dynamic library loading

# Run the sample
(gdb) run

# When breakpoint hits:
(gdb) bt                      # Backtrace — see call chain
(gdb) info registers          # Register state
(gdb) x/20x $rsp              # Examine stack (20 hex words)
(gdb) x/s $rdi                # Print string argument (first arg in x64)
(gdb) x/s $rsi                # Second argument
(gdb) info proc mappings      # Memory map
(gdb) continue                # Resume to next breakpoint
```

### Anti-debug bypass with GDB

Many malware use `ptrace(PTRACE_TRACEME)` to detect debuggers:

```bash
# Option 1: Catch and neutralize
(gdb) catch syscall ptrace
(gdb) run
# When ptrace caught:
(gdb) set $rax = 0            # Fake success return
(gdb) continue

# Option 2: LD_PRELOAD with fake ptrace (prepare in advance)
# Create a small .so that returns 0 for ptrace
```

### Dumping decrypted memory

```bash
# When execution reaches post-decryption point:
(gdb) info proc mappings
# Find the region with the decrypted payload (RWX or recently mprotect'd)
(gdb) dump binary memory dump.bin 0x7f0000 0x7f1000
```

### Scripting GDB for automation

```python
# Save as gdb_trace.py, run with: gdb -q -x gdb_trace.py ./sample
import gdb

class NetworkTrace(gdb.Breakpoint):
    def __init__(self, func):
        super().__init__(func, gdb.BP_BREAKPOINT)
        self.func = func

    def stop(self):
        frame = gdb.selected_frame()
        print(f"[TRACE] {self.func} called")
        # Print first 3 args (x64 ABI: rdi, rsi, rdx)
        for reg in ["rdi", "rsi", "rdx"]:
            val = frame.read_register(reg)
            print(f"  {reg} = {val}")
        return False  # Don't stop, just log

for func in ["connect", "send", "recv", "write"]:
    try:
        NetworkTrace(func)
    except Exception:
        pass

gdb.execute("run")
```

## x64dbg — Windows

x64dbg is the primary Windows debugger for malware analysis. See the `x64dbg` skill for detailed command reference.

### Malware analysis strategy

1. **Initial breakpoints** — set before running:
   - `bp VirtualAlloc` / `bp VirtualAllocEx` — memory allocation (unpacking, injection)
   - `bp VirtualProtect` — permission changes (RWX = shellcode about to execute)
   - `bp CreateRemoteThread` / `bp NtCreateThreadEx` — injection
   - `bp WriteProcessMemory` — injection data write
   - `bp InternetOpenA` / `bp WinHttpOpen` — first network call
   - `bp CryptDecrypt` / `bp BCryptDecrypt` — decryption

2. **Unpack workflow:**
   - Run with breakpoint on `VirtualProtect` (looking for PAGE_EXECUTE_READWRITE)
   - When hit: check the buffer being changed — this is likely the unpacked code
   - Step through until the "tail jump" (indirect JMP/CALL to unpacked code)
   - At OEP: dump process with Scylla → fix imports → save clean sample

3. **C2 extraction at runtime:**
   - Break on network APIs
   - When hit: inspect stack/registers for URL/IP strings
   - Follow in dump to see full C2 configuration

4. **Anti-debug bypass:**
   - Install ScyllaHide plugin (patches common anti-debug techniques automatically)
   - Or manually: patch `PEB.BeingDebugged` to 0, handle `NtQueryInformationProcess`

## strace / ltrace — Linux

### System call tracing

```bash
# Trace all syscalls, follow forks
strace -f -o syscalls.log ./sample.elf

# Focus on network syscalls
strace -f -e trace=network -o net_trace.log ./sample.elf

# Focus on file operations
strace -f -e trace=file -o file_trace.log ./sample.elf

# Focus on process operations
strace -f -e trace=process -o proc_trace.log ./sample.elf
```

### Library call tracing

```bash
# Trace library calls
ltrace -f -o ltrace.log ./sample.elf

# Filter for interesting functions
ltrace -f -e 'connect+send+recv+system+exec*+fopen+mmap+mprotect' ./sample.elf
```

### Post-analysis grep patterns

```bash
# Find C2 connections
grep -E 'connect|sendto|sendmsg' syscalls.log | grep -v ENOENT
# Find file drops
grep -E 'open|creat|write' syscalls.log | grep -v "/dev/\|/proc/"
# Find executed commands
grep -E 'execve|clone|fork' syscalls.log
```

## Process Monitor (procmon) — Windows

1. Start procmon **before** running the sample
2. Set filters: Process Name is `sample.exe`
3. After execution, check:
   - **File activity:** created/modified files (drops, configs, persistence)
   - **Registry activity:** autorun keys, service creation, config storage
   - **Network activity:** connections, DNS queries
   - **Process activity:** child processes, injection targets

Key registry paths to monitor:
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKLM\SYSTEM\CurrentControlSet\Services`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders`

## Network interception

### fakenet-ng (Windows/Linux)

```bash
# Install
pip install fakenet-ng

# Run (intercepts all DNS/HTTP/HTTPS/TCP/UDP)
sudo fakenet
# Then run the sample — all traffic is captured and logged
```

### inetsim (Linux)

```bash
sudo apt-get install inetsim
sudo inetsim
# Simulates DNS, HTTP, HTTPS, FTP, SMTP, IRC, and more
# Configure in /etc/inetsim/inetsim.conf
```

### Manual packet capture

```bash
# Capture all traffic from the sample's network namespace
tshark -i eth0 -w capture.pcap

# Filter for specific protocols after capture
tshark -r capture.pcap -Y "http || dns || tcp.port==443"
```

## Memory forensics with Volatility 3

For analyzing memory dumps from dynamic analysis:

```bash
# Install
pip install volatility3

# Identify OS profile
vol -f memory.dmp windows.info

# List processes
vol -f memory.dmp windows.pslist
vol -f memory.dmp windows.pstree

# Find injected code
vol -f memory.dmp windows.malfind

# Extract process memory
vol -f memory.dmp windows.memmap --pid <PID> --dump

# Network connections
vol -f memory.dmp windows.netscan
```
