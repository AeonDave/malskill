# WinDbg — Kernel Debugging & Driver/Rootkit Analysis

## Kernel Debug Setup

### Local Kernel Debugging (same machine)

```powershell
# Enable local kernel debugging (requires elevation)
bcdedit /debug on
# Restart required. In WinDbg:
# File → Kernel Debug → Local
# Note: limited — can't break execution, only inspect
```

### Network (recommended for VMs)

```powershell
# On target VM:
bcdedit /debug on
bcdedit /dbgsettings net hostip:192.168.1.100 port:50000
# Note the KEY it outputs

# On host WinDbg:
# File → Kernel Debug → Net → port: 50000, key: <from above>
# Or: windbg -k net:port=50000,key=xxx.xxx.xxx.xxx
```

### Serial / Pipe (VMware/VirtualBox)

```powershell
# Target:
bcdedit /dbgsettings serial debugport:1 baudrate:115200

# Host (WinDbg):
File → Kernel Debug → COM → port: \\.\pipe\com1, baud: 115200
# VMware: add serial port → named pipe \\.\pipe\com1
```

## First Steps in a Kernel Debug Session

```
# After connecting:
.symfix                         # Set Microsoft symbol server
.reload /f                      # Load symbols
!analyze -v                     # If crash dump: auto-analyze
lm                              # List loaded modules
!process 0 0                    # All processes (if system running)
```

## Driver/Module Analysis

### Enumerate drivers and modules

```
# All kernel modules
lm t n                           # List by type, sorted by name
lm f                             # Full paths

# Find suspicious/unsigned drivers
!for_each_module "!chkimg -d @#Base @#End @#ModuleName"  # Check image integrity

# Specific module info
lm m <name>                      # Module details
lmvm <name>                      # Verbose module info

# List DriverObject structures
!object \Driver                  # All driver objects
!drvobj DriverName 7             # Detailed: name, dispatch table
```

### Inspect driver dispatch table

```
# Get DRIVER_OBJECT address
dt nt!_DRIVER_OBJECT <address>

# MajorFunction table (28 IRP_MJ_* pointers starting at +0x70)
dps <DriverObject+0x70> L1C      # 28 entries = IRP handlers
# Normal: all point to ntoskrnl or the driver's own module
# Hook detected: pointer outside driver's address range

# Identify which module each handler belongs to
ln <handler_address>             # Shows nearest symbol
```

### SSDT (System Service Descriptor Table) hook detection

```
# View SSDT entries
dps nt!KiServiceTable L100       # First 256 syscall handlers

# Automated hook check: all entries should be within ntoskrnl range
# Get ntoskrnl range first:
lm m nt
# Note: Start address and size

# Check for hooks (entries outside ntoskrnl range):
.for (r $t0 = 0; @$t0 < 0x100; r $t0 = @$t0 + 1) {
    r $t1 = dwo(nt!KiServiceTable + @$t0 * 4)   # 32-bit: 4 bytes, 64-bit: different
    ln @$t1
}
# Any symbol not in nt!* = hook
```

### Detect DKOM (Direct Kernel Object Manipulation)

```
# Process hiding: EPROCESS.ActiveProcessLinks manipulation
# Normal walk:
!process 0 0

# Manual EPROCESS walk (bypass DKOM):
dt nt!_EPROCESS                           # Check offsets
dt nt!_LIST_ENTRY                         # ActiveProcessLinks offset

# Walk manually:
r $t0 = @@c++(&nt!PsActiveProcessHead)   # List head
.for (r $t1 = poi(@$t0); @$t1 != @$t0; r $t1 = poi(@$t1)) {
    dt nt!_EPROCESS @$t1-0x2f0            # Adjust offset for OS version
    .printf "%p\n", @$t1
}
```

### Object manager hooks (DKOM callbacks)

```
# List registered callbacks
!object \Callback                         # Enumerate callbacks

# Process creation callbacks (rootkits often hook these)
dt nt!_EX_CALLBACK_ROUTINE_BLOCK         # Check each callback
```

## Memory Analysis

### Pool memory and driver allocations

```
# Find nonpaged pool allocations with a tag
!pool 0 NonPagedPool                     # Show all nonpaged pool
!poolfind "Drvr" 0                       # Find pools with tag "Drvr"
!poolused                                # Pool usage summary

# Scan for specific pool tag (find rootkit allocations)
!poolused 2 Drvr                         # Tag "Drvr" in nonpaged pool
```

### Virtual memory inspection

```
# All VADs for a process
.process /p <EPROCESS>
!vad                                     # Virtual Address Descriptor tree

# Check for hidden/injected regions
!vad flags                               # Show permissions
# Suspicious: EXECUTE_READWRITE, no file-backed, outside known modules
```

### Direct physical memory access

```
!db <physical_address>                   # Read physical memory
!dc <physical_address>                   # Display physical as DWORDs
```

## Interrupt Descriptor Table (IDT) Analysis

```
# Current IDT
!idt                                     # Full IDT dump
!idt -a                                  # All IDT entries with symbols

# Manual IDT read
r idtr                                   # IDT register
dq @idtr L100                           # Raw IDT entries
# Hooks: entries pointing outside ntoskrnl = suspicious
```

## Network/System State

```
# Network connections (kernel view)
!ndiskd.netadapter                       # Network adapters
!ndiskd.vc                               # Virtual connections

# Kernel timer analysis (useful for rootkit timers)
!timer                                   # All kernel timers
# Suspicious: timer callbacks outside known drivers
```

## TTD (Time Travel Debugging)

TTD records full execution trace → replay forwards/backwards without re-running.
User-mode via WinDbg Preview (File → Record Process). Kernel-mode via Insider Preview.

### User-mode malware analysis workflow

```
# Record:
# WinDbg Preview → File → Record Process → select malware.exe
# Let it run → produces malware.exe.run + malware.exe.idx

# Open trace: File → Open Trace File → .run file
```

```
# Key LINQ queries (dx = Data Model eXpression language):

# Find all LoadLibrary calls (DLL injection, C2 staging)
dx @$cursession.TTD.Calls("kernelbase!LoadLibraryExW").Select(c => c.Parameters[0])

# Find all VirtualAlloc calls + return values (shellcode allocation)
dx @$cursession.TTD.Calls("kernelbase!VirtualAlloc").Select(c => new { Args=c.Parameters, Ret=c.ReturnValue })

# Find WriteProcessMemory (process injection)
dx @$cursession.TTD.Calls("kernelbase!WriteProcessMemory").Select(c => c.Parameters)

# Find CreateRemoteThread (thread injection)
dx @$cursession.TTD.Calls("kernelbase!CreateRemoteThread")

# Find all network calls
dx @$cursession.TTD.Calls("ws2_32!connect").Select(c => c.Parameters)
dx @$cursession.TTD.Calls("wininet!InternetConnectW")

# Count calls to a suspicious API
dx @$cursession.TTD.Calls("ntdll!NtAllocateVirtualMemory").Count()

# Find exact moment when specific memory was written
# Set memory breakpoint, then reverse-execute to previous write:
ba w8 <suspicious_addr>
g-                        # Step backwards to last write

# Navigate to a specific recorded time position:
!tt 0:0                   # Beginning of trace
!tt 100%                  # End of trace
!tt <position>            # Jump to timestamp (e.g., !tt 4B:23)

# Backward step to find root cause:
p-                        # Step back one instruction
g-                        # Run backwards to last event/breakpoint
```

### Kernel TTD (requires Windows Insider + Kernel TTD preview)

```
# Settings → Kernel Debugging → Record with TTD

# After recording:
dx @$cursession.TTD.Calls("nt!ExAllocatePoolWithTag")
dx @$cursession.TTD.Calls("nt!MmMapLockedPages").Count()
```

### TTD for unpacking

```
# Record malware execution from start
# Query for RWX allocations:
dx @$cursession.TTD.Calls("kernelbase!VirtualAlloc")
    .Where(c => ((int)c.Parameters[3] & 0x40) != 0)   # PAGE_EXECUTE_READWRITE

# After identifying allocation, jump to time of RWX:
!tt <time_from_above>
# Then find when execution enters that region (set exec BP, run):
bp <alloc_return_value>
g
# Now at OEP of unpacked code
```

## Live Kernel Commands Quick Reference

| Goal | Command |
|------|---------|
| All processes | `!process 0 0` |
| Switch to process context | `.process /i <EPROCESS>` |
| All threads | `!thread` |
| All drivers | `lm t n` |
| Driver by name | `!drvobj DriverName 7` |
| Object by path | `!object \Device\mydevice` |
| Symbolic links | `!object \??\` |
| Named pipes | `!object \Device\NamedPipe` |
| Registry handles | `!reg querykey \Registry\Machine\System` |
| Loaded DLLs | `!peb → .peb → lm` |
| Handle table | `!handle 0 7 <EPROCESS>` |
