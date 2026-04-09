---
name: asm-testing
description: "Assembly code testing, debugging, and bug-hunting workflow for hand-written and injected assembly: C/Go harness testing, GDB/LLDB/WinDbg/x64dbg verification, objdump structural analysis, Python helpers (Capstone/Unicorn/Keystone), Frida dynamic instrumentation, offensive ASM debugging (trampolines, callgates, syscall stubs, stack spoofing, PIC shellcode), reverse engineering own binaries, and common bug pattern diagnosis. Use when verifying correctness of .asm/.s/.S files, debugging crashes in injected code, hunting silent corruption in offensive tooling, or building ad-hoc Python analysis scripts."
license: MIT
metadata:
  author: AeonDave
  version: "1.1"
compatibility: "x86-64 and ARM64. Windows: WinDbg, x64dbg, MSVC/MASM. Linux: GDB >= 10, LLDB >= 12, gcc/clang, nasm. Python: capstone, unicorn, keystone-engine, frida-tools."
---

# asm-testing

Structured workflow for testing, debugging, and hunting bugs in hand-written and injected assembly — from standard library functions to offensive trampolines, callgates, and PIC shellcode.

---

## Phase 1 — ABI Compliance Checklist

Run before writing a single test. ABI violations cause silent corruption that surfaces far from the root cause.

### x86-64 System V (Linux/macOS)

- [ ] `rsp` 16-byte aligned at every `call` site (misalignment → SSE crashes)
- [ ] `rbx`, `r12`–`r15` restored to entry values before `ret`
- [ ] Integer return in `rax`; float/double in `xmm0`
- [ ] Stack allocation/deallocation symmetric (no net drift)
- [ ] No writes below `rsp` except within the red zone (leaf only)

### x86-64 Win64 (Windows)

- [ ] `rsp` 16-byte aligned at every `call` site
- [ ] 32-byte shadow space allocated before every `call` (`sub rsp, 0x28` minimum including alignment)
- [ ] `rbx`, `rsi`, `rdi`, `rbp`, `r12`–`r15` restored before `ret`
- [ ] `xmm6`–`xmm15` callee-saved (only `xmm0`–`xmm5` may be clobbered)
- [ ] First 4 integer args in `rcx`, `rdx`, `r8`, `r9`; float args in `xmm0`–`xmm3`
- [ ] `r10 = rcx` before `syscall` instruction (kernel clobbers `rcx`)

### ARM64 AAPCS

- [ ] `sp` 16-byte aligned at all times (hardware enforced)
- [ ] `x19`–`x28` and `d8`–`d15` restored before `ret`
- [ ] `x29` (fp) and `x30` (lr) saved with `stp x29, x30, [sp, #-N]!` if calling out
- [ ] Integer return in `x0`; float return in `d0`

---

## Phase 2 — Structural Analysis (before running)

```bash
# Disassemble and check prologue/epilogue
objdump -d -M intel -S my.o | grep -A40 '<my_fn>:'

# Callee-saved register save/restore
objdump -d -M intel my.o | grep -E 'push|pop|mov \[rsp'

# Section flags (check .text is +x, .data is +w)
objdump -h my.o

# Exported symbols
nm my.o | grep ' T '

# Relocation targets (PIC / GOT usage)
objdump -r my.o

# Windows: dumpbin for COFF objects
dumpbin /disasm /all my.obj
```

**What to confirm**:
- Prologue saves the registers the function uses; epilogue restores in reverse
- Stack allocation/deallocation is symmetric
- No jump to undefined symbols
- For PIC code: no absolute addresses, all access RIP-relative or through register

---

## Phase 3 — C Harness Unit Test

Write a thin C driver that calls the ASM function and asserts results.

```c
/* test_hot_fn.c */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

extern int64_t hot_fn(int64_t a, int64_t b);

typedef struct { int64_t a; int64_t b; int64_t expected; } Case;

static const Case cases[] = {
    { 0,  0,  0 },
    { 1,  2,  3 },
    { -1, 1,  0 },
    { INT64_MAX, 0, INT64_MAX },
};

int main(void) {
    int failed = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        int64_t got = hot_fn(cases[i].a, cases[i].b);
        if (got != cases[i].expected) {
            fprintf(stderr, "FAIL case %zu: hot_fn(%ld, %ld) = %ld, want %ld\n",
                    i, cases[i].a, cases[i].b, got, cases[i].expected);
            failed++;
        }
    }
    if (!failed) puts("ALL PASS");
    return failed ? 1 : 0;
}
```

### Build and run

```bash
# NASM + C harness (Linux)
nasm -f elf64 hot_fn.asm -o hot_fn.o
gcc -g -o test_hot_fn test_hot_fn.c hot_fn.o
./test_hot_fn

# MASM + MSVC (Windows)
ml64 /c /Fo hot_fn.obj hot_fn.asm
cl /Zi /Fe:test_hot_fn.exe test_hot_fn.c hot_fn.obj
test_hot_fn.exe
```

> Load `references/c-harness.md` for Makefile patterns, assertion helpers (float/SIMD/memory), and templates for testing syscall stubs and PIC shellcode via function pointers.

---

## Phase 4 — Debugger Verification

Use the right debugger for the target platform to step through and verify register state.

### GDB (Linux) — quick start

```bash
gdb ./test_hot_fn
(gdb) break hot_fn
(gdb) run
(gdb) layout asm          # split ASM view
(gdb) layout regs         # register panel
(gdb) si                  # step one instruction
(gdb) p/x $rsp % 16       # must be 0 at every CALL
(gdb) x/8gx $rsp          # examine 8 qwords at rsp
```

### WinDbg (Windows) — quick start

```
# Attach to process (do NOT launch binary directly if testing EDR-aware code)
windbg -p <pid>

bp mymodule!my_fn         # breakpoint at symbol
g                          # go
t                          # trace (step into)
p                          # step over
r                          # dump registers
r rsp                      # single register
dqs @rsp L10              # dump 16 qwords at rsp
u @rip L20                # disassemble 20 instructions from RIP
.writemem C:\path\dump.bin <addr> L<size>  # dump memory to file
```

### x64dbg (Windows GUI) — essentials

- **Conditional bp**: `bp <addr>, EAX==1 && ECX==1` — break only when condition holds
- **Log bp**: log register state without breaking (fast resume mode)
- **Trace record**: mark executed instructions green; identify dead code / unreached branches
- **Memory map**: locate injected code regions (RWX pages = suspicious)

> Load `references/debug-commands.md` for full GDB/LLDB/WinDbg/x64dbg command reference.

### Stepping checklist

- At entry: note callee-saved registers (`rbx`, `r12`–`r15` on SysV; add `rsi`, `rdi`, `xmm6`–`xmm15` on Win64)
- After prologue: `rsp` difference from entry = declared frame size
- At every `call`: `rsp % 16 == 0`
- Before `syscall` (Windows): `r10 == rcx`, `rax` = SSN
- At `ret`: callee-saved registers match entry values; `rax` = correct result
- For trampolines: verify fixup label is reached; original `rsp` restored after ROP chain

---

## Phase 5 — Offensive ASM Debugging

Trampolines, callgates, indirect syscall stubs, and stack spoofing code require specialized techniques because they lack symbols, run in dynamic memory, and intentionally manipulate control flow.

### Debugging injected / PIC code

1. **Insert `int3` (0xCC) at known offset** — hard breakpoint inside shellcode for debugger attachment
2. **WinDbg attach to target process** — `windbg -p <pid>` after injection; `bp <alloc_base>+<offset>`
3. **x64dbg memory map** — find RWX regions, set breakpoint on first instruction
4. **Readmem trick** — load shellcode into debugger: `.readmem <path> <addr>`

### Common offensive ASM bug patterns

| Bug | Symptom | Diagnosis |
|-----|---------|-----------|
| Stack misalignment | SSE/XMM crash (0xC0000005) | `r rsp` → check `rsp % 16` at CALL site |
| Shadow space missing | Crash in callee prologue | Verify `sub rsp, 0x28` before every CALL on Win64 |
| Register clobbering | Corrupted variable after syscall return | Step through; compare callee-saved regs at entry vs exit |
| Wrong SSN | Wrong syscall executed or BSOD | Verify `rax` = correct SSN for target OS build |
| Gadget addr miscalculation | JMP into garbage / access violation | Dump gadget memory: `u <addr>` — verify `syscall; ret` or `jmp [rbx]` |
| Frame size mismatch | Stack walker crash / infinite loop | Compare UNWIND_INFO frame sizes with actual SUB/ADD RSP |
| OOB in PE parsing | Silent heap corruption → delayed crash | Bounds-check every VA offset read from PE headers |
| Fixup label not reached | Hang after syscall return | Verify ROP chain: each RET pops expected address |
| RBP/RSP restore after spoof | Stack points to freed memory | Watchpoint on original RSP save location |

### Debugging strategy for callgates / trampolines

1. Break at trampoline entry → dump context struct (all gadget addresses, frame sizes, args)
2. Verify each gadget: `u <gadget_addr> L3` — must see expected instruction sequence
3. Step to `CALL <gadget>` or `JMP <gadget>` → single-step into gadget
4. After syscall return: verify fixup is reached, `rsp` restored, callee-saved regs intact
5. If crash: check last known good RIP (`~* k` in WinDbg) and correlate with ROP chain layout

> Load `references/offensive-asm-debugging.md` for Python helper scripts, Frida hooks, Unicorn emulation, and reverse engineering workflow.

---

## Phase 6 — Python Helper Scripts

When standard debuggers are insufficient, write ad-hoc Python scripts for rapid analysis.

### Capstone — disassemble raw bytes

```python
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
md = Cs(CS_ARCH_X86, CS_MODE_64)
code = open("shellcode.bin", "rb").read()
for i in md.disasm(code, 0x1000):
    print(f"0x{i.address:x}:\t{i.mnemonic}\t{i.op_str}")
```

### Unicorn — emulate and verify without execution

```python
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RAX, UC_X86_REG_RDI

uc = Uc(UC_ARCH_X86, UC_MODE_64)
base = 0x100000
uc.mem_map(base, 0x10000)
code = open("stub.bin", "rb").read()
uc.mem_write(base, code)
uc.reg_write(UC_X86_REG_RDI, 42)     # set arg
uc.emu_start(base, base + len(code))
print(f"RAX = 0x{uc.reg_read(UC_X86_REG_RAX):x}")
```

### Keystone — assemble to verify encoding

```python
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
ks = Ks(KS_ARCH_X86, KS_MODE_64)
encoding, count = ks.asm("sub rsp, 0x28; mov r10, rcx; syscall")
print(f"{count} insns, {len(encoding)} bytes: {bytes(encoding).hex()}")
```

### Gadget finder — locate `syscall; ret` in ntdll

```python
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
md = Cs(CS_ARCH_X86, CS_MODE_64)
ntdll = open("ntdll.dll", "rb").read()
for i in range(len(ntdll) - 3):
    if ntdll[i:i+2] == b'\x0f\x05' and ntdll[i+2] == 0xc3:
        print(f"syscall;ret at offset 0x{i:x}")
```

> Load `references/offensive-asm-debugging.md` for full Python script templates, Frida hook patterns, and Unicorn emulation with tracing callbacks.

---

## Phase 7 — Dynamic Instrumentation (Frida)

Frida injects JavaScript/Python hooks into running processes — useful when source-level debugging is impractical or when testing EDR-visible behavior.

```bash
# Trace all calls to NtAllocateVirtualMemory
frida-trace -p <pid> -i "NtAllocateVirtualMemory"

# Hook a function at offset in module
frida-trace -p <pid> -a "ntdll.dll!0x1234"
```

```javascript
// Custom Frida hook: log args + return for a syscall stub
Interceptor.attach(ptr("0x<stub_addr>"), {
  onEnter(args) {
    console.log("stub called, RCX=" + this.context.rcx);
    console.log("RSP alignment: " + (this.context.rsp % 16));
  },
  onLeave(retval) {
    console.log("returned NTSTATUS=" + retval);
  }
});
```

Use cases: verify stack alignment at runtime across many calls, log gadget resolution results, monitor which syscalls are actually invoked by the trampoline.

---

## Phase 8 — Reverse Engineering Own Binaries

When debugging compiled offensive tools, symbols may be stripped or the bug manifests only in the release build.

### Strategy

1. **Build with symbols for initial debugging** — `/Zi` (MSVC) or `-g` (GCC/clang); strip only for deployment
2. **Compare debug vs release disassembly** — diff the function prologue/epilogue, check if optimizer broke assumptions
3. **dumpbin / objdump the final binary** — verify your ASM stub is in the right section and has correct relocations
4. **PE section analysis** — ensure injected code lands in executable section; check `.pdata` for RUNTIME_FUNCTION entries if you need unwinding to work
5. **Binary diff** — if a change broke it, diff the two `.obj` files byte-by-byte to find what changed

### Quick checks

```bash
# Verify function is present and exported
dumpbin /exports myloader.dll | findstr my_fn
nm -D myloader.so | grep my_fn

# Check RUNTIME_FUNCTION coverage (Windows)
dumpbin /unwindinfo myloader.dll | findstr my_fn

# Compare two builds
fc /b old.obj new.obj          # Windows
cmp -l old.o new.o             # Linux
```

---

## Phase 9 — SIMD / Float Output Verification

Use `memcmp` for exact bit equality or tolerance check for floats.

```c
extern void vec_add(float *dst, const float *src, int n);

static void test_vec_add(void) {
    float dst[8] = {1,2,3,4,5,6,7,8};
    float src[8] = {1,1,1,1,1,1,1,1};
    float exp[8] = {2,3,4,5,6,7,8,9};
    vec_add(dst, src, 8);
    for (int i = 0; i < 8; i++)
        if (dst[i] != exp[i])
            fprintf(stderr, "FAIL dst[%d] = %f, want %f\n", i, dst[i], exp[i]);
}
```

For rounding-sensitive functions: `fabsf(got - expected) < 1e-6f`.

---

## Phase 10 — Cycle Measurement

Only after correctness is confirmed.

```c
static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile("lfence\nrdtsc\nlfence" : "=a"(lo), "=d"(hi) :: "memory");
    return ((uint64_t)hi << 32) | lo;
}

void bench_hot_fn(void) {
    const int RUNS = 10000;
    uint64_t total = 0;
    for (int i = 0; i < RUNS; i++) {
        uint64_t t0 = rdtsc();
        hot_fn(i, i+1);
        uint64_t t1 = rdtsc();
        total += t1 - t0;
    }
    printf("avg cycles: %.2f\n", (double)total / RUNS);
}
```

Pin to one CPU core (`taskset -c 0` on Linux, `start /affinity 1` on Windows). Disable turbo if possible.

---

## Resources

- `references/debug-commands.md` — GDB/LLDB/WinDbg/x64dbg/objdump/readelf/strace command reference
- `references/c-harness.md` — Makefile templates, assertion helpers, PIC shellcode and syscall stub test patterns
- `references/offensive-asm-debugging.md` — Python scripts (Capstone/Unicorn/Keystone), Frida hook patterns, gadget finders, common bug diagnosis, reverse engineering workflow
