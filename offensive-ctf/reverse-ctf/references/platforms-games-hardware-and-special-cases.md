# CTF Reverse - Games, Hardware, and Special-Case Platforms

Focused platform reference for game engines, automotive targets, hardware-centric architectures, and other specialized platform cases.

## Table of Contents
- [Game Engine Reversing](#game-engine-reversing)
- [Automotive / CAN Bus RE](#automotive-can-bus-re)
- [RISC-V QEMU Execution with GLIBC Symbol Version Patching](#risc-v-qemu-execution-with-glibc-symbol-version-patching)
- [APK Certificate SHA-256 as AES Key](#apk-certificate-sha-256-as-aes-key)
- [Moxie ISA Custom Opcode Discovery](#moxie-isa-custom-opcode-discovery)
- [Unity APK Assembly-CSharp.dll Runtime Patch](#unity-apk-assembly-csharpdll-runtime-patch)
- [Il2CppDumper for Unity IL2CPP Metadata Recovery](#il2cppdumper-for-unity-il2cpp-metadata-recovery)
- [HD44780 LCD Controller GPIO Reconstruction](#hd44780-lcd-controller-gpio-reconstruction)
- [RISC-V (Advanced)](#risc-v-advanced)
- [ARM64/AArch64 Reversing and Exploitation](#arm64aarch64-reversing-and-exploitation)
- [MIPS64 Cavium OCTEON Coprocessor 2 Crypto](#mips64-cavium-octeon-coprocessor-2-crypto)
- [EFM32 ARM Microcontroller MMIO AES](#efm32-arm-microcontroller-mmio-aes)
- [MBR/Bootloader Reversing with QEMU + GDB](#mbrbootloader-reversing-with-qemu-gdb)
- [Game Boy ROM Z80 Analysis in bgb Debugger](#game-boy-rom-z80-analysis-in-bgb-debugger)
- [KVM Guest Analysis via ioctl + KVM_EXIT_HLT Block Chaining](#kvm-guest-analysis-via-ioctl-kvm_exit_hlt-block-chaining)
- [Coreboot ROM XOR-Pair Bit-Flip Address Discovery](#coreboot-rom-xor-pair-bit-flip-address-discovery)

## Game Engine Reversing

### Unreal Engine

```bash
unrealpak.exe extract GameName.pak -output extracted/
```

**Blueprint reversing:**
```text
Blueprints compile to bytecode in .uasset files.
- UAssetGUI / FModel to browse Blueprint assets
- Kismet bytecode → visual scripting logic
- Look for: K2_SetTimer, DoOnce, Branch, Custom Events
```

**UE4/UE5 C++ reversing:**
```bash
# Key engine classes:
# UObject, AActor, UGameInstance, APlayerController
```

### Unity (Beyond IL2CPP)

See [languages-core-scripting-and-esolangs.md](languages-core-scripting-and-esolangs.md#unity-il2cpp-games) for IL2CPP basics.

**Mono-based Unity (not IL2CPP):**
```bash
dnspy Assembly-CSharp.dll
ilspy Assembly-CSharp.dll
```

**Unity asset extraction:**
```bash
# AssetStudio / AssetRipper / UABE
```

### Anti-Cheat Analysis

```text
EasyAntiCheat, BattlEye, and VAC all create different triage surfaces.
For lab tasks, identify the specific check first; don't assume you need to defeat the entire anti-cheat stack.
```

### Lua-Scripted Games

```bash
luadec bytecode.luac > decompiled.lua
unluac bytecode.luac > decompiled.lua
luajit -bl bytecode.lua
```

-

## Automotive / CAN Bus RE

```bash
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0
candump can0
candump -l can0
cansniffer can0
canplayer -I logfile.log can0
cansend can0 7DF#0201000000000000
```

**CTF automotive patterns:**
- seed-key bypass from ECU firmware
- CAN message replay
- UDS/KWP2000 firmware extraction

-

## RISC-V QEMU Execution with GLIBC Symbol Version Patching

```bash
ar x libc6_2.27-5_riscv64.deb && tar xf data.tar.xz
sed 's@GLIBC_2.25@GLIBC_2.27@g' -i binary
objdump -p binary
qemu-riscv64 -L./sysroot./binary
```

**Key insight:** Patch both the version string and the associated hash slot.

-

## APK Certificate SHA-256 as AES Key

```python
from hashlib import sha256
import base64, zipfile

cert = zipfile.ZipFile('app.apk').read
key  = base64.b64encode(sha256(cert).digest())[:16]
```

**Key insight:** Deterministic keys derived from public signing material are recoverable offline.

-

## Moxie ISA Custom Opcode Discovery

```python
def xorshift32(s):
    s ^= (s << 13) & 0xffffffff
    s ^= (s >> 17)
    s ^= (s << 15) & 0xffffffff
    return s & 0xffffffff
```

**Key insight:** Grep obscure-ISA binaries for opcode help text before building tooling from scratch.

-

## Unity APK Assembly-CSharp.dll Runtime Patch

```bash
apktool d game.apk -o game_src
apktool b game_src -o patched.apk
jarsigner -keystore debug.keystore -storepass android patched.apk androiddebugkey
adb install -r patched.apk
```

**Key insight:** A hidden render or animation path is often easiest to remove in managed code instead of patching native logic.

---

## Il2CppDumper for Unity IL2CPP Metadata Recovery

```bash
Il2CppDumper libil2cpp.so global-metadata.dat out/
grep -r "https://" out/
```

**Key insight:** Metadata recovery is often enough to extract strings, endpoints, and type names without deep native RE.

---

## HD44780 LCD Controller GPIO Reconstruction

```python
display = [' '] * 80
cursor = 0

for timestamp, gpio_state in sorted(gpio_log):
  if falling_edge(gpio_state, CLK_PIN):
    nibble = extract_data_bits(gpio_state)
    byte = assemble_nibble(nibble)
    if rs_high(gpio_state):
      display[dram_to_position(cursor)] = chr(byte)
      cursor += 1
    else:
      cursor = parse_command(byte)
```

**Key insight:** Recover the clock line first, then infer RS from alternating command/data phases.

---

## RISC-V (Advanced)

### Custom Extensions

```text
Bitmanip extensions (Zbb, Zbc, Zbs): clz, ctz, cpop, andn, orn, xnor, clmul, bset
Crypto extensions (Zk*): aes32esi, aes32dsmi, sha256sig0, sm4ed
```

### Privileged Modes

```text
Machine mode (M), Supervisor mode (S), User mode (U)
Important CSRs: mstatus/sstatus, mtvec/stvec, mepc/sepc, mcause/scause, satp
```

### RISC-V Debugging

```bash
openocd -f interface/jlink.cfg -f target/riscv.cfg
riscv64-unknown-elf-gdb binary
```

---

## ARM64/AArch64 Reversing and Exploitation

```bash
apt install gcc-aarch64-linux-gnu gdb-multiarch qemu-user-static
qemu-aarch64-static -L /usr/aarch64-linux-gnu ./arm64_binary
```

**Key differences from x86-64:**
- `x0-x7` carry arguments and return values
- `x30` is the link register
- fixed 4-byte instructions
- PC-relative loads use `ADRP + ADD`

**Key insight:** AArch64 ROP leans heavily on `LDP ...; RET` gadgets.

---

## MIPS64 Cavium OCTEON Coprocessor 2 Crypto

Cavium OCTEON processors expose hardware AES/SHA through MIPS CP2 via `dmtc2` / `dmfc2`.

**Key insight:** Treat CP2 register writes like hardware-crypto setup, not ordinary register traffic.

---

## EFM32 ARM Microcontroller MMIO AES

```python
from Crypto.Cipher import AES

key = bytes(a ^ b for a, b in zip(key_part_a, key_part_b))
cipher = AES.new(key, AES.MODE_ECB)
plaintext = cipher.decrypt(ciphertext)
```

**Key insight:** Register-level crypto reconstruction is often easier than full-firmware emulation.

---

## MBR/Bootloader Reversing with QEMU + GDB

```bash
qemu-system-x86_64 -fda disk.img -s -S
gdb -ex "set architecture i8086" -ex "target remote :1234"
```

**Key insight:** QEMU's GDB stub makes bootloader debugging feel like userland once the architecture is set correctly.

---

## Game Boy ROM Z80 Analysis in bgb Debugger

Game Boy ROMs use the Sharp SM83 CPU.

**Key insight:** Comparisons against `(hl)` often leak the expected byte directly in memory.

---

## KVM Guest Analysis via ioctl + KVM_EXIT_HLT Block Chaining

```bash
strace -v -e ioctl ./challenge 2>&1 | grep -E "KVM_RUN|KVM_(GET|SET)_REGS"
```

**Key insight:** In KVM-backed tasks, the host often contains the real control-flow graph.

---

## Coreboot ROM XOR-Pair Bit-Flip Address Discovery

```python
intended = C1 ^ C2
diff = intended ^ actual
```

**Key insight:** XOR-composed addresses turn one-bit fault models into very small candidate sets.
