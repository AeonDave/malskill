# Debug Commands Reference

Complete reference for tools used to inspect and debug assembly code.

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
```
