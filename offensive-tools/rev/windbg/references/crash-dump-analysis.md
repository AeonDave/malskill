# WinDbg — Crash Dump Analysis & BSOD Triage

## Dump Types

| Type | Size | Content | When Used |
|------|------|---------|-----------|
| Complete memory dump | Full RAM | All physical memory | Full analysis, rare |
| Kernel memory dump | ~50-100MB | Kernel + driver pages | Standard BSOD analysis |
| Small memory dump (minidump) | 256KB | Exception + stack | Quick triage |
| Active memory dump | ~400MB | Non-hardware pages | Hyper-V environments |

```powershell
# Configure dump type:
# System Properties → Advanced → Startup and Recovery → Write debugging information
# Or:
Set-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl -Name CrashDumpEnabled -Value 2
# 0=none, 1=complete, 2=kernel, 3=small, 7=automatic
```

## Load and First Commands

```
# Open dump:
# File → Open Crash Dump → *.dmp

# ALWAYS start with:
!analyze -v              # Automated root-cause analysis
.ecxr                    # Switch to exception context record
k                        # Stack trace at crash point
r                        # Registers at crash
```

## !analyze -v Output Interpretation

```
BUGCHECK_STR: 0x3B           # Bug check code
DEFAULT_BUCKET_ID: WIN8_DRIVER_FAULT
FOLLOWUP_NAME: MachineOwner
MODULE_NAME: <driver_name>   # Faulting driver
IMAGE_NAME: driver.sys       # Faulting image
FAILURE_BUCKET_ID: X64_0x3B_<address>

# Key fields:
STACK_TEXT:                  # Call stack — start here
FAULTING_IP:                 # Exact instruction that crashed
CONTEXT:                     # Processor context at crash
FAILURE_EXCEPTION_CODE:      # Exception type

# After !analyze -v, switch to crash context:
.ecxr
k                            # Stack at crash
```

## Common Bug Check Codes

| Code | Name | Common Cause |
|------|------|-------------|
| `0x3B` | SYSTEM_SERVICE_EXCEPTION | Driver kernel mode exception |
| `0x50` | PAGE_FAULT_IN_NONPAGED_AREA | NULL deref, freed memory access |
| `0x7E` | SYSTEM_THREAD_EXCEPTION_NOT_HANDLED | Unhandled exception in kernel |
| `0xD1` | DRIVER_IRQL_NOT_LESS_OR_EQUAL | Driver accessed invalid IRQL |
| `0x1E` | KMODE_EXCEPTION_NOT_HANDLED | Unhandled exception in kernel |
| `0xC4` | DRIVER_VERIFIER_DETECTED_VIOLATION | Driver Verifier caught bug |
| `0xEF` | CRITICAL_PROCESS_DIED | Critical process (lsass, csrss) killed |
| `0x139` | KERNEL_SECURITY_CHECK_FAILURE | Stack corruption, CFG violation |
| `0xC5` | DRIVER_CORRUPTED_EXPOOL | Pool corruption |
| `0x9F` | DRIVER_POWER_STATE_FAILURE | Power IRP handling failure |

## Bug-Specific Analysis

### PAGE_FAULT_IN_NONPAGED_AREA (0x50)

```
!analyze -v
# Parameter 1 = faulting address
# Parameter 2 = 0 (read) or 1 (write)
# Parameter 3 = faulting address (instruction)

# Find what was at that address:
!pte <faulting_address>          # Page Table Entry analysis
!pool <faulting_address>         # Pool analysis (might be freed pool)
dt nt!_POOL_HEADER <pool_addr>   # Pool header details
```

### DRIVER_IRQL_NOT_LESS_OR_EQUAL (0xD1)

```
!analyze -v
# Parameter 1 = address accessed
# Parameter 2 = IRQL at crash
# Parameter 3 = 0 (read) or 1 (write)
# Parameter 4 = instruction

# The stack trace shows the driver that caused it
k
# Look for the driver frame in the stack
```

### Pool Corruption (0xC5, 0x19)

```
!analyze -v
!pool <address>              # Analyze the corrupt pool block
!verifier                    # If Driver Verifier was on: shows which driver
.bugcheck                    # Bug check parameters

# Find all allocations near the corrupt pool
!pool <address> 0xa         # Extended pool info
```

## Malware-Related Crash Analysis

### Blue screen caused by rootkit/driver

```
# Step 1: identify faulting module
!analyze -v
# Look at: MODULE_NAME, IMAGE_NAME

# Step 2: check if module is signed/known
lm m <module_name>
!chkimg -d <module_base> <module_end> <module_name>  # Integrity check

# Step 3: check the driver's dispatch table for hooks
!drvobj <DriverName> 7

# Step 4: check if it's loading from unusual path
lm f                         # Full paths of all modules
# Suspicious: temp folders, AppData, non-System32 paths for kernel drivers
```

### Process crash analysis (user-mode dump)

```
# Load user-mode dump
.load wow64exts              # 32-bit on 64-bit
!analyze -v
.ecxr                        # Exception context
k                            # Stack

# All threads at time of crash
~* k                         # Stack of ALL threads

# Thread with exception:
.ttime                       # Thread times
~.                           # Current thread
```

### Memory forensics from dump

```
# Extract strings from entire dump
s -a 0 L?0x7fffffff "cmd.exe"   # Search for strings
s -u 0 L?0x7fffffff "cmd"       # Unicode search

# Find PE headers in memory
s -b 0 L?0x7fffffff 4d 5a       # MZ signatures
# Then check each result:
!dh <address>                    # PE header dump

# Process list from dump
!process 0 0

# Specific process memory
.process /p <EPROCESS>
!vad                             # VADs for process
```

## WinDbg Extensions for Crash Analysis

```
# MEX (Microsoft Escalation Extension)
.load mex                        # Load MEX
!mex.help                        # Command list
!mex.p                           # Process list (nicer)
!mex.tl                          # Thread list

# Psscor2/4 for .NET crashes
.loadby sos clr
!analyze -v                      # .NET-aware crash analysis
!clrstack                        # Managed call stack
!dumpheap -stat                  # Heap statistics

# CMKD (crash mode kernel debugging)
!cmkd.stack                      # Stack analysis
```

## Symbol Configuration

```
# Microsoft public symbol server
.sympath srv*C:\Symbols*https://msdl.microsoft.com/download/symbols

# Corporate + Microsoft
.sympath srv*C:\Symbols*https://msdl.microsoft.com/download/symbols;C:\MySymbols

# Check symbol status
!sym noisy                       # Verbose symbol loading
.reload /f ntoskrnl.exe          # Force reload specific module

# Set source path (if you have source)
.srcpath C:\DriverSource\
```

## Automated Dump Analysis Script

```powershell
# Process all .dmp files in a folder
$dumps = Get-ChildItem "C:\Dumps" -Filter "*.dmp"
foreach ($dump in $dumps) {
    $output = & "C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe" `
        -z $dump.FullName `
        -c "!analyze -v; q" `
        -lines 100 2>&1 | Out-String

    # Extract bug check code
    $bugcheck = ($output | Select-String "BUGCHECK_STR: (.+)").Matches.Groups[1].Value
    $module = ($output | Select-String "MODULE_NAME: (.+)").Matches.Groups[1].Value

    "$($dump.Name): BugCheck=$bugcheck Module=$module" | Out-File "crash_summary.txt" -Append
}
```
