# CTF Reverse - Apple, Firmware, and Kernel Platforms

Focused platform reference for Apple binaries, firmware/embedded targets, and kernel-facing reversing.

## Table of Contents
- [macOS / iOS Reversing](#macos-ios-reversing)
  - [Mach-O Binary Format](#mach-o-binary-format)
  - [Code Signing & Entitlements](#code-signing-entitlements)
  - [Objective-C Runtime RE](#objective-c-runtime-re)
  - [Swift Binary Reversing](#swift-binary-reversing)
  - [iOS App Analysis](#ios-app-analysis)
  - [dyld / Dynamic Linking](#dyld-dynamic-linking)
- [Embedded / IoT Firmware RE](#embedded-iot-firmware-re)
  - [Firmware Extraction](#firmware-extraction)
  - [Firmware Unpacking](#firmware-unpacking)
  - [Architecture-Specific Notes](#architecture-specific-notes)
  - [RTOS Analysis](#rtos-analysis)
- [Kernel Driver Reversing](#kernel-driver-reversing)
  - [Linux Kernel Modules](#linux-kernel-modules)
  - [eBPF Programs](#ebpf-programs)
  - [Windows Kernel Drivers](#windows-kernel-drivers)

## macOS / iOS Reversing

### Mach-O Binary Format

```bash
file binary
otool -l binary
otool -L binary
lipo -info universal_binary
lipo universal_binary -thin arm64 -output binary_arm64
otool -l binary | grep -A5 "segment\|section"
```

**Key Mach-O concepts:**
- Load commands drive the dynamic linker (`dyld`)
- `LC_MAIN` → entry point
- `LC_LOAD_DYLIB` → shared library dependencies
- `LC_CODE_SIGNATURE` → code signing blob
- `__DATA_CONST.__got` → Global Offset Table
- `__DATA.__la_symbol_ptr` → Lazy symbol pointers

### Code Signing & Entitlements

```bash
codesign -dvvv binary
codesign -verify binary
codesign -d -entitlements - binary
codesign -remove-signature binary
codesign -f -s - binary
```

**CTF relevance:** Patched binaries need re-signing to run on macOS.

### Objective-C Runtime RE

```bash
class-dump binary > classes.h
(lldb) expression -l objc -O - [NSClassFromString(@"ClassName") new]
(lldb) expression -l objc -O - [[ClassName alloc] init]
```

**Objective-C in disassembly:**
```text
objc_msgSend(receiver, selector, ...)
RDI = self, RSI = selector
```

**class-dump alternatives:**
- `dsdump`
- `otool -oV binary`
- Ghidra Objective-C analyzer

### Swift Binary Reversing

```bash
strings binary | grep "swift"
otool -l binary | grep "swift"
swift demangle 's14MyApp0A8ClassC10checkInput6resultSbSS_tF'
```

**Swift in disassembly:**
```text
Key runtime functions:
swift_allocObject
swift_release
swift_bridgeObjectRetain
swift_once
```

**Ghidra for Swift:** Enable the Swift analyzer; `__swift5_*` sections contain useful metadata.

### iOS App Analysis

```bash
unzip app.ipa -d extracted/
otool -l extracted/Payload/*.app/binary | grep -A4 "LC_ENCRYPTION_INFO"
frida-ios-dump -H jailbroken_ip -p 22 "App Name"
class-dump decrypted_binary > headers.h
```

**Jailbreak detection and bypass:**
```javascript
var paths = ["/Applications/Cydia.app", "/bin/sh", "/etc/apt",
             "/private/var/lib/apt", "/usr/bin/ssh"];
Interceptor.attach(Module.findExportByName(null, "access"), {
    onEnter(args) {
        this.path = Memory.readUtf8String(args[0]);
    },
    onLeave(retval) {
        if (paths.some(p => this.path && this.path.includes(p))) {
            retval.replace(-1);
        }
    }
});
```

### dyld / Dynamic Linking

```bash
DYLD_PRINT_LIBRARIES=1./binary
DYLD_INSERT_LIBRARIES=hook.dylib./binary
dyld_shared_cache_util -list /System/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e
```

-

## Embedded / IoT Firmware RE

### Firmware Extraction

```bash
binwalk firmware.bin
binwalk -e firmware.bin
binwalk -Me firmware.bin
binwalk -dd='.*' firmware.bin
strings firmware.bin | head -50
hexdump -C firmware.bin | grep "hsqs"
hexdump -C firmware.bin | grep "UBI#"
```

**Hardware extraction methods:**
```text
UART  → serial console and bootloader access
JTAG  → CPU halt / memory access / flash dump
SPI   → direct flash chip reads
eMMC  → raw storage extraction from test pads or chip reader
```

### Firmware Unpacking

```bash
unsquashfs -d output/ squashfs-root.sqfs
jefferson -d output/ jffs2.img
ubireader_extract_images firmware.ubi
ubireader_extract_files ubifs.img
cpio -idv < initramfs.cpio
dtc -I dtb -O dts -o output.dts device_tree.dtb
binwalk -e firmware.bin
```

### Architecture-Specific Notes

**ARM (most common in IoT):**
```bash
apt install gcc-arm-linux-gnueabihf gdb-multiarch
qemu-arm -L /usr/arm-linux-gnueabihf/./arm_binary
qemu-arm -g 1234./arm_binary
gdb-multiarch -ex 'target remote:1234'./arm_binary
```

**ARM64/AArch64:** See [platforms-games-hardware-and-special-cases.md](platforms-games-hardware-and-special-cases.md#arm64aarch64-reversing-and-exploitation).

**MIPS (routers, embedded):**
```bash
file binary
qemu-mips -L /usr/mips-linux-gnu/./mips_binary
qemu-mipsel -L /usr/mipsel-linux-gnu/./mipsel_binary
```

**RISC-V:** See [platforms-games-hardware-and-special-cases.md](platforms-games-hardware-and-special-cases.md#risc-v-advanced).

### RTOS Analysis

```text
FreeRTOS: xTaskCreate, xQueueSend/xQueueReceive, vTaskDelay
Zephyr:   k_thread_create, k_msgq_put/k_msgq_get, CONFIG_* symbols
Bare metal: vector table + polling loop + MMIO peripheral map
```

-

## Kernel Driver Reversing

### Linux Kernel Modules

```bash
file module.ko
modinfo module.ko
nm module.ko | grep -v " U "
strings module.ko | grep -i "flag\|secret\|ioctl\|device"
```

**Common kernel module patterns:**
```c
alloc_chrdev_region(&dev, 0, 1, "challenge");
cdev_init(&cdev, &fops);

long my_ioctl(struct file *f, unsigned int cmd, unsigned long arg) {
    switch (cmd) {
        case CUSTOM_CMD_1: break;
        case CUSTOM_CMD_2: break;
    }
}
```

**Debugging kernel modules:**
```bash
qemu-system-x86_64 -kernel bzImage -initrd initrd.cpio -s -S \
  -append "console=ttyS0 nokaslr" -nographic

gdb vmlinux
(gdb) target remote:1234
(gdb) lx-symbols
```

### eBPF Programs

```bash
bpftool prog list
bpftool prog dump xlated id <N>
bpftool prog dump jited id <N>
llvm-objdump -d ebpf_prog.o
```

**Key eBPF patterns:**
- `bpf_map_lookup_elem`
- `bpf_map_update_elem`
- `bpf_probe_read`
- `bpf_trace_printk`

### Windows Kernel Drivers

```bash
#.sys files are PE format — load in IDA/Ghidra as normal PE
# Entry point: DriverEntry(PDRIVER_OBJECT, PUNICODE_STRING)
```

**Key patterns:**
- `IoCreateDevice`
- `IRP_MJ_DEVICE_CONTROL`
- `MmMapIoSpace`
- `ZwCreateFile` / `ZwReadFile`
