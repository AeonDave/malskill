# CTF Reverse - Runtime, UI, and Handler Patterns

Patterns where success comes from symbolic runtime modeling, UI/event tracing, or odd handler-driven behavior rather than pure static extraction.

## Table of Contents
- [Z3 for Single-Line Python Boolean Circuit](#z3-for-single-line-python-boolean-circuit)
- [Sliding Window Popcount Differential Propagation](#sliding-window-popcount-differential-propagation)
- [Morse Code from Keyboard LEDs via ioctl](#morse-code-from-keyboard-leds-via-ioctl)
- [C++ Destructor-Hidden Validation](#c-destructor-hidden-validation)
- [Syscall Side-Effect Memory Corruption](#syscall-side-effect-memory-corruption)
- [MFC Dialog Event Handler Location](#mfc-dialog-event-handler-location)
- [VM Sequential Key-Chain Brute-Force](#vm-sequential-key-chain-brute-force)
- [Burrows-Wheeler Transform Inversion without Terminator](#burrows-wheeler-transform-inversion-without-terminator)
- [OpenType Font Ligature Exploitation for Hidden Messages](#opentype-font-ligature-exploitation-for-hidden-messages)

## Z3 for Single-Line Python Boolean Circuit

```python
from z3 import *

n_bytes = 29
ari = BitVec('ari', n_bytes * 8)
s = Solver()
s.add(bfu == 0)
```

**Key insight:** Split the line, translate the circuit, solve symbolically.

## Sliding Window Popcount Differential Propagation

```python
expected = [...]
total_bits = 337 + 15
for start_val in range(0x10000):
    if bin(start_val).count('1') != expected[0]:
        continue
```

**Key insight:** Once the first 16 bits are fixed, the rest of the bitstream becomes deterministic.

## Morse Code from Keyboard LEDs via ioctl

```bash
python3 -c "
data = open('binary','rb').read()
data = data[:0x72b] + b'\x90'*5 + data[0x730:]
open('patched','wb').write(data)
"
strace -e ioctl ./patched 2>&1 | grep KDSETLED > leds.txt
```

**Key insight:** Treat LED blinking as an observable side channel, not as an output gimmick.

## C++ Destructor-Hidden Validation

```asm
__cxa_atexit(destructor_func, object_ptr, dso_handle);
```

**Key insight:** If `main()` looks empty, the real checker may live in global destructors.

## Syscall Side-Effect Memory Corruption

```c
// Input ':' triggers rt_sigprocmask(SIG_BLOCK, NULL, (sigset_t*)0x603397, ...)
```

**Key insight:** A syscall can become the corruption primitive when parsing logic feeds it attacker-shaped pointers.

## MFC Dialog Event Handler Location

```asm
bp user32!SendMessageW ".if (poi(@esp+8)==0x111) {}.else {gc}"
```

**Key insight:** In MFC tasks, event routing is the control-flow graph.

## VM Sequential Key-Chain Brute-Force

```c
uint32_t process(uint32_t val) {
    for (int i = 0; i < 1000; i++) {
        val ^= (val << 13);
        val ^= (val >> 17);
        val ^= (val << 5);
        val *= 0x2545f491;
    }
    return val;
}
```

**Key insight:** When the transform is intentionally one-way, brute force is the design, not the fallback.

## Burrows-Wheeler Transform Inversion without Terminator

```python
def bwt_inverse_bruteforce(bwt_string):
    n = len(bwt_string)
    table = [''] * n
    for _ in range(n):
        table = sorted([bwt_string[i] + table[i] for i in range(n)])
    return [row for row in table if is_valid_plaintext(row)]
```

**Key insight:** Missing terminators turn BWT reversal into candidate ranking by domain constraints.

## OpenType Font Ligature Exploitation for Hidden Messages

```python
from fontTools.ttLib import TTFont

font = TTFont(font_path)
gsub = font['GSUB']
```

**Key insight:** Custom ligatures are often just a substitution cipher embedded in a font file.
