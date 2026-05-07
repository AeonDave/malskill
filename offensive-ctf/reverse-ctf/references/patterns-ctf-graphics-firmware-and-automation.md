# CTF Reverse - Graphics, Firmware, and Automation Patterns

Patterns built around emulation, rendering artifacts, firmware symbol recovery, and large-scale automation.

## Table of Contents
- [GLSL Shader VM with Self-Modifying Code](#glsl-shader-vm-with-self-modifying-code)
- [Instruction Counter as Cryptographic State](#instruction-counter-as-cryptographic-state)
- [Thread Race Condition with Signed Integer Overflow](#thread-race-condition-with-signed-integer-overflow)
- [ESP32/Xtensa Firmware Reversing with ROM Symbol Map](#esp32xtensa-firmware-reversing-with-rom-symbol-map)
- [Batch Crackme Automation via objdump Pattern Extraction](#batch-crackme-automation-via-objdump-pattern-extraction)
- [Fork + Pipe + Dead Branch Anti-Analysis](#fork--pipe--dead-branch-anti-analysis)
- [Time-Locked Binary with Date-Based Key](#time-locked-binary-with-date-based-key)
- [ARM Code in Image Pixels via UnicornJS](#arm-code-in-image-pixels-via-unicornjs)

## GLSL Shader VM with Self-Modifying Code

```python
from PIL import Image
import numpy as np

img = Image.open('program.png').convert('RGBA')
state = np.array(img, dtype=np.int32).copy()
regs = [0] * 33
```

**Key insight:** When GPU parallelism destroys the intended semantics, re-run the VM sequentially in software.

## Instruction Counter as Cryptographic State

```python
from unicorn import *
from unicorn.x86_const import *

uc = Uc(UC_ARCH_X86, UC_MODE_64)
```

**Key insight:** If the transform depends on how many instructions have run so far, byte-by-byte emulation is often simpler than algebra.

## Thread Race Condition with Signed Integer Overflow

```python
import time, threading
def race():
    select_skill(2)
    time.sleep(0.001)
    select_skill(5)
```

**Key insight:** Signed-extension edge cases (`cdqe`) can turn a race into an arithmetic kill switch.

## ESP32/Xtensa Firmware Reversing with ROM Symbol Map

```bash
r2 -a xtensa -b 32 firmware.bin
```

**Key insight:** ROM symbol maps from vendor SDKs can do half the naming work for you.

## Batch Crackme Automation via objdump Pattern Extraction

```bash
objdump -M intel -d $binary | grep -P "cmp\s+rdi" | grep -oP "0x\w{1,2}" | xxd -r -p
```

```bash
python3 <<'EOF'
import subprocess, re, glob
for binary in sorted(glob.glob("crackmes/*")):
    asm = subprocess.check_output(["objdump", "-M", "intel", "-d", binary]).decode()
    ops = re.findall(r'(add|sub)\s+rdi,(0x\w+)', asm)
EOF
```

**Key insight:** If 100 binaries share one template, automate the template instead of solving 100 puzzles by hand.

## Fork + Pipe + Dead Branch Anti-Analysis

```bash
python3 -c "
data = open('binary','rb').read()
data = data.replace(b'\x83\x7d\xf4\x01', b'\x83\x7d\xf4\x00')
open('binary_patched','wb').write(data)
"
```

**Key insight:** Once `strace` shows the real process topology, dead-branch patching often beats dynamic babysitting.

## Time-Locked Binary with Date-Based Key

```bash
LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1 FAKETIME="2012-12-21 00:00:00" ./binary
```

**Key insight:** Date checks are often thematic, not technically deep.

## ARM Code in Image Pixels via UnicornJS

```python
from PIL import Image
import capstone

img = Image.open('decoded.png').convert('RGBA')
pixels = list(img.getdata())
arm_code = bytes([channel for pixel in pixels for channel in pixel])
```

**Key insight:** If a bundled emulator tells you the ISA, believe it and extract the byte stream it consumes.
