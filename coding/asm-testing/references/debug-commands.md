# Debug Commands Reference

Complete reference for tools used to inspect and debug assembly code — GDB, LLDB, WinDbg, x64dbg, and static analysis utilities.

---

## GDB

### Setup

```bash
gdb ./binary
gdb -p <pid>           # attach to running process
gdb --args ./binary a b c
```

### Breakpoints

```gdb
break my_fn                    # at function entry
break hot_fn.asm:42            # source line (if -g)
break *0x4005a0                # at absolute address
b hot_fn if $rdi == 0          # conditional breakpoint
watch $rax                     # watchpoint on register
watch -l *ptr                  # watchpoint on memory address
rwatch *0x7fff0010             # read watchpoint (trigger on read)
awatch *0x7fff0010             # access watchpoint (read or write)
delete <n>                     # delete breakpoint n
info break                     # list all breakpoints
```

### Execution

```gdb
run [args]
continue / c
si                             # step one instruction (into calls)
ni                             # step one instruction (over calls)
finish                         # run until current function returns
until <line>                   # run until source line
```

### Register inspection

```gdb
info registers                 # all GP registers
info float                     # x87 FP stack
info all-registers             # including vector regs
p/x $rax                       # print register hex
p/d $rdi                       # print signed decimal
p/f $xmm0.v4_float[0]          # print first float in xmm0
set $rax = 42                  # modify register
p/x $rsp % 16                  # check stack alignment (must be 0 at CALL)
```

### Memory inspection

```gdb
x/Nuf ADDR                     # examine: N units, format, size
x/8gx $rsp                     # 8 quadwords hex from rsp
x/16bx $rdi                    # 16 bytes hex from rdi
x/4wx 0x[addr]                 # 4 dwords
x/s $rdi                       # null-terminated string
x/i $pc                        # instruction at PC
x/10i $pc                      # next 10 instructions
```

### ASM-focused layout

```gdb
layout asm                     # split view: ASM + source
layout regs                    # split view: registers
focus asm                      # keyboard focus to ASM pane
set disassembly-flavor intel   # Intel syntax
```

### Stack inspection

```gdb
info frame                     # current frame info
backtrace / bt                 # call stack
frame <n>                      # switch frame
p $rsp % 16                    # check 16-byte alignment
x/40gx $rsp                    # dump 40 qwords from rsp
```

### Scripting

```gdb
define dump_regs
  printf "rax=%lx rbx=%lx rcx=%lx rdx=%lx\n", $rax, $rbx, $rcx, $rdx
end

# Log register state at every step (useful for trampoline debugging)
define trace_regs
  while 1
    si
    printf "RIP=%lx RSP=%lx RAX=%lx\n", $rip, $rsp, $rax
  end
end
```

---

## LLDB

### Basic usage

```bash
lldb ./binary
lldb -- ./binary arg1 arg2
lldb -p <pid>
```

### Breakpoints and execution

```lldb
b hot_fn                        # break at function
br set -a 0x4005a0              # break at address
run
s                               # step into (si)
n                               # step over (ni)
finish
c
```

### Register and memory

```lldb
register read                   # all GP registers
register read rax rbx rcx       # specific registers
register read --all             # including SIMD
register write rax 42           # modify register
memory read -s8 -c8 $rsp        # 8 qwords at rsp
memory read -s1 -c16 $rdi       # 16 bytes at rdi
memory read -f s $rdi           # string
```

### Disassembly

```lldb
disassemble --pc                # ~10 instructions around PC
disassemble -n 20 --pc          # 20 instructions
disassemble --name hot_fn       # entire function
disassemble -s 0x4005a0 -c 30   # 30 insns from address
```

---

## objdump

```bash
# Disassemble all code (Intel syntax)
objdump -d -M intel binary.o

# Disassemble with source (requires -g)
objdump -d -S -M intel binary.o

# Only one function (pipe + awk)
objdump -d -M intel binary | awk '/^[0-9a-f]+ <hot_fn>:/,/^$/'

# Show all sections
objdump -h binary.o

# Relocations
objdump -r binary.o

# Full symbol table
objdump -t binary

# DWARF debug info
objdump --dwarf=info binary
```

---

## readelf

```bash
# Section headers
readelf -S binary.o

# Program headers (segments)
readelf -l binary

# Symbol table
readelf -s binary

# Dynamic symbols (shared lib)
readelf -d binary

# DWARF unwind table
readelf --debug-dump=frames binary
```

---

## nm

```bash
nm binary.o                    # all symbols
nm -S binary.o                 # with size
nm -u binary.o                 # undefined symbols only
nm -D binary                   # dynamic symbols
nm --demangle binary           # C++ demangled
```

---

## WinDbg

### Launch and attach

```
windbg binary.exe              # launch with debugger
windbg -p <pid>                # attach to running process
windbg -pn notepad.exe         # attach by process name
windbg -z dump.dmp             # analyze crash dump
```

**Important**: to debug EDR-aware code, attach to an already-running process (`-p <pid>`). Launching directly means hooks are not yet installed.

### Breakpoints

```
bp mymodule!my_fn              # break at symbol
bp ntdll!NtAllocateVirtualMemory  # break at Nt function
bu mymodule!my_fn              # deferred bp (unloaded module)
ba e1 <addr>                   # hardware exec breakpoint (1 byte)
ba w4 <addr>                   # hardware write watchpoint (4 bytes)
ba r8 <addr>                   # hardware read watchpoint (8 bytes)
bp <addr> ".if (@rax==0) {} .else {gc}"  # conditional: break only if rax==0
bp <addr> "r; gc"              # log registers and continue (never breaks)
bl                             # list breakpoints
bc *                           # clear all breakpoints
```

### Execution

```
g                              # go (continue)
t                              # trace (step into, one instruction)
p                              # step over
gu                             # go up (run until function returns)
ta <addr>                      # trace to address
```

### Registers

```
r                              # dump all registers
r rax                          # single register
r rax=42                       # modify register
r @rsp                         # @-prefix for expressions
? @rsp % 10                    # check alignment (result should be 0)
.formats <value>               # show value in multiple formats
```

### Memory inspection

```
dqs @rsp L10                   # dump 16 qwords at rsp (with symbols)
db <addr> L40                  # dump 64 bytes raw
dd <addr> L10                  # dump 16 dwords
u @rip L20                     # disassemble 20 instructions from RIP
u <addr> L5                    # disassemble 5 instructions at addr
uf mymodule!my_fn              # disassemble entire function
s -b <start> L<len> 0f 05 c3  # search for syscall;ret bytes
```

### Stack and call chain

```
k                              # stack trace
kP                             # stack trace with full params
~* k                           # stack trace for all threads
!uniqstack                     # show unique stacks across threads
.frame <n>                     # switch to frame n
dqs @rsp L40                   # raw stack dump
```

### Memory and modules

```
lm                             # list loaded modules
!address <addr>                # show memory region info (RWX, mapped?)
!address -summary              # memory layout summary
.writemem C:\path\dump.bin <addr> L<size>  # dump memory to file
.readmem C:\path\code.bin <addr>           # load file to memory
```

### Scripting

```
$$ Log RAX at every hit and continue
bp <addr> ".printf \"RAX=%p RSP=%p\\n\", @rax, @rsp; gc"

$$ Step until ret (0xC3) is hit
.while (1) { t; .if (by(@rip) == 0xc3) { .break } }

$$ Dump context struct at R15
dt _MY_CONTEXT @r15
```

---

## x64dbg

### Basics

- Open binary: File → Open or drag-drop
- Attach: File → Attach → select process
- Step: F7 (into) / F8 (over) / F9 (run) / Ctrl+F9 (run to return)
- Go to address: Ctrl+G → type address or expression

### Breakpoints

```
bp <addr>                           # software breakpoint
bp <addr>, EAX==1 && ECX==1        # conditional break
bp <addr>, mem.valid(EAX)          # break if EAX is valid address
bp <addr>, $breakpointcounter==3   # break on 3rd hit
bp <addr>, tid()==1C0              # break only on specific thread
bph <addr>, r, 8                   # hardware read watchpoint (8 bytes)
bph <addr>, w, 4                   # hardware write watchpoint
bph <addr>, x, 1                   # hardware execute breakpoint
```

### Conditional log (non-breaking)

Set break condition = `0`, log text = `RAX={RAX} RSP={RSP}`, enable fast resume. Logs at thousands of hits/sec without stopping.

### Trace record

Enable trace record (Trace → Start) to mark every executed instruction. Useful for:
- Identifying dead code in trampolines
- Finding which branch was taken in obfuscated code
- Post-mortem analysis after a crash

### Memory map

View → Memory Map shows all allocated regions. Look for:
- **RWX pages** — likely injected shellcode or JIT
- Pages allocated by VirtualAlloc that are `PAGE_EXECUTE_READWRITE`
- Code outside known modules (unbacked memory)

### Useful commands

```
dis.asm(addr)                  # disassemble address
mem.read(addr, size)           # read memory
str.ascii(addr) / str.unicode(addr)  # read string
mod.base(ntdll.dll)            # module base address
ref.find(addr, "0F05C3")      # search for byte pattern (syscall;ret)
```

---

## strace (Linux)

```bash
strace ./binary                # trace all syscalls
strace -e write,read ./binary  # filter by syscall name
strace -e trace=memory ./binary
strace -c ./binary             # summary table
```

---

## Useful one-liners

```bash
# Find a symbol by approximate name
nm binary | grep -i 'hot'

# Dump all strings in binary
strings binary | grep -v '^\.'

# Count instructions in function
objdump -d -M intel binary | awk '/^[0-9a-f]+ <hot_fn>:/,/^$/' | wc -l

# Show stripped / not stripped
file binary
readelf -S binary | grep debug

# Search for syscall;ret gadget in binary (Linux)
objdump -d -M intel binary | grep -B1 'ret' | grep -B1 'syscall'

# Dump RUNTIME_FUNCTION table (Windows)
dumpbin /unwindinfo binary.dll

# Find all JMP [reg] gadgets in binary
objdump -d -M intel binary | grep -E 'jmp\s+\[r[a-z0-9]+\]'

# Compare two object files byte-by-byte
cmp -l old.o new.o          # Linux
fc /b old.obj new.obj       # Windows
```

---

## Frida (quick reference)

```bash
# Trace API calls by name
frida-trace -p <pid> -i "NtAllocateVirtualMemory"

# Trace function at offset in module
frida-trace -p <pid> -a "ntdll.dll!0x1234"

# Attach and run script
frida -p <pid> -l hook.js
```

```javascript
// hook.js — log args and return value for any function
Interceptor.attach(Module.findExportByName("ntdll.dll", "NtAllocateVirtualMemory"), {
  onEnter(args) {
    console.log("ProcessHandle=" + args[0]);
    console.log("BaseAddress=" + args[1].readPointer());
    console.log("RegionSize=" + args[3].readPointer());
  },
  onLeave(retval) {
    console.log("NTSTATUS=" + retval);
  }
});

// Check stack alignment inside a custom stub
Interceptor.attach(ptr("0x<stub_addr>"), {
  onEnter() {
    var rsp = this.context.rsp;
    if (rsp.and(0xF).toInt32() !== 0)
      console.log("MISALIGNED RSP=" + rsp + " at stub entry!");
  }
});
```
