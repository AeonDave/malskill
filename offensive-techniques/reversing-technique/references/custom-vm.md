# Custom VM, Side-Channel, and Emulation Techniques

Methodology for reversing custom bytecode VMs, bypassing nanomites and signal-handler tricks, recovering flag bytes via side channels, and using emulation frameworks when direct debugging is blocked.

---

## Category 1: Custom VM Reversing

A custom VM appears when a binary bundles a bytecode blob alongside a dispatcher loop. Reverse the opcode switch table first, then write a disassembler to lift the bytecode before reasoning about the algorithm.

### 1.1 Recognition

**Indicators:**
- Large `switch(opcode)` or jump table dispatching to small handlers
- Loop reading from a byte buffer with an advancing instruction pointer
- Register array (`R[0]..R[N]`) and a separate memory/stack array
- Opcode fan-out: ~10–40 distinct handlers (less = too simple, more = likely something else)

**Common VM structure:**
```c
while (1) {
    uint8_t opcode = bytecode[ip++];
    switch (opcode) {
        case 0x01: R[A] = R[B] + R[C]; break;         // ADD
        case 0x02: R[A] = R[B] ^ imm; break;          // XOR imm
        case 0x03: if (!R[A]) ip += offset; break;     // JZ
        case 0x04: mem[R[A]] = R[B]; break;            // STORE
        case 0x05: R[A] = getchar(); break;             // INPUT
        case 0x06: halt = (R[0] == expected); break;   // CHECK
    }
}
```

---

### 1.2 Analysis Workflow

```
1. Identify: Locate the dispatcher loop (large switch or jmp-table near top of main).
2. Map opcodes: Enumerate all case labels → assign mnemonics (ADD, MOV, XOR, JNZ, …).
3. Write a disassembler: Parse bytecode blob → emit human-readable listing.
4. Lift to pseudocode: Understand the algorithm the bytecode implements.
5. Invert (if needed): Derive input that satisfies the final comparison.
```

---

### 1.3 RVA-Based Opcode Dispatching

Opcodes are relative virtual addresses pointing to handler functions. No integer switch — each opcode is a 4-byte RVA.

**Analysis:**
1. Find the handler table (array of RVAs at a fixed data offset).
2. Follow each RVA to its handler function.
3. Map: `handler_address → mnemonic`.
4. Extract the bytecode blob; replace each 4-byte RVA with your mnemonic.

---

### 1.4 State Machine VM (Large Number of States)

Some VMs have thousands of states (e.g., DFA-style string acceptance). Use BFS to find valid paths without fully understanding the transition logic.

```python
from collections import deque

# state_transitions[state][input_char] = next_state
# Load from binary: array indexed by (state, char)

def find_accepting_path(state_transitions, start_state, accept_state, max_length):
    """BFS to find input string that drives VM from start to accept."""
    agenda = deque([(start_state, "")])
    visited = set()
    while agenda:
        state, path = agenda.popleft()
        if state == accept_state and len(path) == max_length:
            return path
        if state in visited or len(path) >= max_length:
            continue
        visited.add((state, len(path)))
        for char_code, next_state in state_transitions.get(state, {}).items():
            agenda.append((next_state, path + chr(char_code)))
    return None
```

---

### 1.5 Black-Box ISA Discovery via Fuzzing

When static analysis of the dispatch loop is too complex, discover the instruction set empirically.

**Step 1: Determine instruction alignment.**
Dump bytecode as bit strings at widths 6–11 bits. Look for repeating boundary markers.

**Step 2: Single-instruction fuzzing.**
Send one instruction at a time and observe register/memory state changes.

**Step 3: Build the ISA table.**
```text
# Example discovered ISA (variable-length 6–11 bits):
000 xxxxxxxx  jmpz       001 xxxxxxxx  jmp
010 xxxxxxxx  call       011 xxxxxxxx  label
1000 xxxxxxx  loadram    1001 xxxxxxx  saveram
110 xxxxxxxx  loadi      11100 xxxxxx  shl
11101 xxxxxx  shr        111100        not
111101        and        111110        or
111111        setif
```

**Step 4: Build assembler/disassembler.** Lift bytecode to readable form.

**Step 5: Implement missing primitives from available ones:**
```python
# If ISA has AND/OR/NOT but no XOR or ADD:
def xor_(a, b): return (a | b) & ~(a & b)         # XOR from AND/OR/NOT

def add_(a, b, bits=32):                            # ADD via full-adder chain
    carry, result = 0, 0
    for i in range(bits):
        ai, bi = (a >> i) & 1, (b >> i) & 1
        s = xor_(xor_(ai, bi), carry)
        carry = (ai & bi) | (carry & xor_(ai, bi))
        result |= s << i
    return result
```

---

### 1.6 Multi-Stage Self-Decrypting Bytecode (Layer Oracle)

Pattern: binary has N layers; each reads 2 key bytes, derives keystream (e.g., SHA-256), XOR-decrypts the next layer, jumps to it. Wrong key → garbage code.

**Oracle:** Correct key bytes produce code with exactly 2 `call read@plt` instructions (the next layer's reads). Brute-force all 65536 candidates per layer.

**JIT execution approach (fastest for many layers):**
```c
// Map binary's memory into solver process at original virtual addresses
void *text = mmap((void*)0x400000, text_sz, PROT_READ|PROT_WRITE|PROT_EXEC,
                  MAP_FIXED|MAP_PRIVATE, fd, text_offset);

// Fork per candidate — COW provides isolated memory cheaply
for (int cand = 0; cand < 65536; cand++) {
    pid_t pid = fork();
    if (pid == 0) {
        inject_key_bytes(cand >> 8, cand & 0xff);
        ((void(*)())layer_addr)();   // Execute layer as function call
        int hits = count_call_read_plt(next_layer_addr);
        if (hits == 2) signal_parent_with(cand);
        _exit(0);
    }
    waitpid(pid, NULL, 0);
}
```

**Performance note:** Fork-per-candidate with copy-on-write is orders of magnitude faster than subprocess + ptrace injection. For 256 layers × 65536 candidates, target ≥1000 candidates/second (JIT) vs ~2/s (Python subprocess).

---

## Category 2: Nanomites

### 2.1 Linux Signal-Based Nanomites

The binary replaces instructions with `int 3` / `ud2` / `idiv $0` / null-deref. A parent process catches the resulting signals, performs the real computation, modifies child registers/memory, and restarts the child.

**Identification:**
```bash
# Look for fork + ptrace(TRACEME) at the start
strace ./binary 2>&1 | head -20
# Fork call followed by ptrace(PTRACE_TRACEME)
# Parent enters WaitForDebugEvent / waitpid loop
```

**Analysis:**
1. Locate `fork()` + `ptrace(PTRACE_TRACEME)` in the child.
2. Find the `waitpid`/`waitid` loop in the parent.
3. Map signal type → computation: each signal handler extracts `EAX` from the trap to determine the operation.
4. Log all `PTRACE_POKETEXT`/`PTRACE_POKEDATA` calls — these are the hidden computations.

```bash
# Let strace record all parent pokes:
strace -f -e trace=ptrace -e write=all -o trace.log ./binary
# Extract (address, bytes) pairs and replay into a clean binary
```

---

### 2.2 Windows Debug Event Nanomites

**Pattern:** Parent installs `WaitForDebugEvent` loop. Child uses magic markers:
```c
__asm { int 3 }         // Triggers EXCEPTION_DEBUG_EVENT in parent
// Parent checks EAX for magic value (e.g., 0x1337BABE)
// Parent writes real instruction result back via WriteProcessMemory
```

**Analysis:**
1. Trace `WaitForDebugEvent` loop to find the switch on `dwDebugEventCode`.
2. Map each exception code to its operation.
3. Reconstruct algorithm from sequence of operations.

---

## Category 3: Self-Modifying Code

### 3.1 XOR Self-Decryption

```asm
lea  rax, [next_block]
mov  dl, [rcx]          ; Input character = decryption key
.loop:
    xor  [rax+rbx], dl
    inc  rbx
    cmp  rbx, BLOCK_SIZE
    jnz  .loop
jmp  rax                ; Execute decrypted block
```

**Known-good opcode attack:**
The first bytes of a decrypted block are predictable (e.g., function prologue `55 48 89 E5`). XOR with the encrypted first bytes to recover the key character.

```python
prologue = bytes([0x55, 0x48, 0x89, 0xe5])   # push rbp; mov rbp, rsp
encrypted_block_start = bytes([...])           # from binary
key_char = encrypted_block_start[0] ^ prologue[0]
print(chr(key_char))
```

---

### 3.2 mmap RWX Shellcode

Pattern: binary `mmap`s a region with `PROT_READ|PROT_WRITE|PROT_EXEC`, copies/decodes data into it, and jumps to it.

**Detection:**
```bash
strace -e trace=mmap ./binary 2>&1 | grep "PROT_EXEC"
```

**Analysis:**
1. Break on the `jmp rax` / `call rax` that enters the shellcode.
2. Dump the RWX region at that moment: `gdb -ex 'b *0xADDR' -ex 'run' -ex 'dump memory shellcode.bin addr addr+size'`
3. Disassemble: `ndisasm -b 64 shellcode.bin` or load in Ghidra/r2.

---

## Category 4: Side-Channel Attacks

### 4.1 Instruction Count via Intel Pin

**When to use:** Binary compares input character-by-character; each correct character causes deeper execution → more instructions executed.

```python
import string, subprocess

PIN = '/path/to/pin'
TOOL = 'source/tools/ManualExamples/obj-intel64/inscount0.so'

def count_instructions(input_str):
    cmd = [PIN, '-t', TOOL, '--', './binary']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate(input_str.encode())
    with open('inscount.out') as f:
        return int(f.read().split()[-1])

flag = ''
for pos in range(64):   # max flag length
    best_count, best_char = 0, ''
    for c in string.printable[:62]:
        n = count_instructions(flag + c + 'A' * (63 - pos))
        if n > best_count:
            best_count, best_char = n, c
    flag += best_char
    print(f'[+] flag so far: {flag}')
```

**Also works for:** Movfuscated binaries (compiles everything to `mov`), binaries with loop-count-dependent execution.

---

### 4.2 Genetic Algorithm for Complex Instruction-Count Landscapes

When characters interact (self-modifying code), brute-force per-position counting fails. Use a genetic algorithm.

```python
import random, string, subprocess

def fitness(candidate):
    proc = subprocess.Popen(['./pin', '-t', TOOL, '--', './binary'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    proc.communicate(candidate.encode())
    with open('inscount.out') as f:
        return int(f.read().split()[-1])

CHARSET = string.printable[:62]
FLAG_LEN = 40
POP = 100

pop = [''.join(random.choices(CHARSET, k=FLAG_LEN)) for _ in range(POP)]
for generation in range(200):
    scores = [(fitness(ind), ind) for ind in pop]
    scores.sort(reverse=True)
    print(f"Gen {generation}: best = {scores[0][1]!r}")
    survivors = [ind for _, ind in scores[:POP//2]]
    # Crossover + mutate
    children = []
    for _ in range(POP//2):
        p1, p2 = random.choices(survivors, k=2)
        cut = random.randint(0, FLAG_LEN)
        child = list(p1[:cut] + p2[cut:])
        for i in range(FLAG_LEN):
            if random.random() < 0.05:
                child[i] = random.choice(CHARSET)
        children.append(''.join(child))
    pop = survivors + children
```

---

### 4.3 Timing Side Channel

**Pattern:** Validation sleeps or iterates longer on a correct character.

```python
import time, string
from pwn import *

def time_check(candidate, host, port):
    io = remote(host, port, timeout=10)
    start = time.perf_counter()
    io.sendline(candidate.encode())
    io.recvall(timeout=5)
    elapsed = time.perf_counter() - start
    io.close()
    return elapsed

flag = ''
for pos in range(40):
    best_time, best_char = 0, ''
    for c in string.printable[:62]:
        t = time_check(flag + c + 'A' * (39 - pos), 'target', 1234)
        if t > best_time:
            best_time, best_char = t, c
    flag += best_char
    print(f'[+] {flag}')
```

---

### 4.4 SIGFPE Signal Count as Side Channel

**Pattern:** Binary uses SIGFPE signal handlers for control flow validation — correct characters trigger more SIGFPE signals.

```bash
for c in {a..z} {A..Z} {0..9}; do
    count=$(echo -n "${c}AAAAAAA" | strace -e signal=SIGFPE ./binary 2>&1 | grep -c SIGFPE)
    echo "$c: $count"
done
# Character with highest count at position i = correct character
```

**Extend to each position:**
```python
import subprocess, string

def count_sigfpe(input_str):
    proc = subprocess.run(
        ['strace', '-e', 'signal=SIGFPE', './binary'],
        input=input_str.encode(), capture_output=True
    )
    return proc.stderr.count(b'SIGFPE')

flag = ''
for pos in range(32):
    best = max(string.printable[:62],
               key=lambda c: count_sigfpe(flag + c + 'A' * (31 - pos)))
    flag += best
    print(f'[+] {flag}')
```

---

### 4.5 LD_PRELOAD memcmp Side Channel

**Pattern:** Binary calls `memcmp(user_input, expected, n)` — a naive implementation returns early on first mismatch, creating a length side channel.

```c
// hook_memcmp.c
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <stdio.h>

int memcmp(const void *s1, const void *s2, size_t n) {
    static int (*real)(const void*, const void*, size_t) = NULL;
    if (!real) real = dlsym(RTLD_NEXT, "memcmp");
    int result = real(s1, s2, n);
    // Count the matching prefix length
    size_t match = 0;
    while (match < n && ((char*)s1)[match] == ((char*)s2)[match]) match++;
    fprintf(stderr, "[memcmp] match_len=%zu\n", match);
    return result;
}
```

```bash
gcc -shared -fPIC -ldl hook_memcmp.c -o hook_memcmp.so
LD_PRELOAD=./hook_memcmp.so ./binary 2>&1 | grep match_len
```

---

## Category 5: Emulation Frameworks

### 5.1 Qiling (Cross-Platform, OS-Layer Emulation)

**Best for:** Foreign architecture, heavy anti-debug, automated input testing, IoT firmware.

Qiling emulates OS syscalls and the filesystem — anti-debug checks like `ptrace(TRACEME)` return success naturally without patching.

```python
from qiling import Qiling
from qiling.const import QL_VERBOSE

# Linux ELF on any host arch
ql = Qiling(['./binary', 'arg1'], 'rootfs/x8664_linux',
            verbose=QL_VERBOSE.DEFAULT)

# Hook ptrace syscall to always return 0
def bypass_ptrace(ql, req, pid, addr, data):
    return 0
ql.os.set_syscall('ptrace', bypass_ptrace)

# Hook specific address (skip anti-VM check)
def skip_check(ql):
    ql.arch.regs.rax = 0
ql.hook_address(skip_check, 0x401234)

ql.run()
```

**Brute-force input with Qiling:**
```python
import string
from qiling import Qiling
from qiling.const import QL_VERBOSE
import io

def test_input(candidate: str):
    stdin_buf = io.BytesIO(candidate.encode())
    stdout_buf = io.BytesIO()
    ql = Qiling(['./binary'], 'rootfs/x8664_linux',
                verbose=QL_VERBOSE.DISABLED,
                stdin=stdin_buf, stdout=stdout_buf)
    ql.run()
    return stdout_buf.getvalue()

flag = ''
for pos in range(40):
    for c in string.printable[:62]:
        out = test_input(flag + c)
        if b'Correct' in out or b'flag' in out.lower():
            flag += c; break
print(flag)
```

---

### 5.2 Unicorn + Keystone: Trace Inversion

**Best for:** Pure arithmetic obfuscation — trace a sequence of instructions, invert them, emulate on the known output to recover the input.

**Workflow:**
1. Trace non-jump instructions (sub, add, xor, rol, ror) in the obfuscated routine.
2. Invert: reverse order; swap `add ↔ sub`, `rol ↔ ror`; `xor` is self-inverse.
3. Assemble with Keystone and emulate with Unicorn on the known target value.

```python
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import *

# 1. Collected transforms from IDAPython / GDB trace:
transforms = [('sub', 'rax, 0x13'), ('xor', 'rax, 0xdeadbeef'), ('rol', 'rax, 7')]

# 2. Invert
inv_map = {'add': 'sub', 'sub': 'add', 'rol': 'ror', 'ror': 'rol', 'xor': 'xor'}
inverted = [(inv_map[m], op) for m, op in reversed(transforms)]

# 3. Assemble
ks = Ks(KS_ARCH_X86, KS_MODE_64)
src = '\n'.join(f'{m} {op}' for m, op in inverted)
encoding, _ = ks.asm(src)

# 4. Emulate on known output
uc = Uc(UC_ARCH_X86, UC_MODE_64)
CODE = 0x1000000
uc.mem_map(CODE, 0x10000)
uc.mem_write(CODE, bytes(encoding))
uc.reg_write(UC_X86_REG_RAX, 0xcafebabe)   # Known output value
uc.emu_start(CODE, CODE + len(encoding))
print(f'Recovered input: {uc.reg_read(UC_X86_REG_RAX):#x}')
```

---

### 5.3 angr Symbolic Execution

**Best for:** Crackmes where you want to find input satisfying a comparison without understanding the algorithm.

```python
import angr, claripy

proj = angr.Project('./binary', auto_load_libs=False)

# Symbolic input (32-byte flag)
flag = claripy.BVS('flag', 32 * 8)
state = proj.factory.full_init_state(
    args=['./binary'],
    stdin=claripy.Concat(flag, claripy.BVV(b'\n'))
)

# Add printable ASCII constraints
for i in range(32):
    byte = flag.get_byte(i)
    state.add_constraints(byte >= 0x20, byte <= 0x7e)

# Explore: find "Correct" path, avoid "Wrong"
sm = proj.factory.simulation_manager(state)
sm.explore(
    find=lambda s: b'Correct' in s.posix.dumps(1),
    avoid=lambda s: b'Wrong' in s.posix.dumps(1)
)

if sm.found:
    sol = sm.found[0]
    print(sol.solver.eval(flag, cast_to=bytes))
```

**Dealing with path explosion:**
```python
# Option A: Use DFS to avoid breadth explosion
sm.use_technique(angr.exploration_techniques.DFS())

# Option B: Manually exclude known-bad functions
proj.hook_symbol('sleep', angr.SIM_PROCEDURES['stubs']['ReturnUnconstrained']())
proj.hook_symbol('rand', angr.SIM_PROCEDURES['libc']['rand']())

# Option C: Start from a mid-function address after unpacking
state = proj.factory.blank_state(addr=0x401800)
```

---

### 5.4 Triton (Single-Path Symbolic Execution)

**Best for:** Linear code with known execution path; faster than angr for single-path problems.

```python
from triton import TritonContext, ARCH, MemoryAccess, CPUSIZE

ctx = TritonContext(ARCH.X86_64)

# Symbolize the input buffer
for i in range(32):
    ctx.symbolizeMemory(MemoryAccess(0x600000 + i, CPUSIZE.BYTE), f'flag_{i}')

# Process instructions (from a concrete execution trace)
for (addr, opcode) in trace:
    inst = ctx.processing(addr, opcode)

# At the comparison point, solve for flag
model = ctx.getModel(ctx.getPathConstraintsAst())
flag = ''.join(chr(v.getValue()) for _, v in sorted(model.items()))
print(f'Flag: {flag}')
```

---

## Common Pitfalls

1. **Missing the real logic** — if a binary has threads or signal handlers, the real computation may be in a SIGSEGV/SIGTRAP handler or a separate goroutine, invisible to linear static analysis.
2. **Instruction-count side channel requires consistent execution** — sandbox interference, ASLR, and parallel threads can add noise; run each candidate 3× and take the median.
3. **Qiling rootfs mismatch** — use the rootfs that matches the target's libc version; a wrong libc causes syscall wrapper mismatches that silently produce wrong results.
4. **angr path explosion** — concolic symbolic execution diverges on loops; hook known-clean functions (sleep, rand, time) with stubs to reduce state count.
5. **Unicorn lacks OS layer** — Unicorn only emulates the CPU; if the code calls syscalls (write, read, mmap), add manual hooks or use Qiling instead.
6. **JIT execution of packed layers** — if the next layer rewrites code at an address your solver process already mapped, ensure `MAP_FIXED` isolation per candidate.

---

## Category 6: Metamorphic Decrypt / Re-Encrypt Loops

A self-modifying binary decrypts a code region on demand, executes it, then re-encrypts it before returning. Each execution window is short; the code is never fully in memory simultaneously.

### 6.1 Detection

```bash
# Static: look for write+exec on the same region
objdump -d binary | grep -E "mprotect|VirtualProtect"
# Or: XOR loop writing to an address that is later called
# Pattern: loop over buffer with XOR, then call/jmp into that buffer

# Dynamic: catch first write to a region that gets executed
gdb ./binary
(gdb) break main
(gdb) run
# After main breaks, set a read watchpoint on suspected encrypted region
(gdb) watch -l *(char*)0x<encrypted_region_base>   # fires on any byte write
```

**Characteristic signature:** A single XOR/ADD loop operating on a fixed-size buffer at one address, followed by a `call` or `jmp` into that buffer. After the call returns, the same loop runs again (re-encrypt path).

### 6.2 Dump at peak decryption

**GDB approach:**
```bash
gdb ./binary
# Catch the execute permission grant or the call into the buffer
(gdb) catch syscall mprotect
(gdb) commands
>   # When mprotect grants EXEC permission, set a breakpoint at the target region
>   set $target_addr = <encrypted_region_base>
>   break *$target_addr
>   continue
> end
(gdb) run

# When the inner code breakpoint fires, dump the decrypted region
(gdb) dump binary memory /tmp/decrypted.bin <start> <end>
(gdb) shell file /tmp/decrypted.bin
(gdb) shell objdump -d /tmp/decrypted.bin -b binary -m i386:x86-64
```

**Frida auto-dump (runs for every round):**
```javascript
// Hook mprotect to detect EXEC grants, then set Instruction-level hooks
const mprotect = Module.getExportByName(null, 'mprotect');
Interceptor.attach(mprotect, {
  onEnter(args) {
    const addr = args[0];
    const size = args[1].toInt32();
    const prot = args[2].toInt32();
    const PROT_EXEC = 0x4;
    if (prot & PROT_EXEC) {
      // Schedule dump: snapshot memory after mprotect returns
      this.dumpInfo = { addr, size };
    }
  },
  onLeave(retval) {
    if (this.dumpInfo) {
      const { addr, size } = this.dumpInfo;
      const data = addr.readByteArray(size);
      const name = `/tmp/memdump_${addr}_round${Date.now()}.bin`;
      require('frida-fs').writeFileSync(name, data);
      console.log(`[dump] ${name} (${size} bytes)`);
    }
  }
});
```

### 6.3 Analysis strategy

1. Collect multiple dump snapshots (the inner code may vary between rounds if truly polymorphic)
2. Compare snapshots: if identical → simple decrypt/re-encrypt; if different → true polymorphism
3. Analyze the first dump as a standalone binary; locate the return path
4. If the inner code also makes calls → it may have its own import table or PLT; reconstruct from dump context
5. For multi-round metamorphic: identify the transform function (often a constant-key XOR or ADD loop) and model it algebraically rather than dumping every round

---

## Category 7: Lattice / Linear-Algebra-Aided VM Solving

Some VMs or state machines compute a linear transformation of the input: `output = M * input + c` where `M` is a matrix of constants. Direct solving is faster than symbolic execution when the structure is identified.

### 7.1 Recognition

**Indicators:**
- VM has a fixed set of opcodes, each of which does: `state[i] += input[j] * constant` or `state[i] ^= input[j]`
- Final check is `state == expected_output` (byte-by-byte or as a vector comparison)
- Multiple passes over the input with accumulated state

**Confirm via angr or Unicorn trace:**
```python
import angr, claripy

# Trace all memory writes to state buffer; check if they are linear in input bytes
# If input[j] appears only in add/mul operations (no branches dependent on input value),
# the transformation is linear
```

### 7.2 Extract transition matrix

**Approach A — Unicorn trace:**
```python
from unicorn import *
from unicorn.x86_const import *
import numpy as np

def run_with_unit_vector(code, base_addr, input_size, idx):
    """Run VM with input = e_i (unit vector), return output state."""
    mu = Uc(UC_ARCH_X86, UC_MODE_64)
    # Map and setup memory...
    inp = [0] * input_size
    inp[idx] = 1  # unit vector e_i
    mu.mem_write(INPUT_ADDR, bytes(inp))
    mu.emu_start(base_addr, base_addr + CODE_SIZE)
    state = bytes(mu.mem_read(STATE_ADDR, OUTPUT_SIZE))
    return np.frombuffer(state, dtype=np.uint8).astype(int)

# Build matrix M: column i = run_with_unit_vector(i)
M = np.column_stack([run_with_unit_vector(code, BASE, INPUT_SIZE, i)
                     for i in range(INPUT_SIZE)])
```

**Approach B — angr symbolic trace:**
```python
import angr, claripy, numpy as np

proj = angr.Project('./binary')
flag = claripy.BVS('flag', 8 * INPUT_SIZE)
state = proj.factory.blank_state(addr=VM_START)
state.memory.store(INPUT_ADDR, flag)

sm = proj.factory.simulation_manager(state)
sm.run(until=lambda s: s.addr == CHECK_ADDR)

# Extract the symbolic expression for each output byte
# and read off the linear coefficients
```

### 7.3 Solve the linear system

**Integer arithmetic (XOR-based, mod 256):**
```python
import numpy as np

# M * x = target (mod 256 if XOR/byte arithmetic)
# Use Gaussian elimination over GF(2) or Z/256Z

def solve_mod256(M, target):
    # Use numpy for float-based approx then verify, or use sympy
    from sympy import Matrix
    M_sym = Matrix(M.tolist())
    t_sym = Matrix(target.tolist())
    sol = M_sym.solve(t_sym)   # Exact rational solution
    return [int(x) % 256 for x in sol]

solution = solve_mod256(M, expected_output)
print(''.join(chr(b) for b in solution))
```

**Z3 linear arithmetic:**
```python
from z3 import *

solver = Solver()
inp = [BitVec(f'x_{i}', 8) for i in range(INPUT_SIZE)]

# Add printable constraints
for x in inp:
    solver.add(x >= 0x20, x <= 0x7e)

# Add linear constraints: M * inp == expected
for row_idx, row in enumerate(M):
    expr = sum(int(row[j]) * inp[j] for j in range(INPUT_SIZE))
    solver.add(expr % 256 == int(expected_output[row_idx]))

if solver.check() == sat:
    model = solver.model()
    print(''.join(chr(model[x].as_long()) for x in inp))
```

### 7.4 Pitfalls

- If the matrix is not square (more equations than unknowns), the system is overdetermined → use least squares or verify you captured all state dimensions
- Mod 256 arithmetic may produce multiple solutions → add printable ASCII constraints to narrow down
- If any opcode has a branch on input value (e.g., `if input[i] > 128`), the system is non-linear → fall back to angr/Unicorn direct solve
