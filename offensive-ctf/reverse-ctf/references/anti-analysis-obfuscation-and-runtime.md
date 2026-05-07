# CTF Reverse - Anti-Analysis Obfuscation and Runtime Tricks

Focused anti-analysis reference for anti-disassembly, layered bypass playbooks, and challenge-specific runtime handler techniques.

## Table of Contents
- [Anti-Disassembly Techniques](#anti-disassembly-techniques)
- [Comprehensive Bypass Strategies](#comprehensive-bypass-strategies)
- [Challenge Runtime and Writeup Tactics](#challenge-runtime-and-writeup-tactics)

## Anti-Disassembly Techniques

### Opaque Predicates

```asm
mov eax, [some_memory]
imul eax, eax
and eax, 1
jnz fake_branch
```

**Identification:** Z3/SMT can prove branch is always/never taken.

### Junk Bytes / Overlapping Instructions

```asm
jmp real_code
db 0xE8
real_code:
mov eax, 1
```

**Fix:** Switch to graph-mode disassembly (Ghidra/IDA handle this well). Manual: undefine and re-analyze from correct offset.

### Jump-in-the-Middle

```asm
eb 01
e8
90
```

### Function Chunking / Scattered Code

Functions split into non-contiguous chunks connected by unconditional jumps. Defeats linear function boundary detection.

**Tool:** IDA's "Append function tail" or Ghidra's "Create function" at each chunk.

### Control Flow Flattening (Advanced)

Beyond basic switch-case (see patterns.md): modern OLLVM variants use:
- **Bogus control flow:** Fake branches with opaque predicates
- **Instruction substitution:** `a + b` → `a - (-b)`, `a ^ b` → `(a | b) & ~(a & b)`
- **String encryption:** Strings decrypted at runtime, cleared after use

**Deobfuscation tools:**
- **D-810** (IDA plugin): Pattern-based deobfuscation, MBA simplification
- **GOOMBA** (Ghidra): Automated deobfuscation for OLLVM
- **Miasm**: Symbolic execution for deobfuscation
- **Arybo** / **SiMBA**: MBA expression simplification

```bash
# D-810: install in IDA plugins directory, Edit → Plugins → D-810
# Simplifies MBA expressions: (a | b) & ~(a & b) → a ^ b
# Removes opaque predicates via pattern matching
```

### Mixed Boolean-Arithmetic (MBA) Identification & Simplification

```python
# Common MBA patterns and their simplified forms:
# (x & y) + (x | y) == x + y
# (x ^ y) + 2*(x & y) == x + y
# (x | y) - (x & ~y) == y
# ~(~x & ~y) == x | y (De Morgan's)
# (x | y) & ~(x & y) == x ^ y

from simba import simplify_mba
expr = "(a | b) + (a & b) - (~a & b)"
print(simplify_mba(expr))  # → a
```

The sections below extend the core taxonomy with challenge-specific runtime handler tricks, tracing shortcuts, and dump-oriented bypasses.

-

## Comprehensive Bypass Strategies

### Universal Bypass Checklist

1. **Identify all anti-analysis checks** — search for: `ptrace`, `IsDebuggerPresent`, `rdtsc`, `cpuid`, `NtQuery`, `GetTickCount`, `CheckRemoteDebuggerPresent`, `/proc/self`, `SIGTRAP`, `alarm`
2. **Static patching** — NOP/patch checks with pwntools or Ghidra before running
3. **LD_PRELOAD** (Linux) — hook libc functions returning fake values
4. **ScyllaHide** (Windows x64dbg) — patches PEB, hooks NT functions automatically
5. **Emulation** (Unicorn/Qiling) — no debugger artifacts to detect
6. **Kernel-level bypass** — modify `/proc/sys/kernel/yama/ptrace_scope`, use `prctl`

### Layered Anti-Debug (Real-World Pattern)

Many challenges stack multiple checks:
```text
1. TLS callback → IsDebuggerPresent (before main)
2. main() → ptrace(TRACEME)
3. Watchdog thread → timing check + /proc scan
4. Code section → self-CRC32 integrity
5. Signal handler → real logic in SIGSEGV handler
```

**Approach:** Identify ALL checks before patching. Patch or hook each one systematically. Run under emulator if too many to patch individually.

### Quick Reference: Check to Bypass

| Anti-Debug Check | Platform | Bypass |
|-|-|-|
| `ptrace(TRACEME)` | Linux | `LD_PRELOAD`, patch to `ret 0`, `catch syscall` |
| `IsDebuggerPresent` | Windows | ScyllaHide, Frida hook, PEB patch |
| `NtQueryInformationProcess` | Windows | ScyllaHide, hook ntdll |
| `rdtsc` timing | Both | NOP rdtsc, Frida time hook, Pin |
| `/proc/self/status` | Linux | Mount namespace, hook fopen |
| `alarm(N)` | Linux | `handle SIGALRM ignore` in GDB |
| `SIGTRAP` handler | Linux | `handle SIGTRAP nostop pass` |
| `SIGFPE` handler side-channel | Linux | `strace -e signal=SIGFPE` count per input |
| TLS callback | Windows | Break on TLS in x64dbg, patch |
| DR register scan | Windows | Use software BPs, hook GetThreadContext |
| INT3 scan / CRC | Both | Hardware BPs, patch CRC comparison |
| Frida detection | Both | Early-load gadget, hook strstr |
| CPUID hypervisor | Both | Patch CPUID result, bare metal |
| Thread hiding | Windows | Hook NtSetInformationThread |

-

### Trap-Flag Self-Check with cmovz Patcher

**Pattern:** The binary checks `EFLAGS` by doing `pushf; pop edx; and edx, 0x100` (isolating the single-step Trap Flag) and using the result inside a `cmovz` so the correct instruction is overwritten only when the TF bit is clear. Single-stepping in gdb leaves TF set, the `cmovz` never fires, and the program silently runs the wrong code path without crashing.

```asm
check_debugger:
    pushf
    pop   edx
    and   edx, 0x100
    test  edx, edx
    cmovz eax, ebx
    mov   [rip+target], eax
```

**Bypass with hardware breakpoints:**
```gdb
(gdb) hbreak *0x56557267
(gdb) run
(gdb) # inspect EAX at the hbreak — the patched value is now written
```

**Key insight:** `pushf; pop reg; and reg, 0x100` is the cleanest way to check TF without triggering a trap. Hardware breakpoints let the instruction run in normal mode.

-

### SIGFPE Handler for mprotect Code Mutation

**Pattern:** The binary installs a custom `SIGFPE` handler with `sys_sigaction` and arranges for an arithmetic instruction to trap. The handler marks `.text` writable with `mprotect` and mutates code that would otherwise stay constant.

```c
void on_fpe(int sig, siginfo_t *info, void *uap) {
    ucontext_t *ctx = uap;
    void *page = (void *)((uintptr_t)ctx->uc_mcontext.gregs[REG_RIP] & ~0xfff);
    mprotect(page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    *((uint32_t *)(page + 0x42)) = 0xDEADBEEF;
}
```

**Bypass:**
```bash
gdb./challenge
(gdb) handle SIGFPE nostop noprint pass
(gdb) break *on_fpe
(gdb) run
```

**Key insight:** Signal handlers that `mprotect` + mutate code are cross-delimited in a way decompilers cannot model.

-

## Challenge Runtime and Writeup Tactics

### SIGILL Handler for Execution Mode Switching

Binaries may install SIGILL handlers to switch between x86 and x86-64 execution modes or implement custom opcode dispatch.

```c
void sigill_handler(int sig, siginfo_t *info, void *ucontext) {
    ucontext_t *ctx = (ucontext_t *)ucontext;
    unsigned char *pc = (unsigned char *)ctx->uc_mcontext.gregs[REG_RIP];
    ctx->uc_mcontext.gregs[REG_RIP] += opcode_length;
}
```

**Key insight:** If a binary installs signal handlers for SIGILL/SIGSEGV/SIGTRAP early in execution, suspect custom instruction dispatch.

-

### SIGFPE Signal Handler Side-Channel via strace Counting

Binary uses SIGFPE signal handlers for control flow, making static analysis unreliable. Brute-force by counting SIGFPE signals via strace.

```bash
for c in {a..z} {A..Z} {0..9}; do
    count=$(echo -n "${c}AAAAAAA" | strace -e signal=SIGFPE ./binary 2>&1 | grep -c SIGFPE)
    echo "$c: $count"
done
```

**Key insight:** Counting signals via `strace -e signal=SIGFPE` turns opaque validation into a measurable side-channel.

-

### Instruction Trace Inversion with Keystone and Unicorn

Arithmetic-only transform pipelines can be inverted by recording non-branch instructions, reversing them, and swapping inverse operations.

```python
import idaapi, idc

def trace_transforms(start_ea, end_ea):
    instructions = []
    ea = start_ea
    while ea < end_ea:
        mnem = idc.print_insn_mnem(ea)
        if mnem not in ('jmp', 'je', 'jne', 'call', 'ret'):
            instructions.append((ea, mnem, idc.print_operands(ea)))
        ea = idc.next_head(ea)
    return instructions
```

```python
from keystone import *
from unicorn import *
from unicorn.x86_const import *
```

**Key insight:** Arithmetic-only obfuscation with no memory writes is usually reversible by trace inversion.

-

### Call-less Function Chaining via Stack Frame Manipulation

`leave; ret` chains can emulate a hidden call graph by rewriting saved frame and return pointers.

```python
def reverse_processing(byte):
    res = byte | 0x80
    res = res ^ 0xCA
    res = (res + 66) & 0xFF
    res = res ^ 0xCA
    res = (res + 66) & 0xFF
    res = res ^ 0xCA
    res = (res + 66) & 0xFF
    res = res ^ 0xFE
    return res
```

**Key insight:** Disassemblers that assume balanced `call`/`ret` behavior often fail here.

-

### Parent-Patched Child Binary Dump via strace process_vm_writev

The parent can rewrite child code just-in-time via `process_vm_writev`; tracing the parent is enough to recover the real code.

```bash
strace -f -e trace=process_vm_writev -e write=all -o trace.log ./keygenme
```

```python
import re, pathlib
patches = []
pattern = re.compile(
    r'process_vm_writev\(\d+, \[{iov_base="([^"]+)", iov_len=(\d+)}\].*?\[{iov_base=(0x[0-9a-f]+)',
)
for m in pattern.finditer(pathlib.Path('trace.log').read_text()):
    data = m.group(1).encode('latin1').decode('unicode_escape').encode('latin1')
    addr = int(m.group(3), 16)
    patches.append((addr, data))
```

**Key insight:** Parent-side trace logs reveal both target addresses and the exact bytes written.

-

### ConfuserEx Dynamic Module Dump via Constructor Breakpoint

Break on `<Module>.cctor`, let the protector materialize the decrypted assembly in memory, dump it, then clean names with `de4dot`.

```text
dnSpy:
  File → Open → target.exe
  Assembly Explorer → <Module>.cctor → F9
  F5 to run; wait until loaded
  Right-click assembly → Save Module → out.exe
$ de4dot out.exe
```

**Key insight:** Many .NET protectors secure the on-disk image, not the post-constructor runtime module.
