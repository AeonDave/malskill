# Anti-Analysis Techniques and Bypasses

Comprehensive reference for anti-debugging, anti-VM, anti-DBI, code integrity, and anti-disassembly techniques with practical bypass strategies. Applies to protected targets on Linux and Windows.

---

## Quick Triage Checklist

Before dynamic analysis, enumerate protection layers:

```bash
# Linux
strace -e trace=ptrace,signal ./binary 2>&1 | head -30
strings binary | grep -iE "ptrace|tracerpid|cpuid|hypervisor|vmware|vbox|frida|pin"

# Windows  
strings binary | grep -iE "IsDebugger|NtQuery|CheckRemote|VirtualBox|VMware|Frida"
```

**Layering order:** self-ptrace check → timing check → environment check → integrity check → real logic.  
Always identify all layers before patching — missing a secondary check often wastes significant time.

---

## Category 1: Linux Anti-Debug

### 1.1 ptrace Self-Tracing

The most common anti-debug primitive. Binary calls `ptrace(PTRACE_TRACEME)` — if a debugger is attached, the call returns `-1` and the process exits.

```c
// Source pattern
if (ptrace(PTRACE_TRACEME, 0, 0, 0) == -1) exit(1);
```

**Bypass options (choose based on access level):**

```bash
# Option A — LD_PRELOAD hook (no root, user-space)
cat > hook.c << 'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/ptrace.h>
long int ptrace(enum __ptrace_request req, ...) {
    return 0;   // Always report success
}
EOF
gcc -shared -fPIC -ldl hook.c -o hook.so
LD_PRELOAD=./hook.so ./binary

# Option B — pwntools binary patch (permanent fix)
python3 - << 'EOF'
from pwn import *
elf = ELF('./binary', checksec=False)
elf.asm(elf.symbols['ptrace'], 'xor eax, eax; ret')   # return 0
elf.save('patched')
EOF

# Option C — GDB syscall intercept
gdb ./binary
(gdb) catch syscall ptrace
(gdb) commands
> set $rax = 0
> continue
> end
(gdb) run

# Option D — kernel scope (requires root)
echo 0 > /proc/sys/kernel/yama/ptrace_scope
```

**Double-ptrace (watchdog child):**
Some binaries fork a child that ptrace-attaches to the parent, blocking all external debuggers.

```c
pid_t child = fork();
if (child == 0) {
    ptrace(PTRACE_ATTACH, getppid(), 0, 0);
    while (1) waitpid(getppid(), NULL, 0);  // keeps parent traced
}
// Parent continues with real logic
```

**Bypass:** Kill or prevent the watchdog child:
```bash
# In GDB: set a fork catchpoint and kill the child
(gdb) catch fork
(gdb) run
# When fork fires, GDB is in child:
(gdb) call (void)exit(0)   # Kill watchdog child
(gdb) continue             # Parent proceeds unmonitored
```

---

### 1.2 /proc Filesystem Checks

```c
// TracerPid check — non-zero means debugger attached
FILE *f = fopen("/proc/self/status", "r");
// Scans for "TracerPid:" field
```

**Bypass options:**
```bash
# LD_PRELOAD: intercept fopen and return /dev/null for status files
cat > fake_proc.c << 'EOF'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
FILE *fopen(const char *path, const char *mode) {
    FILE *(*orig)(const char*, const char*) = dlsym(RTLD_NEXT, "fopen");
    if (strstr(path, "/proc/self/status") || strstr(path, "/proc/self/maps"))
        return orig("/dev/null", mode);
    return orig(path, mode);
}
EOF
gcc -shared -fPIC -ldl fake_proc.c -o fake_proc.so
LD_PRELOAD=./fake_proc.so ./binary

# GDB: redirect fopen argument at call time
(gdb) b fopen
(gdb) commands
> set $rdi = &"/dev/null"
> continue
> end
```

---

### 1.3 Timing-Based Detection

Binary measures elapsed CPU cycles or wall clock time to detect the single-step overhead of a debugger.

```c
uint64_t start = __rdtsc();
// ... some code ...
if (__rdtsc() - start > THRESHOLD) exit(1);   // Too slow = debugger
```

**Bypass:**
```bash
# Option A — Frida: freeze clock_gettime
frida -f ./binary --no-pause -e '
Interceptor.attach(Module.findExportByName(null, "clock_gettime"), {
    onLeave(retval) {
        var ts = this.context.rsi;
        Memory.writeU64(ts, 0);
        Memory.writeU64(ts.add(8), 0);
    }
});
'

# Option B — faketime library
LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1 FAKETIME="2024-01-01" ./binary

# Option C — GDB: NOP the rdtsc instruction
(gdb) set {unsigned char[2]} 0xADDRESS = {0x90, 0x90}

# Option D — Qiling emulation (no timing side-effects by design)
```

---

### 1.4 Signal-Based Anti-Debug

```c
// SIGTRAP: if a debugger is attached, it intercepts INT3 — handler never runs
signal(SIGTRAP, my_handler);
__asm__("int3");
// If handler runs: not debugged. If debugger catches: debugged.

// SIGSEGV handler doing real work
signal(SIGSEGV, real_logic_handler);
*(int*)0 = 0;   // Deliberate null deref → real code in handler
```

**Bypass:**
```bash
# GDB: pass signals to the program instead of intercepting
(gdb) handle SIGTRAP nostop pass
(gdb) handle SIGSEGV nostop pass
(gdb) handle SIGALRM ignore

# strace: observe signal flow and count signal deliveries as side channel
strace -e signal=SIGFPE ./binary                    # count SIGFPE per input
strace -e signal=SIGFPE ./binary 2>&1 | grep -c SIGFPE
```

---

### 1.5 Direct Syscall (Bypasses LD_PRELOAD)

Binaries that call `ptrace` via raw `syscall` instruction bypass LD_PRELOAD hooks entirely.

```c
asm volatile("mov $101, %%rax; syscall" : : : "rax");   // ptrace syscall 101
```

**Bypass:**
```bash
# GDB: catch at syscall level
(gdb) catch syscall 101
(gdb) commands
> set $rax = 0
> continue
> end
```

---

## Category 2: Windows Anti-Debug

### 2.1 PEB Checks

The Process Environment Block has several debugger-indicator fields.

```c
// PEB.BeingDebugged (byte at PEB+0x2)
BOOL IsBeingDebugged = *(BOOL*)(__readgsqword(0x60) + 2);

// PEB.NtGlobalFlag (0x70) — set to 0x70 when debugged
DWORD NtGlobalFlag = *(DWORD*)(__readgsqword(0x60) + 0x70);

// Heap flags (at PEB.ProcessHeap+0x70 on x64)
DWORD HeapFlags = *(DWORD*)(heap + 0x70);  // 0x40000062 when debugged
```

**Bypass options:**
```bash
# x64dbg with ScyllaHide: automatically patches PEB fields
# Enable: Options → ScyllaHide → NtGlobalFlag, HeapFlags, BeingDebugged

# Manual: set breakpoint after PEB read, zero out the field
# In WinDbg:
eb @$peb+2 0                # Zero BeingDebugged
ed @$peb+0x70 0             # Zero NtGlobalFlag
```

---

### 2.2 NtQueryInformationProcess

```c
ULONG DebugPort = 0;
NtQueryInformationProcess(GetCurrentProcess(), 7,   // ProcessDebugPort
                           &DebugPort, sizeof(ULONG), NULL);
if (DebugPort != 0) ExitProcess(0);   // Debugger attached
```

**Bypass:** Hook with Frida or ScyllaHide; force output to zero.

---

### 2.3 TLS Callbacks

TLS (Thread Local Storage) callbacks execute before the debugger reaches the entry point. Used to plant anti-debug checks that fire before `main()`.

**Detection:**
```bash
# Check for TLS callbacks in binary
python3 - << 'EOF'
import pefile
pe = pefile.PE('./binary.exe')
if hasattr(pe, 'DIRECTORY_ENTRY_TLS'):
    tls = pe.DIRECTORY_ENTRY_TLS.struct
    callbacks_rva = tls.AddressOfCallBacks
    print(f"TLS callbacks at RVA: {callbacks_rva:#x}")
EOF
```

**Bypass:**
- Set breakpoint on TLS callback addresses before running.
- In x64dbg: Options → Preferences → Events → TLS Callbacks → Break on TLS callbacks.

---

### 2.4 Hardware Breakpoint Detection

```c
// Read debug registers via CONTEXT structure
CONTEXT ctx = { .ContextFlags = CONTEXT_DEBUG_REGISTERS };
GetThreadContext(GetCurrentThread(), &ctx);
if (ctx.Dr0 || ctx.Dr1 || ctx.Dr2 || ctx.Dr3) ExitProcess(0);
```

**Bypass:** Use software breakpoints (INT3 / 0xCC) instead of hardware breakpoints, or hook `GetThreadContext`/`NtGetContextThread` to zero debug registers in returned data.

---

### 2.5 Software Breakpoint Detection (INT3 Scanning)

```c
// Binary hashes its own code at startup; INT3 (0xCC) changes the hash
DWORD crc = CRC32(code_start, code_length);
if (crc != EXPECTED_CRC) ExitProcess(0);
```

**Bypass:** Use hardware breakpoints (DR0-DR3) instead of INT3. Alternatively, patch the integrity check itself.

---

### 2.6 NtSetInformationThread (Thread Hiding)

Hides a thread from debuggers. Breakpoints and single-stepping on hidden threads are transparent to attached debuggers.

```c
NtSetInformationThread(GetCurrentThread(),
                        ThreadHideFromDebugger, NULL, 0);
```

**Bypass:** Hook `NtSetInformationThread` to ignore `ThreadHideFromDebugger` class.

---

## Category 3: Anti-VM and Anti-Sandbox

### 3.1 CPUID Hypervisor Bit

```c
// Check bit 31 of ECX after CPUID leaf 1
int cpuinfo[4];
__cpuid(cpuinfo, 1);
if (cpuinfo[2] & (1 << 31)) exit(0);   // Hypervisor bit set = VM
```

**Bypass:**
- Configure VMware/VirtualBox to hide hypervisor bit (CPUID masking).
- In Qiling: CPUID is emulated and hypervisor bit is not set by default.

---

### 3.2 MAC Address / Hardware Fingerprinting

```c
// Known VM MAC prefixes: 00:0C:29 (VMware), 08:00:27 (VirtualBox)
getifaddrs(&ifap);
// Checks first 3 octets against known VM prefix table
```

**Bypass:**
- Change VM's MAC address to a non-VM OUI.
- LD_PRELOAD hook on `getifaddrs` to return a fake interface.

---

### 3.3 Timing VM Detection

VMs have higher latency on certain instructions (`cpuid`, `rdtsc`, I/O port access).

**Bypass:** Same timing bypass as anti-debug timing checks (§1.3). Qiling avoids this entirely.

---

### 3.4 File / Registry Artifacts

```c
// Checks for VM-specific files
access("/proc/scsi/scsi", F_OK);           // SCSI controller name has "VBOX"
fopen("C:\\Windows\\System32\\drivers\\vmmouse.sys", "r");
RegOpenKeyEx(HKLM, "SOFTWARE\\VMware, Inc.", ...);
```

**Bypass:**
- Linux: mount-bind `/dev/null` over the checked path.
- Windows: registry virtualization or hook `RegOpenKeyEx`.
- Qiling: filesystem hooks redirect all checked paths.

---

### 3.5 Resource Checks

```c
// Too few CPUs or too little RAM = sandbox
if (GetNumberOfProcessors() < 4) ExitProcess(0);
if (GetPhysicallyInstalledSystemMemory(&kb) && kb < 4*1024*1024) ExitProcess(0);
// Disk size check, fan speed via WMI, screen resolution check
```

**Bypass:** Patch comparison or hook the resource-querying functions.

---

## Category 4: Anti-DBI (Dynamic Binary Instrumentation)

### 4.1 Frida Detection

```c
// /proc/self/maps contains "frida" or "linjector"
grep("frida", maps_content);

// frida-agent creates a named pipe: /tmp/frida-*
access("/tmp/frida-12345", F_OK);

// Thread name injection: frida threads have "frida-" prefix
// Direct API check
```

**Bypass:**
- Use Frida `gadget` mode (embedded, no injection visible in maps).
- Use `--runtime=v8` injection mode instead of default.
- Hook `fopen`/`openat` to redirect `/proc/self/maps` to a sanitized version.

---

### 4.2 Pin / DynamoRIO Detection

```c
// Pin creates extra threads; DynamoRIO uses specific memory patterns
// Detection via /proc/self/maps looking for pin-specific libraries
// Direct detection of code cache in known address ranges
```

**Bypass:** Use Qiling (purely user-space, no injected threads) or Triton (offline trace analysis).

---

## Category 5: Code Integrity and Self-Hashing

**Pattern:** Binary computes a hash (CRC32, MD5, SHA-1) over its own code at startup. Patching instructions breaks the integrity check.

**Bypass strategies:**

```python
# Option A — patch the integrity check itself, not the protected code
# Find: cmp eax, <expected_crc>
# Patch: nop the comparison and jump

# Option B — use hardware breakpoints (don't modify code bytes, avoid 0xCC)

# Option C — fix-up the expected hash after patching
from pwn import *
elf = ELF('./binary')
# Patch target function
elf.asm(target_addr, 'xor eax, eax; ret')
# Recalculate CRC32 of the modified section and patch the expected constant
import binascii
new_crc = binascii.crc32(elf.read(section_start, section_len)) & 0xFFFFFFFF
elf.write(expected_crc_addr, p32(new_crc))
elf.save('patched')
```

---

## Category 6: Anti-Disassembly

### 6.1 Opaque Predicates

```asm
; Always-true condition that confuses disassemblers
xor eax, eax
jz  real_code       ; Always jumps (eax always zero)
db  0xe8            ; Junk byte interpreted as incomplete call
real_code:          ; Disassemblers may parse 0xe8 as call instruction
```

**Bypass:** Force disassembler to start at the correct address. In Ghidra: right-click → Disassemble at cursor position.

---

### 6.2 Junk Bytes and Overlapping Instructions

```asm
; 0xEB 0x01 0x?? — short jump over one junk byte
jmp short +1
db  0xe8            ; junk — never executed
real_instruction:
```

**Bypass:** Use the `DISASM_OVERRIDE` annotation in Ghidra, or set a concrete execution breakpoint in GDB and note the actual PC after the jump.

---

### 6.3 Control Flow Flattening (CFF / OLLVM)

All basic blocks dispatched via a central state variable in a `while(1) { switch(state) { ... } }` loop. Static decompilation produces unreadable nested conditionals.

**Bypass — runtime state trace:**
```bash
# GDB script: break at each state update and log the value
gdb ./binary << 'EOF'
b *0x401234       # Address of state variable write
commands
  silent
  printf "state = %d\n", $eax
  continue
end
run < /dev/null
quit
EOF
```

**Bypass — D-810 (IDA plugin) or GOOMBA (Ghidra):** Pattern-based deobfuscation rewrites the CFF dispatcher back to structured control flow.

**Bypass — Miasm symbolic execution:**
```python
from miasm.analysis.binary import Container
from miasm.analysis.machine import Machine
from miasm.core.locationdb import LocationDB

loc_db = LocationDB()
cont = Container.from_stream(open('./binary', 'rb'), loc_db)
machine = Machine('x86_64')
mdis = machine.dis_engine(cont.bin_stream, loc_db=loc_db)
# Use CFG reconstruction to lift CFF blocks back to structured IR
```

---

### 6.4 Mixed Boolean-Arithmetic (MBA) Simplification

MBA replaces simple operations with equivalent but complex bitwise/arithmetic expressions:
```
(a + b) → (a ^ b) + 2*(a & b)
(a XOR b) → (a | b) - (a & b)
```

**Identification:** Long chains of bitwise operations (`and`, `or`, `xor`, `not`, shifts) that could be replaced by a single arithmetic operation.

**Bypass options:**
1. **D-810 IDA plugin** — MBA simplification rules.
2. **GOOMBA Ghidra plugin** — P-Code-level simplification.
3. **sspam (Python):** `pip install sspam`; `sspam 'expr'` simplifies expressions.
4. **Symbolic execution (Z3):** Treat the expression as a black box and verify simplification:

```python
from z3 import *

a, b = BitVecs('a b', 64)
# Original MBA expression
original = (a | b) - (a & b)
# Proposed simplification
simplified = a ^ b
# Prove equivalence
s = Solver()
s.add(original != simplified)
if s.check() == unsat:
    print("Simplification correct")
```

---

## Category 7: Comprehensive Bypass Quick Reference

| Check | Best bypass tool | Approach |
|-------|-----------------|----------|
| `ptrace(TRACEME)` | pwntools / LD_PRELOAD | Return 0; or NOP the call |
| `/proc/self/status` TracerPid | LD_PRELOAD fopen | Redirect to `/dev/null` |
| `rdtsc` / `clock_gettime` timing | Frida / faketime | Freeze timestamp |
| `SIGTRAP` handler | GDB `handle SIGTRAP nostop pass` | Signal passthrough |
| `SIGSEGV` real logic | GDB `handle SIGSEGV nostop pass` | Signal passthrough |
| PEB.BeingDebugged | ScyllaHide / x64dbg plugin | Auto-patch PEB fields |
| NtQueryInformationProcess | ScyllaHide | Hook return value |
| TLS callbacks anti-debug | x64dbg TLS breakpoints | Break before TLS executes |
| Hardware BP detection | Software BPs (INT3) only | Avoid HWBP entirely |
| Code integrity CRC | HWBP over patched code | Avoid modifying code bytes |
| CPUID hypervisor bit | Qiling / VM CPU masking | Hide bit in CPUID response |
| VM MAC address check | Change VM MAC | Non-VM OUI prefix |
| CFF obfuscation | D-810 / GOOMBA / GDB trace | Runtime state trace or plugin |
| MBA obfuscation | D-810 / Z3 | Algebraic simplification |
| Frida detection | Gadget mode | Embedded, no map entries |
| Direct syscall ptrace | GDB `catch syscall 101` | Kernel-level intercept |
| Double-ptrace watchdog | GDB fork catchpoint | Kill child immediately |

---

## Common Pitfalls

1. **Patching the wrong layer** — fix one check but a secondary check (TLS callback, integrity hash) defeats the patch.
2. **Using INT3 breakpoints on integrity-checked code** — always use hardware breakpoints on self-hashing binaries.
3. **Ignoring signal handlers** — real logic inside SIGSEGV/SIGILL/SIGTRAP handlers is invisible to linear disassembly.
4. **Trusting the "wrong" code path** — CFF and MBA mean the "obvious" path may be the decoy; trace runtime state.
5. **LD_PRELOAD bypass fails on direct syscalls** — if the binary calls `ptrace` directly via `syscall` instruction, LD_PRELOAD doesn't intercept it; use GDB catch syscall instead.

---

## Category 7: Heaven's Gate / WoW64 on Linux (x86 ↔ x64 Mixed-Mode)

A 32-bit ELF can switch to 64-bit execution mode at runtime using a far jump with selector `0x33`. This is the Linux equivalent of the Windows "Heaven's Gate" trick. The outer binary appears to be x86 (32-bit); sections of its code actually execute as x86-64.

### 7.1 Detection

```bash
# Static: look for far jump / far ret with segment 0x33
objdump -d binary | grep -E "ljmp|lcall|lret|retf"
# Explicit pattern for ljmp 0x33:
objdump -d binary | grep "ljmp.*0x33,"
# or hex search: EA xx xx xx xx 33 00 (far jmp to selector 0x33)
python3 -c "
data = open('binary','rb').read()
import re
# Far jmp pattern: 0xEA + 4-byte offset + 0x0033
for m in re.finditer(b'\\xea....\\x33\\x00', data):
    print('far jmp at', hex(m.start()))
# push 0x33; retf pattern
for m in re.finditer(b'\\x6a\\x33[\\xc3\\xcb]', data):
    print('push 0x33 + ret at', hex(m.start()))
"
```

**Other indicators:**
- Binary is `ET_EXEC` with class `ELF32` but imports suggest 64-bit behavior
- Unusual CS register manipulation (segment register writes in 32-bit context)
- `readelf -h binary` → `Class: ELF32`, `Machine: Intel 80386` but binary payload clearly uses 64-bit instructions

### 7.2 GDB strategy

GDB's default architecture for a 32-bit ELF is `i386`. After the far jump, GDB will misinterpret the 64-bit code unless you switch:

```bash
gdb ./binary
(gdb) set architecture i386        # Initial: 32-bit mode
(gdb) break _start
(gdb) run

# When execution crosses the far jump into 64-bit code:
(gdb) set architecture i386:x86-64  # Switch to 64-bit disassembly
# Or use gdb-multiarch which auto-detects mode switches
```

```bash
# Prefer gdb-multiarch for seamless mode switching
gdb-multiarch ./binary
(gdb) set architecture auto
```

**Catch the mode switch:**
```bash
# Set a watchpoint on CS register if the debugger supports it
(gdb) watch $cs
# Or breakpoint at the far-jump address
(gdb) b *0x<ljmp_address>
```

### 7.3 Ghidra analysis

Ghidra auto-analyzes based on the ELF header (32-bit). The 64-bit region will be disassembled as 32-bit garbage.

**Workflow:**
1. Import binary normally → analyze as 32-bit x86
2. Locate the far-jump target address (from static or dynamic analysis)
3. In Ghidra: right-click at the target address → **Disassemble → Disassemble x86-64 context**  
   - `Edit → Set Processor Context` → change context to 64-bit for that address range
4. Alternatively: extract the 64-bit code region as a raw binary and load as a separate ELF64 project
5. Cross-reference: link the two Ghidra projects via shared data structures

**Extract 64-bit region:**
```bash
# After identifying the offset and size of the 64-bit code region
dd if=binary bs=1 skip=<offset> count=<size> of=code64.bin
# Load code64.bin as raw x86-64 in a new Ghidra project
# Set base address to the VA from the original binary
```

### 7.4 radare2 workflow

```bash
r2 -m 0x0 binary     # Load with base address override if needed
[0x0]> e asm.arch=x86
[0x0]> e asm.bits=32
[0x0]> aaa

# Navigate to the far-jump target
[0x0]> s <target_addr>
[0x0]> e asm.bits=64   # Switch to 64-bit disassembly at this position
[0x0]> pd 30           # Disassemble 30 instructions in 64-bit mode
```

### 7.5 Bypass pattern

The goal is to analyze the 64-bit payload in isolation:

1. **Dump at runtime:** GDB / Frida — after the far jump fires, dump the memory region
2. **Load as 64-bit ELF:** reconstruct an ELF64 header pointing to the dumped code region
3. **Analyze normally:** the 64-bit region is usually a self-contained function or stage
