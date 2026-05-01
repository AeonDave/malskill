# Binary Triage Reference

Quick decision-making before investing time in full static or dynamic analysis.
Goal: spend ≤10 minutes answering the key questions that determine your RE strategy.

---

## Key questions before starting

1. **What binary type?** PE (Windows), ELF (Linux), firmware blob, .NET, or other?
2. **Is it packed/encrypted?** Entropy > 7.0 in code sections = unpack first.
3. **Go / Rust / C++?** Changes tool choice and analysis approach significantly.
4. **What imports?** Few imports + injection APIs = suspicious behavior.
5. **String leaks?** Compiler artifacts, debug paths, offensive terms = immediate context.

---

## Phase 1: OS-level identification

### Linux tools

```bash
# Format + arch + linker info
file sample.exe
file sample.elf
file firmware.bin

# Quick string scan
strings -a -n 6 sample.exe | head -100
strings -a -e l sample.exe | head -50     # UTF-16LE (Windows binaries)

# ELF-specific
readelf -h sample.elf          # Header: class, arch, type, entry point
readelf -S sample.elf          # Sections: name, size, offset, flags
readelf -s sample.elf          # Symbol table (if not stripped)
readelf -d sample.elf          # Dynamic section (shared libs)

# PE-specific (requires Python pefile or radare2)
objdump -f sample.exe          # File headers
```

### radare2 quick pass

```bash
r2 sample.exe
> iI           # PE/ELF info: arch, bits, class, endian, lang
> iS           # Sections: name, size, entropy, permissions
> ii           # Imports
> ie           # Exports
> iz           # Strings in data sections
> q
```

---

## Phase 2: Entropy scan

Entropy is the single fastest indicator of whether code is accessible.

| Range | Meaning | Action |
|-------|---------|--------|
| 0 – 3.5 | Padding / structured data | Normal |
| 4.0 – 6.5 | Plaintext code or text | Ready for static analysis |
| 6.5 – 7.0 | Mixed, maybe compressed | Investigate sections |
| > 7.0 | Encrypted / compressed | Must unpack before analysis |

```bash
# binwalk: per-section entropy + graph
binwalk -E sample.exe

# radare2: per-section entropy in section table
r2 -q -e bin.verbose=0 sample.exe -c "iS;q"
# Entropy column in iS output — look for > 7.0 in .text or unnamed sections
```

### Python snippet — per-section entropy (inline, no deps)

```python
import math, struct, sys

def shannon(data):
    if not data: return 0.0
    freq = [0]*256
    for b in data: freq[b] += 1
    n = len(data)
    return -sum(f/n*math.log2(f/n) for f in freq if f > 0)

def pe_section_entropy(path):
    data = open(path,'rb').read()
    assert data[:2] == b'MZ'
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    nsec = struct.unpack_from('<H', data, e_lfanew+6)[0]
    optsz = struct.unpack_from('<H', data, e_lfanew+20)[0]
    soff = e_lfanew + 24 + optsz
    print(f"{'Name':<12} {'RawSz':>8} {'Entropy':>8}  Flag")
    for i in range(nsec):
        s = soff + i*40
        name = data[s:s+8].rstrip(b'\x00').decode('ascii','ignore')
        rs = struct.unpack_from('<I', data, s+16)[0]
        ro = struct.unpack_from('<I', data, s+20)[0]
        if rs == 0: continue
        e = shannon(data[ro:ro+rs])
        flag = '← ENCRYPTED/COMPRESSED !' if e > 7.0 else ''
        print(f"{name:<12} {rs:>8,} {e:>8.4f}  {flag}")

pe_section_entropy(sys.argv[1])
```

---

## Phase 3: Packer / obfuscation detection

### Indicators in order of reliability

1. **High-entropy `.text`** (> 7.0) — encrypted code, must unpack.
2. **Very few imports** (< 5 functions) — packed binary hides real IAT.
3. **Packer signatures** in section names: `.UPX0`, `.nsp0`, `.vmp0`, `CODE`.
4. **Mismatched section flags** — writable+executable section (shellcode staging).
5. **Entry point outside `.text`** — entry in `.data`, `.reloc`, or unnamed section.

```bash
# UPX detection and unpacking
upx -d sample.exe -o unpacked.exe

# packer signature check (radare2)
r2 sample.exe -q -c "iS;q" | grep -iE "upx|vmp|nsp|themid"

# PE entry point vs sections
r2 sample.exe -q -c "ie;q"   # entry point VA
# Compare against iS output to see which section contains it
```

---

## Phase 4: Import analysis (PE)

### What to look for

```bash
# radare2: full import list
r2 sample.exe -q -c "ii;q"

# Filter for suspicious categories
r2 sample.exe -q -c "ii;q" | grep -iE "Virtual|WriteProcess|CreateRemote|SetThread|QueueAPC"
r2 sample.exe -q -c "ii;q" | grep -iE "IsDebugger|NtQuery|GetTickCount|OutputDebug"
```

### Python snippet — flag suspicious APIs (inline, no deps)

```python
import struct, sys

INJECTION = {"VirtualAllocEx","WriteProcessMemory","CreateRemoteThread",
             "NtAllocateVirtualMemory","NtWriteVirtualMemory","NtCreateThreadEx",
             "RtlCreateUserThread","QueueUserAPC","SetThreadContext"}
EVASION   = {"IsDebuggerPresent","CheckRemoteDebuggerPresent","NtQueryInformationProcess",
             "GetTickCount","GetTickCount64","NtSetInformationThread"}
COMBOS = [
    ({"VirtualAllocEx","WriteProcessMemory","CreateRemoteThread"}, "remote injection"),
    ({"VirtualAlloc","VirtualProtect","CreateThread"},             "local shellcode exec"),
    ({"QueueUserAPC","ResumeThread"},                              "early-bird APC"),
    ({"NtAllocateVirtualMemory","NtWriteVirtualMemory","NtCreateThreadEx"}, "direct syscall inject"),
]

def quick_iat(path):
    data = open(path,'rb').read()
    # collect all null-terminated strings as proxy for API names
    all_strs = set()
    i = 0
    while i < len(data)-2:
        if 0x20 <= data[i] < 0x7F:
            j = i
            while j < len(data) and 0x20 <= data[j] < 0x7F: j += 1
            s = data[i:j].decode('ascii','ignore')
            if 3 < len(s) < 60: all_strs.add(s)
            i = j
        else:
            i += 1

    inj = [f for f in all_strs if f in INJECTION]
    eva = [f for f in all_strs if f in EVASION]
    if inj: print(f"[INJECTION] {inj}")
    if eva: print(f"[EVASION]   {eva}")
    for combo, label in COMBOS:
        if combo.issubset(all_strs):
            print(f"[COMBO] ⚠  {label}: {combo}")

quick_iat(sys.argv[1])
```

---

## Phase 5: Language / toolchain detection

### .NET binaries (managed)

```bash
# Fast managed detection (CLI metadata directory present)
python -c "import struct,sys;d=open(sys.argv[1],'rb').read();e=struct.unpack_from('<I',d,0x3C)[0];o=e+24;m=struct.unpack_from('<H',d,o)[0];ddb=o+(112 if m==0x20B else 96);cli=ddb+(14*8);rva,size=struct.unpack_from('<II',d,cli);print('.NET managed' if rva and size else 'native PE')" sample.exe

# Quick framework/runtime markers
strings -a sample.exe | grep -iE "mscorlib|System\.Private\.CoreLib|v4\.0\.30319|\.NET"

# If managed: move to .NET toolchain
# - dnSpy/dnSpyEx for decompilation + debugging + patching
# - de4dot for deobfuscation
# - ilspycmd for CLI export/decompile
```

### Go binaries

```bash
# Fast check: runtime markers
strings -a sample.exe | grep -cE "runtime\."   # > 10 = almost certainly Go
strings -a sample.exe | grep "go.buildid"

# radare2: pclntab function recovery
r2 -A sample.exe
> afl                         # after analysis, Go functions appear dotted (main.X)
> "afl~main\."                # main package functions
> "iz~pclntab"                # pclntab section present?
> q
```

### Rust binaries

```bash
strings -a sample.exe | grep -cE "/rustc/|core::fmt|panicked at"   # > 0 = Rust
```

### C++ RTTI (GCC/MSVC)

```bash
strings -a sample.exe | grep -E "^\.?class [A-Z]"    # RTTI class names
strings -a sample.elf  | grep "vtable for"
```

### Python snippet — language detection (inline, no deps)

```python
import re, sys

data = open(sys.argv[1],'rb').read()

go_rt = len(re.findall(rb'runtime\.\w+', data))
go_bd = data.count(b'go.buildid') + data.count(b'go:buildid')
rust = data.count(b'/rustc/') + data.count(b'core::fmt') + data.count(b'panicked at')
mingw = data.count(b'mingw') + data.count(b'__mingw')
cgo   = data.count(b'_cgo_')
dotnet = (
    data.count(b'mscoree.dll') +
    data.count(b'_CorExeMain') +
    data.count(b'mscorlib') +
    data.count(b'System.Private.CoreLib') +
    data.count(b'v4.0.30319')
)

if dotnet:
    print(f"[.NET] CLR markers: {dotnet}")
    print("       → use dnSpy/dnSpyEx, de4dot, ilspycmd")

if go_rt > 5 or go_bd:
    print(f"[Go] runtime.*: {go_rt}, buildid: {go_bd}")
    print("     → use radare2 pclntab recovery; ghidra GoRename script")
if rust:
    print(f"[Rust] /rustc/+core refs: {rust}")
    print("     → demangler needed; prefer ghidra with Rust support")
if mingw or cgo:
    print(f"[MinGW/CGo] mingw: {mingw}, _cgo_: {cgo}")
if go_rt == 0 and rust == 0 and dotnet == 0:
    print("[C/C++/MSVC] no language-specific markers found")
```

---

## Phase 6: Hardening and interface sketch

Before deep analysis, capture a quick exploitability and reachability baseline.

### Hardening snapshot

- **PE:** note ASLR, DEP/NX, CFG, SEH behavior, signature state, service/driver context.
- **ELF:** note PIE, NX, RELRO, CANARY, FORTIFY, setuid/capabilities, seccomp hints.
- **Firmware / embedded:** note watchdog restart behavior, privileged daemons, update-signature checks.

The point is not to decide exploitability yet; it is to avoid spending hours on a code path that can never produce the control you need.

### Interface discovery

Map the reachable input surfaces before picking targets:

- argv / CLI switches
- environment variables
- file formats or config files
- network listeners / protocols
- IPC, plugins, update packages, or scripts

### Priority-target list

Build a short target list with explicit rationale:

1. **parser-heavy function** — attacker-controlled length/offset/content reaches memory operations
2. **auth or crypto decision path** — good for bypass, oracle, or secrets work
3. **dangerous call cluster** — allocator + memcpy/strcpy/formatting + branch logic

For each target, write one proof requirement such as:

- “show attacker controls length and destination size relation”
- “show branch is reachable from default runtime path”
- “show crash is repeatable across restarts”

---

## Phase 7: String leak scan

Quick scan for strings that immediately reveal context (offensive tooling, build paths, debug info).

```bash
# Broad offensive terms
strings -a -n 6 sample.exe | grep -iE \
  "beacon|shellcode|inject|loader|cobalt|sliver|amsi|etw|unhook|c2server"

# Debug/path leaks
strings -a -n 8 sample.exe | grep -iE "\\\\Users\\\\|\.pdb$|\\\\src\\\\"

# Compiler artifacts
strings -a -n 6 sample.exe | grep -iE "GCC:|mingw|rustc|GOROOT|go\.buildid"

# GetProcAddress targets appearing as plaintext
strings -a -n 6 sample.exe | grep -iE \
  "NtAllocate|NtCreateThread|EtwEventWrite|AmsiScan|LdrLoadDll"
```

---

## Triage script

[`scripts/triage.py`](../scripts/triage.py) combines all phases above into a single run.

```bash
# Single file
python scripts/triage.py sample.exe

# Multiple files
python scripts/triage.py a.exe b.exe c.elf

# Show all string matches (default: first 5 per category)
python scripts/triage.py --full sample.exe
```

**Output sections:**
1. Binary type, arch, section count
2. Per-section entropy table with classification
3. Packer heuristics (import count, UPX, .text entropy)
4. Import flagging with dangerous combo detection
5. Language / toolchain markers (Go, Rust, .NET, MinGW/CGo, C++)
6. String leak scan (offensive, compiler, debug paths, runtime API targets)
7. Summary with prioritized next-step recommendations

---

## Decision table: what to do next

| Finding | Next step |
|---------|-----------|
| `.text` entropy > 7.0 | Dynamic unpack: `x64dbg` → breakpoint on `VirtualAlloc` → dump with Scylla |
| < 5 imports | Run unpacked binary through triage again |
| `.NET managed assembly` | Switch early to `dnSpy/dnSpyEx` + `de4dot`; inspect `Main`, config/resources, and obfuscator type |
| Go binary | `radare2 -A` → `afl` for pclntab functions; or ghidra GoRename script |
| Rust binary | `ghidra` with Rust demangler; `strings` for panic messages as function hints |
| Injection API combo | Set breakpoints on combo APIs in `x64dbg`; monitor memory allocation |
| `IsDebuggerPresent` | Patch out (NOP or `xor eax,eax`) in `x64dbg` before running |
| Debug path leak | Build metadata → trace back to source repo if OSINT |
| Offensive term leak | Immediate indicator of intent; prioritize that string cross-reference in ghidra |
| High-value parser + weak hardening | Escalate to vulnerability-hunting workflow; define proof requirements before fuzzing |
| Clear input channel but unclear branch reachability | Force branch selection with crafted corpus or runtime probe before deep tracing |
| Clean, no markers | Proceed to static analysis: `ghidra` full auto-analysis |
