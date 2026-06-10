# Nim Binary Reversing

Load after `triage.md` and `re-workflow.md` when the target shows Nim indicators.

---

## Category 1: Recognition

### 1.1 Quick identification

```bash
strings binary | grep -iE "NimMain|nimGC|@\[|\.nim:|nimRawNew"
strings binary | grep -E "fatal\.nim|system\.nim|raises_\.nim"
nm binary 2>/dev/null | grep -iE "NimMain|nimGC|HEX[0-9A-F]+"
```

**Strong indicators:**
- Symbol `NimMain` or `NimMainInner` — always present in non-stripped builds
- Mangled names with `HEX` prefix: `HEXopenHEX_u100` (Nim name mangling)
- String constants matching `*.nim:line` (internal source annotations)
- `@[` substring in read-only data (Nim array literal syntax leaks)
- `nimRawNewObj`, `nimGCref`, `nimGCunref` — GC runtime symbols

**Nim version markers:**
```bash
strings binary | grep -E "^\d+\.\d+\.\d+ \[" | head -5   # Version in error messages
strings binary | grep "Nim-"                               # Build tag
```

---

## Category 2: Symbol Recovery

Nim 1.x and 2.x strip symbols differently. Attempt recovery before manual analysis.

### 2.1 Non-stripped binaries

Nim mangles names but leaves them in the symbol table. Demangling is mechanical:

| Mangled pattern | Decoded rule |
|---|---|
| `HEX41` → `A` | Each `HEXnn` is a hex-encoded ASCII char |
| `_uNNN` | underscore + decimal code point |
| `__` double-underscore | Nim module separator |
| `_dot_` | `.` in original name |
| `_eq_` | `=` operator |
| `_star_` | `*` (exported symbol) |

**Python demangle helper:**
```python
import re

def nim_demangle(sym: str) -> str:
    # HEXnn → char
    sym = re.sub(r'HEX([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), sym)
    # _uNNN → char
    sym = re.sub(r'_u(\d+)', lambda m: chr(int(m.group(1))), sym)
    sym = sym.replace('__', '.').replace('_dot_', '.').replace('_eq_', '=').replace('_star_', '*')
    return sym

# Usage: nm binary | python3 -c "import sys,re; ..."
```

### 2.2 Stripped binaries — FLIRT / function ID

Without symbols, use signature-based recovery:

```bash
# Ghidra: Function ID (FID) database
# Window → Function ID → Create new FID database from Nim stdlib .a files
# Compile Nim hello world at same Nim version → apply FID

# IDA: build sig from Nim stdlib
# pelf nim_stdlib.a nim_stdlib.pat   (FLAIR tools)
# sigmake nim_stdlib.pat nim_stdlib.sig
# Copy sig to IDA/sig/pc/ → apply via View → Open subviews → Signatures

# Binary Ninja: use "create library" from known Nim stdlib object files
```

**Nim stdlib static lib location:**
```
~/.choosenim/toolchains/nim-X.X.X/lib/
Windows: %USERPROFILE%\.nimble\pkgs\  # vendored libs
```

### 2.3 Module layout recovery

Nim embeds module names in the symbol table and string data even when stripped:

```bash
strings binary | grep '\.nim$'    # Source file paths → module list
strings binary | grep 'Traceback' # Nim exception traceback format leaks function names
```

---

## Category 3: Memory Layout

### 3.1 Core types

```
NimString (Nim 1.x):   { len: int64, data: char[] }   // heap-allocated, NOT null-terminated inside buffer
NimSeq<T>:             { len: int64, data: *T[] }       // same header pattern
ref T (managed ptr):   { header: int64, obj: T }        // header contains GC metadata
```

**Nim 2.x ORC GC:**
- `NimSeq` is now a fat pointer: `{ len, cap, data* }`
- Reference counting is embedded in the allocation header (one pointer before the object)
- Arc/ORC objects: first field before the user data is `refCount: int`

### 3.2 Identifying Nim types in Ghidra/IDA

```
; String usage pattern:
; rax = ptr to NimString header
; mov  rdx, [rax]        ; len
; lea  rcx, [rax+8]      ; data ptr (inline for small strings, heap for large)

; Seq index:
; imul rdi, index, sizeof(T)
; add  rdi, [seq_ptr + 8]  ; data array start
```

**Rename pattern:** when you see a struct loaded as `{int64, ptr}` and then the ptr is passed to print/compare functions, it is likely a `NimString` or `NimSeq`.

### 3.3 Exception and traceback structures

Nim exceptions are objects with:
- `parent: ref Exception`
- `name: cstring`
- `msg: NimString`
- `trace: seq[StackTraceEntry]`

The traceback format `"filename.nim(line) functionname"` is stored as a static `StackTraceEntry` array — it survives stripping and is useful for identifying call sites.

---

## Category 4: Decompilation Patterns

### 4.1 Closures → `tyObject_Env_*`

Every Nim closure (lambda passed as proc var) captures its environment in an auto-generated struct named `tyObject_Env_XXX` in debug builds:

```nim
# Source
let mult = proc(x: int): int = x * factor
```
```asm
; Compiled: closure = (funcPtr, envPtr)
; envPtr → struct { factor: int64 }
; Call site: call [closure.funcPtr](arg, closure.envPtr)
```

Look for two-field structs passed together — one is a code pointer, one is the env capture.

### 4.2 Iterators → state machines

Nim inline iterators compile to state machines with a discriminant variable:

```c
// Pseudocode after decompilation
switch (state) {
  case 0: /* first entry */  state = 1; yield item[0];
  case 1: /* resume */       if (i < len) { state = 1; yield item[i++]; }
  case 2: /* done */         return;
}
```

Recognize by: a `switch` on a local int that only ever takes sequential values, and a `return` inside that acts as `yield` return to caller.

### 4.3 Generics → monomorphized copies

Nim generics are fully monomorphized. In stripped binaries you get multiple copies of nearly identical functions (e.g., `sort__int_`, `sort__string_`). Use cross-references and argument types to associate them with the generic source.

### 4.4 Exception handling

Nim uses `setjmp`/`longjmp` on non-Windows targets. Look for:
- `setjmp` call early in a function with result checked against 0
- `longjmp` at error paths
- `nlvm`-compiled Nim uses LLVM EH instead — different pattern

```bash
strings binary | grep -E "Error|Exception|Defect"   # Exception message strings survive stripping
```

### 4.5 Compile-time constants → `.rodata`

Nim `const` arrays and string tables land in `.rodata`. Static lookup tables, XOR keys, or algorithm constants are often Nim `const` blocks:

```bash
# Identify large rodata blobs
radare2 -c 'iS~rodata' binary
# Navigate to them in Ghidra: Data → Define As → Array/Struct
```

---

## Category 5: Stripped Binary Workflow

When neither symbols nor FLIRT help:

1. **Anchor on `NimMain`** — even stripped, `NimMain` is usually exported or detectable by its call structure (calls `initStackBottomWith`, then `NimMainInner`)
2. **Trace from `NimMainInner`** → module init sequence → real program logic
3. **Exception string mining** — `strings binary | grep '\.nim:'` yields source paths → derive module names and key function locations
4. **Recognize GC primitives** — functions that take a single pointer and call `nimGCref`/`nimGCunref`/`nimRawNewObj` are GC helpers, not business logic; skip them
5. **Cross-ref rodata strings** → most Nim programs produce human-readable error messages; trace them to handlers → identify key code paths
6. **Type reconstruction** — use the `NimString` and `NimSeq` patterns above to recover argument types of unknown functions

---

## Category 6: Dynamic Analysis

```bash
# GDB — standard; set breakpoints on NimMain, business logic anchors
gdb ./binary
(gdb) b NimMain
(gdb) b NimMainInner

# Frida — hook Nim procs by address (no symbol hook needed)
frida -n proc_name --eval 'Interceptor.attach(ptr("0xADDR"), { onEnter(args) { console.log(args[0]); } })'

# ltrace — trace libc calls (memory alloc, string ops)
ltrace ./binary 2>&1 | grep -E "malloc|free|memcpy|strcmp"

# strace — trace syscalls (file, network, process)
strace -f ./binary 2>&1
```

**Key dynamic anchors:**
- `NimMain` / `NimMainInner` — program start
- `rawWrite` / `echoBinSafe` — any `echo` call in source → useful side-channel for tracing data flow
- `nimRawNewObj` — every heap allocation passes through here; can intercept to trace object creation

---

## Tool citations

- `ghidra` — Function ID + manual type reconstruction
- `radare2` — headless analysis, rodata navigation
- `gdb` — dynamic debugging, breakpoints on Nim anchors
- `frida` — runtime hooking by address
- `nm`, `strings` — initial triage and symbol/string mining
