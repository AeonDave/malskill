# CTF Reverse - Advanced Tools & Deobfuscation

Canonical advanced-tooling reference for deobfuscation, packers/protectors, diffing, symbolic execution, advanced debugger automation, scripting, and binary patching.

## Table of Contents
- [VMProtect Analysis](#vmprotect-analysis)
  - [Recognition](#recognition)
  - [Approach](#approach)
  - [Tools](#tools)
  - [CTF Strategy](#ctf-strategy)
- [Themida / WinLicense Analysis](#themida-winlicense-analysis)
  - [Themida Recognition](#themida-recognition)
  - [Approach for CTF](#approach-for-ctf)
- [Binary Diffing](#binary-diffing)
  - [BinDiff](#bindiff)
  - [Diaphora](#diaphora)
- [Deobfuscation Frameworks](#deobfuscation-frameworks)
  - [D-810 (IDA)](#d-810-ida)
  - [GOOMBA (Ghidra)](#goomba-ghidra)
  - [Miasm](#miasm)
- [Qiling Framework (Emulation)](#qiling-framework-emulation)
- [Triton (Dynamic Symbolic Execution)](#triton-dynamic-symbolic-execution)
- [Manticore (Symbolic Execution)](#manticore-symbolic-execution)
- [Rizin / Cutter](#rizin-cutter)
- [RetDec (Retargetable Decompiler)](#retdec-retargetable-decompiler)
- [Custom VM Bytecode Lifting to LLVM IR](#custom-vm-bytecode-lifting-to-llvm-ir)
- [Advanced GDB Techniques](#advanced-gdb-techniques)
- [Advanced Ghidra Scripting](#advanced-ghidra-scripting)
- [Patching Strategies](#patching-strategies)
- [GDB Constraint Extraction with ILP/LP Solver](#gdb-constraint-extraction-with-ilplp-solver)
- [GDB Position-Encoded Input with Zero Flag Monitoring](#gdb-position-encoded-input-with-zero-flag-monitoring)
- [LD_PRELOAD to Dump Execute-Only Binary](#ld_preload-to-dump-execute-only-binary)
- [PEDA current_inst Bit-by-Bit Flag Scraper](#peda-current_inst-bit-by-bit-flag-scraper)

## VMProtect Analysis

VMProtect virtualizes x86/x64 code into custom bytecode interpreted by a generated VM. One of the most challenging protectors in CTF.

### Recognition

```bash
# VMProtect signatures
strings binary | grep -i "vmp\|vmprotect"
# PE sections:.vmp0,.vmp1 (VMProtect adds its own sections)
readelf -S binary | grep ".vmp"
# Large binary with entropy > 7.5 in certain sections
```

**Key indicators:**
- `push` / `pop` heavy prologues (VM entry pushes all registers to stack)
- Large switch-case dispatcher (the VM handler loop)
- Anti-debug checks embedded in VM handlers
- Mutation engine: same opcode has different handlers per build

### Approach

```text
1. Identify VM entry points — look for pushad/pushaq-like sequences
2. Find the handler table — large indirect jump (jmp [reg + offset])
3. Trace handler execution — each handler ends with jump to next
4. Identify handlers:
   - vAdd, vSub, vMul, vXor, vNot (arithmetic)
   - vPush, vPop (stack operations)
   - vLoad, vStore (memory access)
   - vJmp, vJcc (control flow)
   - vRet (VM exit — restores real registers)
5. Build disassembler for VM bytecode
6. Simplify / deobfuscate the lifted IL
```

### Tools

- **VMPAttack** (IDA plugin): Automatically identifies VM handlers
- **NoVmp**: Devirtualization via VTIL (open-source)
- **VMProtect devirtualizer scripts**: Community IDA/Binary Ninja scripts
- **Approach For lab-style tasks:** Often easier to trace specific operations (crypto, comparisons) than fully devirtualize

### CTF Strategy

```python
# Trace VM execution dynamically to extract operations on flag
# Hook VM handler dispatch to log opcode + operands

import frida

script = """
var vm_dispatch = ptr('0x...');  // Address of handler table jump
Interceptor.attach(vm_dispatch, {
    onEnter(args) {
        // Log handler index and stack state
        var handler_idx = this.context.rax;  // or whichever register
        console.log('Handler:', handler_idx, 'RSP:', this.context.rsp);
    }
});
"""
```

**Key insight:** Full devirtualization is rarely needed for CTF. Focus on tracing what operations are performed on your input. Hook comparison/crypto functions called from within the VM.

-

## Themida / WinLicense Analysis

Similar to VMProtect but with additional anti-debug layers.

### Themida Recognition
- Sections: `.themida`, `.winlice`
- Extremely heavy anti-debug (kernel-level checks, driver installation)
- Code mutation + virtualization + packing combined

### Approach for CTF
1. **Dump unpacked code:** Let it run, dump process memory after unpacking
2. **Bypass anti-debug:** ScyllaHide in x64dbg with Themida-specific preset
3. **Fix imports:** Use Scylla plugin for IAT reconstruction
4. **Focus on dumped code:** Once unpacked, analyze as normal binary

```bash
# x64dbg workflow for Themida:
1. Load binary
2. Enable ScyllaHide → Profile: Themida
3. Run to OEP (Original Entry Point) — may need several attempts
4. Dump with Scylla: OEP → IAT Autosearch → Get Imports → Dump
5. Fix dump: Scylla → Fix Dump
6. Analyze fixed dump in Ghidra/IDA
```

-

## Binary Diffing

Critical for patch analysis, 1-day exploit development, and challenges that provide two versions of a binary.

### BinDiff

```bash
# Export from IDA/Ghidra first, then diff
# IDA: File → BinExport → Export as BinExport2
# Ghidra: Use BinExport plugin

# Command line diffing
bindiff primary.BinExport secondary.BinExport
# Opens in BinDiff GUI — shows matched/unmatched functions
```

**Key metrics:**
- Similarity score (0.0-1.0) per function pair
- Changed instructions highlighted
- Unmatched functions = new/removed code

### Diaphora

Free, open-source alternative to BinDiff, runs as IDA plugin.

```bash
# In IDA:
# File → Script file → diaphora.py
# Export first binary, then open second and diff

# Ghidra version: diaphora_ghidra.py
```

**Useful For lab-style tasks:** When Artifact set provides "patched" and "original" binaries, diff reveals the vulnerability or hidden functionality.

-

## Deobfuscation Frameworks

### D-810 (IDA)

Pattern-based deobfuscation plugin for IDA Pro. Excellent for OLLVM-obfuscated binaries.

```text
Capabilities:
- MBA simplification: (a ^ b) + 2*(a & b) → a + b
- Dead code elimination
- Opaque predicate removal
- Constant folding
- Control flow unflattening (partial)

Installation: Copy to IDA plugins directory
Usage: Edit → Plugins → D-810 → Select rules → Apply
```

### GOOMBA (Ghidra)

```text
GOOMBA (Ghidra-based Obfuscated Object Matching and Bytes Analysis):
- Integrates with Ghidra's P-Code
- Simplifies MBA expressions
- Pattern matching for known obfuscation

Installation: Copy.jar to Ghidra extensions
Usage: Code Browser → Analysis → GOOMBA
```

### Miasm

Powerful reverse engineering framework with symbolic execution and IR lifting.

```python
from miasm.analysis.binary import Container
from miasm.analysis.machine import Machine
from miasm.expression.expression import *

# Load binary and lift to Miasm IR
cont = Container.from_stream(open("binary", "rb"))
machine = Machine(cont.arch)
mdis = machine.dis_engine(cont.bin_stream, loc_db=cont.loc_db)

# Disassemble function
asmcfg = mdis.dis_multiblock(entry_addr)

# Lift to IR
lifter = machine.lifter_model_call(loc_db=cont.loc_db)
ircfg = lifter.new_ircfg_from_asmcfg(asmcfg)

# Symbolic execution
from miasm.ir.symbexec import SymbolicExecutionEngine
sb = SymbolicExecutionEngine(lifter)
# Execute symbolically, then simplify expressions
```

**Use case:** Deobfuscate expression trees, simplify complex arithmetic, trace data flow through obfuscated code.

-

## Qiling Framework (Emulation)

Cross-platform emulation framework built on Unicorn, with OS-level support (syscalls, filesystem, registry).

```python
from qiling import Qiling
from qiling.const import QL_VERBOSE

# Emulate Linux ELF
ql = Qiling(["./binary"], "rootfs/x8664_linux",
            verbose=QL_VERBOSE.DEBUG)

# Hook specific address
@ql.hook_address
def hook_check(ql, address, size):
    if address == 0x401234:
        ql.arch.regs.rax = 0  # Bypass check
        ql.log.info("Anti-debug bypassed")

# Hook syscall
@ql.hook_syscall(name="ptrace")
def hook_ptrace(ql, request, pid, addr, data):
    return 0  # Always succeed

# Hook API (Windows)
@ql.set_api("IsDebuggerPresent", target=ql.os.user_defined_api)
def hook_isdebug(ql, address, params):
    return 0

ql.run()
```

**Advantages over Unicorn:**
- OS emulation (file I/O, network, registry)
- Multi-platform (Linux, Windows, macOS, Android, UEFI)
- Built-in debugger interface
- Rootfs for library loading

**CTF use cases:**
- Emulate binaries for foreign architectures (ARM, MIPS, RISC-V)
- Bypass all anti-debug at once (no debugger artifacts)
- Fuzz embedded/IoT firmware without hardware
- Trace execution without code modification

-

## Triton (Dynamic Symbolic Execution)

Pin-based dynamic binary analysis framework with symbolic execution, taint analysis, and AST simplification.

```python
from triton import *

ctx = TritonContext(ARCH.X86_64)

# Load binary sections
with open("binary", "rb") as f:
    binary = f.read()
ctx.setConcreteMemoryAreaValue(0x400000, binary)

# Symbolize input
for i in range(32):
    ctx.symbolizeMemory(MemoryAccess(INPUT_ADDR + i, CPUSIZE.BYTE), f"input_{i}")

# Emulate instructions
pc = ENTRY_POINT
while pc:
    inst = Instruction(pc, ctx.getConcreteMemoryAreaValue(pc, 16))
    ctx.processing(inst)

    # At comparison point, extract path constraint
    if pc == CMP_ADDR:
        ast = ctx.getPageneric caseonstraintsAst()
        model = ctx.getModel(ast)
        for k, v in sorted(model.items()):
            print(f"input[{k}] = {chr(v.getValue())}", end="")
        break

    pc = ctx.getConcreteRegisterValue(ctx.registers.rip)
```

**Triton vs angr:**
| Feature | Triton | angr |
|-|-|-|
| Execution | Concrete + symbolic (DSE) | Fully symbolic |
| Speed | Faster (concrete-driven) | Slower (explores all paths) |
| Path explosion | Less prone (follows one path) | Major issue |
| API | C++ / Python | Python |
| Best for | Single-path deobfuscation, taint tracking | Multi-path exploration |

**Key use:** Triton excels at deobfuscation — run the program concretely, but track symbolic state, then simplify the collected constraints.

-

## Manticore (Symbolic Execution)

Trail of Bits' symbolic execution tool. Similar to angr but with native EVM (Ethereum) support.

```python
from manticore.native import Manticore

m = Manticore("./binary")

# Hook success/failure
@m.hook(0x401234)
def success(state):
    buf = state.solve_one_n_batched(state.input_symbols, 32)
    print("Flag:", bytes(buf))
    m.kill()

@m.hook(0x401256)
def fail(state):
    state.abandon()

m.run()
```

**Best for:** EVM/smart contract analysis, simpler Linux binaries. angr is generally more mature for complex RE tasks.

-

## Rizin / Cutter

Rizin is the maintained fork of radare2. Cutter is its Qt-based GUI.

```bash
# Rizin CLI (r2-compatible commands)
rizin -d./binary
> aaa                    # Analyze all
> afl                    # List functions
> pdf @ main             # Print disassembly
> VV                     # Visual graph mode

# Cutter GUI
cutter binary           # Open in GUI with decompiler
```

**Cutter advantages:**
- Built-in Ghidra decompiler (via r2ghidra plugin)
- Graph view, hex editor, debug panel in one GUI
- Integrated Python/JavaScript scripting console
- Free and open source

-

## RetDec (Retargetable Decompiler)

LLVM-based decompiler supporting many architectures. Free and open-source.

```bash
# Install
pip install retdec-decompiler
# Or use web: https://retdec.com/decompilation/

# CLI
retdec-decompiler binary
# Outputs: binary.c (decompiled C), binary.dsm (disassembly)

# Specific function
retdec-decompiler -select-ranges 0x401000-0x401100 binary
```

**Strengths:** Multi-arch support (x86, ARM, MIPS, PowerPC, PIC32), free, produces compilable C. Good for architectures not well-supported by Ghidra.

-

## Custom VM Bytecode Lifting to LLVM IR

For complex custom VMs, transpile the VM bytecode to LLVM IR and use LLVM's optimization passes to simplify the code, then decompile the optimized IR.

```python
# Pipeline: VM bytecode → custom disassembler → LLVM IR → optimize → decompile
# 1. Write disassembler for the custom VM opcodes
# 2. Emit LLVM IR for each opcode:
#    INC reg  → %reg = add i32 %reg, 1
#    CDEC reg → conditional decrement
#    CALL fn  → call void @fn()
# 3. Use MCJIT or llc to optimize:
#    opt -O3 -S vm_lifted.ll -o vm_optimized.ll
# 4. Load optimized IR in IDA or decompile with RetDec
# Result: 1300 lines → 150 lines after inlining + constant folding
```

**Key insight:** LLVM's optimization passes (inlining, constant folding, dead code elimination) dramatically simplify lifted VM bytecode. A custom VM with 26 registers and 3 opcodes that produces 1300 lines of IL reduces to ~150 lines after `-O3`, revealing the underlying algorithm (e.g., Collatz sequence computation).

-

## Advanced GDB Techniques

### Python Scripting

```python
# ~/.gdbinit or source from GDB
import gdb

class TraceCompare(gdb.Breakpoint):
    """Log all comparison operations."""
    def __init__(self, addr):
        super().__init__(f"*{addr}", gdb.BP_BREAKPOINT)

    def stop(self):
        frame = gdb.selected_frame()
        rdi = int(frame.read_register("rdi"))
        rsi = int(frame.read_register("rsi"))
        rdx = int(frame.read_register("rdx"))
        inferior = gdb.selected_inferior()
        buf1 = inferior.read_memory(rdi, rdx).tobytes()
        buf2 = inferior.read_memory(rsi, rdx).tobytes()
        print(f"memcmp({buf1!r}, {buf2!r}, {rdx})")
        return False
```

### Brute-Force with GDB Script

```python
import gdb, string

def bruteforce_flag(check_addr, success_addr, fail_addr, flag_len):
    flag = []
    for pos in range(flag_len):
        for ch in string.printable:
            candidate = ''.join(flag) + ch + 'A' * (flag_len - pos - 1)
            gdb.execute('start', to_string=True)
            gdb.execute(f'b *{check_addr}', to_string=True)
            gdb.execute('continue', to_string=True)
            rip = int(gdb.parse_and_eval('$rip'))
            if rip == success_addr:
                flag.append(ch)
                break
        gdb.execute('delete breakpoints', to_string=True)
    return ''.join(flag)
```

### Conditional Breakpoints

```bash
(gdb) b *0x401234 if $rax == 0x41
(gdb) b *0x401234 if *(char*)$rdi == 'f'
(gdb) b *0x401234
(gdb) ignore 1 99
```

### Watchpoints

```bash
(gdb) watch *(int*)0x601050
(gdb) rwatch *(int*)0x601050
(gdb) awatch *(int*)0x601050
```

### Reverse Debugging (rr)

```bash
rr record ./binary
rr replay
```

### GDB Dashboard / GEF / pwndbg

```bash
pwndbg> context
pwndbg> vmmap
pwndbg> search -s "flag{"
pwndbg> telescope $rsp 20
```

-

## Advanced Ghidra Scripting

```python
from ghidra.program.model.symbol import SourceType

fm = currentProgram.getFunctionManager()
for func in fm.getFunctions(True):
    if func.getName().startswith("FUN_"):
        body = func.getBody()
        inst_iter = currentProgram.getListing().getInstructions(body, True)
        for inst in inst_iter:
            if inst.getMnemonicString() == "CPUID":
                func.setName("anti_vm_check_" + hex(func.getEntryPoint().getOffset()),
                            SourceType.USER_DEFINED)
                break
```

-

## Patching Strategies

### Binary Ninja Patching (Python API)

```python
import binaryninja as bn

bv = bn.open_view("binary")
bv.write(0x401234, b"\x90" * 5)
bv.save("patched")
```

### LIEF (Library for Instrumenting Executable Formats)

```python
import lief

binary = lief.parse("binary")
binary.header.entrypoint = 0x401000
binary.write("patched")
```

-

## GDB Constraint Extraction with ILP/LP Solver

When a binary enforces linear arithmetic relationships between input bytes, extract constraints automatically via GDB and solve with an ILP solver.

```python
from pulp import *

n = 32
prob = LpProblem("crackme", LpMinimize)
x = [LpVariable(f'x{i}', 32, 126, cat='Integer') for i in range(n)]
prob += 0
prob += x[3] + x[7] == 0xAB
prob += x[1] - x[5] == 0x0C
prob.solve(PULP_CBC_CMD(msg=0))
```

**Key insight:** Position-encoded test inputs plus automated comparison logging turn linear validators into direct ILP instances.

-

## GDB Position-Encoded Input with Zero Flag Monitoring

Send input where `input[i] = i` and monitor the zero flag after comparisons to recover expected values in a single pass.

```python
import gdb

class ZFMonitor(gdb.Breakpoint):
    def stop(self):
        zf = (int(gdb.parse_and_eval('$eflags')) >> 6) & 1
        if zf:
            rip = int(gdb.parse_and_eval('$rip'))
            disasm = gdb.execute(f'x/1i {rip-5}', to_string=True)
            print(f"ZF set at {rip:#x}: {disasm.strip()}")
        return False
```

-

## LD_PRELOAD to Dump Execute-Only Binary

A binary has execute-only permissions and cannot be read directly, but its mapped memory remains accessible from inside the process.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

__attribute__((constructor)) void dump() {
    FILE *maps = fopen("/proc/self/maps", "r");
    char line[256];
    unsigned long base = 0, end = 0;
    while (fgets(line, sizeof(line), maps)) {
        if (strstr(line, "binary_name")) {
            sscanf(line, "%lx-%lx", &base, &end);
            break;
        }
    }
    fclose(maps);
}
```

**Key insight:** Execute-only prevents file reads, not self-introspection via `/proc/self/mem`.

-

## PEDA current_inst Bit-by-Bit Flag Scraper

**Pattern:** A large validator dispatches one checker per flag bit. Rather than decompile every wrapper, drive GDB+PEDA to step through the dispatcher and read `edi` / `eax` directly.

```python
def get_current_inst():
    return peda.current_inst(peda.getreg("rip"))[1]

peda.execute('file ./elementary')
peda.set_breakpoint(0x555555554000 + 0xCEB88)
```

**Key insight:** If the validator reduces every bit check to a black-box oracle, scrape the dispatcher rather than the individual checkers.
