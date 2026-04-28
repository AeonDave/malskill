# Offensive ASM Debugging

Techniques for debugging and bug-hunting in offensive assembly: trampolines, callgates, indirect syscall stubs, stack spoofing, and PIC shellcode. Covers Python helper scripts, dynamic instrumentation, emulation, and reverse engineering of own binaries.

---

## 1. Python Analysis Toolkit

Ad-hoc Python scripts are the fastest way to triage ASM bugs when debuggers are impractical (e.g., code only runs inside a target process, anti-debug is active, or the crash is non-deterministic).

### Disassemble raw bytes (Capstone)

```python
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

def disasm_file(path, base=0x1000):
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    code = open(path, "rb").read()
    for i in md.disasm(code, base):
        print(f"0x{i.address:08x}: {i.mnemonic:8s} {i.op_str}")

disasm_file("shellcode.bin")
```

### Disassemble from PE section

```python
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = pefile.PE("loader.exe")
md = Cs(CS_ARCH_X86, CS_MODE_64)
text = next(s for s in pe.sections if b".text" in s.Name)
code = text.get_data()
base = pe.OPTIONAL_HEADER.ImageBase + text.VirtualAddress

for i in md.disasm(code, base):
    print(f"0x{i.address:x}:\t{i.mnemonic}\t{i.op_str}")
```

### Emulate with tracing (Unicorn)

```python
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)

def hook_code(uc, address, size, user_data):
    code = uc.mem_read(address, size)
    for i in md.disasm(bytes(code), address):
        rax = uc.reg_read(UC_X86_REG_RAX)
        rsp = uc.reg_read(UC_X86_REG_RSP)
        print(f"0x{i.address:x}: {i.mnemonic:8s} {i.op_str:30s} "
              f"RAX=0x{rax:x} RSP=0x{rsp:x}")

uc = Uc(UC_ARCH_X86, UC_MODE_64)
BASE = 0x100000
STACK = 0x200000
uc.mem_map(BASE, 0x10000)           # code
uc.mem_map(STACK - 0x4000, 0x8000)  # stack

code = open("stub.bin", "rb").read()
uc.mem_write(BASE, code)
uc.reg_write(UC_X86_REG_RSP, STACK)
uc.reg_write(UC_X86_REG_RCX, 0xFFFFFFFFFFFFFFFF)  # ProcessHandle = -1

uc.hook_add(UC_HOOK_CODE, hook_code)

try:
    uc.emu_start(BASE, BASE + len(code), timeout=5000000)
except Exception as e:
    print(f"Emulation stopped: {e}")
    print(f"RIP=0x{uc.reg_read(UC_X86_REG_RIP):x}")
```

### Assemble and verify encoding (Keystone)

```python
from keystone import Ks, KS_ARCH_X86, KS_MODE_64

ks = Ks(KS_ARCH_X86, KS_MODE_64)

# Verify a syscall stub encodes correctly
asm = """
    mov r10, rcx
    mov eax, 0x18       ; NtAllocateVirtualMemory SSN (example)
    syscall
    ret
"""
encoding, count = ks.asm(asm)
print(f"{count} insns, {len(encoding)} bytes")
print("bytes:", " ".join(f"{b:02x}" for b in encoding))
```

### Gadget finder

```python
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

def find_gadgets(path, pattern_bytes, context=3):
    """Find byte patterns in binary and disassemble surrounding context."""
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    data = open(path, "rb").read()
    results = []
    idx = 0
    while True:
        idx = data.find(pattern_bytes, idx)
        if idx == -1:
            break
        start = max(0, idx - 8)
        chunk = data[start:idx + len(pattern_bytes) + 8]
        insns = list(md.disasm(chunk, start))
        results.append((idx, insns))
        idx += 1
    return results

# Find syscall;ret (0F 05 C3)
for offset, insns in find_gadgets("ntdll.dll", b"\x0f\x05\xc3"):
    print(f"\n--- gadget at offset 0x{offset:x} ---")
    for i in insns:
        marker = " <--" if i.address == offset else ""
        print(f"  0x{i.address:x}: {i.mnemonic} {i.op_str}{marker}")

# Find jmp [rbx] (FF 23)
for offset, insns in find_gadgets("kernelbase.dll", b"\xff\x23"):
    print(f"jmp [rbx] at offset 0x{offset:x}")
```

### PE export resolver

```python
import pefile

def resolve_export(dll_path, func_name):
    """Find RVA of an exported function."""
    pe = pefile.PE(dll_path)
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if exp.name and exp.name.decode() == func_name:
            return exp.address
    return None

rva = resolve_export("ntdll.dll", "NtAllocateVirtualMemory")
print(f"NtAllocateVirtualMemory RVA = 0x{rva:x}")
```

### SSN extractor

```python
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

def extract_ssns(ntdll_path):
    """Extract System Service Numbers from ntdll stubs."""
    pe = pefile.PE(ntdll_path)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    base = pe.OPTIONAL_HEADER.ImageBase
    ssns = {}

    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if not exp.name or not exp.name.decode().startswith("Nt"):
            continue
        name = exp.name.decode()
        if name.startswith("Ntdll"):
            continue
        rva = exp.address
        offset = pe.get_offset_from_rva(rva)
        stub = pe.get_data(rva, 24)
        insns = list(md.disasm(stub, base + rva))
        for i in insns[:5]:
            if i.mnemonic == "mov" and "eax" in i.op_str:
                # Extract immediate value (SSN)
                ssn = int(i.op_str.split(",")[1].strip(), 0)
                ssns[name] = ssn
                break
    return ssns

for name, ssn in sorted(extract_ssns("ntdll.dll").items()):
    print(f"{name}: SSN=0x{ssn:04x}")
```

---

## 2. Frida Dynamic Instrumentation Patterns

Frida hooks are useful when you need to test behavior in a live process without rebuilding.

### Monitor syscall stub invocations

```javascript
// Hook every Nt* export in ntdll
var ntdll = Process.getModuleByName("ntdll.dll");
var exports = ntdll.enumerateExports();
exports.filter(e => e.name.startsWith("Nt") && e.type === "function")
       .forEach(e => {
    Interceptor.attach(e.address, {
        onEnter(args) {
            this.name = e.name;
            this.rsp = this.context.rsp;
        },
        onLeave(retval) {
            if (retval.toInt32() < 0)  // NTSTATUS failure
                console.log(`${this.name} FAILED: 0x${retval.toString(16)}`);
        }
    });
});
```

### Verify stack alignment at runtime

```javascript
// Attach to your custom trampoline; alert on misalignment
Interceptor.attach(ptr("0x<trampoline_addr>"), {
    onEnter() {
        var rsp = this.context.rsp;
        var aligned = rsp.and(0xF).toInt32() === 0;
        if (!aligned) {
            console.log("[!] MISALIGNED RSP=0x" + rsp.toString(16));
            console.log("    Thread " + Process.getCurrentThreadId());
            console.log(Thread.backtrace(this.context, Backtracer.ACCURATE)
                .map(DebugSymbol.fromAddress).join("\n    "));
        }
    }
});
```

### Dump memory region after allocation

```javascript
Interceptor.attach(Module.findExportByName("ntdll.dll", "NtAllocateVirtualMemory"), {
    onEnter(args) {
        this.basePtr = args[1];
        this.sizePtr = args[3];
    },
    onLeave(retval) {
        if (retval.toInt32() === 0) {
            var base = this.basePtr.readPointer();
            var size = this.sizePtr.readPointer().toInt32();
            console.log(`Allocated 0x${size.toString(16)} at ${base}`);
            if (size <= 0x100)
                console.log(hexdump(base, {length: size}));
        }
    }
});
```

### Trace gadget execution

```javascript
// Set hooks on known gadgets to verify they execute in the right order
var gadgets = [
    {name: "syscall;ret", addr: ptr("0x<addr1>")},
    {name: "jmp [rbx]",   addr: ptr("0x<addr2>")},
    {name: "add rsp,X",   addr: ptr("0x<addr3>")},
];

gadgets.forEach(g => {
    Interceptor.attach(g.addr, {
        onEnter() {
            console.log(`[*] Hit gadget: ${g.name} at ${g.addr}`);
            console.log(`    RSP=0x${this.context.rsp} RBX=0x${this.context.rbx}`);
        }
    });
});
```

---

## 3. Common Offensive ASM Bug Diagnosis

### Decision tree: crash in offensive ASM

```
Crash in ASM stub
├── ACCESS_VIOLATION (0xC0000005)
│   ├── RIP in unexpected location → gadget address wrong
│   │   └── Verify gadget: u <addr> L3 — is it syscall;ret or jmp [rbx]?
│   ├── RSP points to freed/unmapped memory → stack restore failed
│   │   └── Check fixup label reached; verify RSP save/restore
│   └── Accessing memory via register with bad value → arg passing error
│       └── Step through: did the context struct get loaded correctly?
├── STATUS_STACK_BUFFER_OVERRUN (0xC0000409)
│   └── CALL with misaligned RSP
│       └── Check rsp % 16 at every CALL site; check heap buffer alignment
├── BSOD / STATUS_INVALID_SYSTEM_SERVICE
│   └── Wrong SSN in RAX
│       └── Verify SSN matches target Windows build (SSNs change per build)
├── Hang (no crash, no return)
│   ├── Fixup label never reached → ROP chain broken
│   │   └── Set bp on fixup; check each RET target in chain
│   └── Infinite loop in stub → wrong conditional jump
│       └── Trace record to find the loop
└── Silent corruption (no crash, wrong results)
    ├── Callee-saved register clobbered → caller variable corrupted later
    │   └── Compare regs at entry vs exit of stub
    └── NTSTATUS return ignored → upstream assumes success
        └── Always check RAX after syscall; non-zero = failure
```

### UNWIND_INFO verification

When building synthetic stack frames for stack spoofing, frame sizes must match the target function's UNWIND_INFO:

```python
import pefile

def dump_unwind_info(pe_path, func_name):
    """Dump RUNTIME_FUNCTION and UNWIND_INFO for a function."""
    pe = pefile.PE(pe_path)
    # Find the function RVA from exports
    rva = None
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if exp.name and exp.name.decode() == func_name:
            rva = exp.address
            break
    if not rva:
        print(f"{func_name} not found")
        return

    # Parse .pdata for RUNTIME_FUNCTION entries
    pdata = next((s for s in pe.sections if b".pdata" in s.Name), None)
    if not pdata:
        print("No .pdata section")
        return

    data = pdata.get_data()
    base = pe.OPTIONAL_HEADER.ImageBase
    for i in range(0, len(data) - 12, 12):
        begin_rva = int.from_bytes(data[i:i+4], "little")
        end_rva = int.from_bytes(data[i+4:i+8], "little")
        unwind_rva = int.from_bytes(data[i+8:i+12], "little")
        if begin_rva <= rva < end_rva:
            print(f"RUNTIME_FUNCTION for {func_name}:")
            print(f"  BeginAddress: 0x{begin_rva:x}")
            print(f"  EndAddress:   0x{end_rva:x}")
            print(f"  UnwindInfoRVA: 0x{unwind_rva:x}")
            # Read UNWIND_INFO header
            ui_offset = pe.get_offset_from_rva(unwind_rva)
            ui = pe.get_data(unwind_rva, 4)
            version = ui[0] & 0x7
            flags = (ui[0] >> 3) & 0x1F
            prolog_size = ui[1]
            code_count = ui[2]
            frame_register = ui[3] & 0xF
            frame_offset = (ui[3] >> 4) * 16
            print(f"  Version: {version}, Flags: {flags}")
            print(f"  PrologSize: {prolog_size}")
            print(f"  CodeCount: {code_count}")
            print(f"  FrameRegister: {frame_register}, FrameOffset: {frame_offset}")
            return

dump_unwind_info("kernel32.dll", "BaseThreadInitThunk")
```

---

## 4. Reverse Engineering Own Binaries

When shipping stripped binaries, you may need to reverse-engineer your own release build to find a bug.

### Strategy

1. **Keep a debug build and PDB/DWARF alongside release** — diff the two when something breaks
2. **Map file** — generate `/MAP` (MSVC) or `-Wl,-Map=output.map` (GCC) to correlate addresses with symbols
3. **Binary diff** — compare old (working) vs new (broken) object files:
   ```bash
   # Linux: byte-by-byte diff
   cmp -l old.o new.o
   # Windows: FC in hex mode
   fc /b old.obj new.obj
   # Better: radiff2 from radare2
   radiff2 -g old.o new.o > diff.dot
   ```
4. **Check .pdata coverage** — if your ASM stub needs proper stack unwinding (e.g., for stack spoofing to work), verify RUNTIME_FUNCTION covers it:
   ```
   dumpbin /unwindinfo loader.dll | findstr my_stub
   ```
5. **PE section validation** — ensure injected code lands in an executable section and at the expected offset:
   ```python
   import pefile
   pe = pefile.PE("loader.dll")
   for s in pe.sections:
       flags = ""
       if s.Characteristics & 0x20000000: flags += "X"
       if s.Characteristics & 0x40000000: flags += "R"
       if s.Characteristics & 0x80000000: flags += "W"
       print(f"{s.Name.decode().strip():10s} VA=0x{s.VirtualAddress:x} "
             f"Size=0x{s.Misc_VirtualSize:x} Flags={flags}")
   ```

### Version-specific debugging

Offensive tools often break across Windows versions because SSNs, struct layouts, and undocumented offsets change. Maintain a version matrix:

```python
# ssn_matrix.py — track SSNs per Windows build
SSNS = {
    "NtAllocateVirtualMemory": {
        "10.0.19041": 0x18,  # 20H1
        "10.0.19045": 0x18,  # 22H2
        "10.0.22621": 0x18,  # Win11 22H2
        "10.0.26100": 0x18,  # Win11 24H2
    },
    "NtCreateThreadEx": {
        "10.0.19041": 0xC7,
        "10.0.19045": 0xC7,
        "10.0.22621": 0xCF,
        "10.0.26100": 0xCF,
    },
}

def get_ssn(func, build):
    return SSNS.get(func, {}).get(build)
```

---

## 5. DBI Frameworks Comparison

| Feature | Frida | Intel PIN | DynamoRIO |
|---------|-------|-----------|-----------|
| API | JavaScript/Python/C | C/C++ | C/C++ |
| Platforms | Win/Linux/macOS/iOS/Android | Win/Linux (x86/x64) | Win/Linux (x86/x64/ARM) |
| Granularity | Function + instruction | Instruction | Basic block + instruction |
| Overhead | Medium-High | High (10-20×) | Medium (2-10×) |
| Detectability | Low (easily fingerprinted) | Medium | Medium |
| Best for | Quick hooks, API monitoring | Deep instruction tracing | Runtime analysis, sandboxing |
| Syscall tracing | Via API hooks | Via syscall callbacks | Via syscall callbacks |

### When to use each

- **Quick triage / API monitoring** → Frida (fastest to write, scriptable)
- **Full instruction trace / coverage** → DynamoRIO or PIN (more overhead but complete)
- **Emulation without execution** → Unicorn (safest; no side effects)
- **Static analysis + gadget finding** → Capstone + pefile (offline, scriptable)
