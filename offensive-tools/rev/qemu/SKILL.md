---
name: qemu
description: "Auth/lab ref: QEMU user-mode and full-system emulation for cross-arch binaries, firmware, kernels, disks, serial consoles, networking, and GDB stubs."
license: MIT
compatibility: "Linux/macOS/Windows hosts with QEMU; target support depends on installed qemu-user and qemu-system binaries."
metadata:
  version: "1.0"
  category: tool
---

# QEMU

QEMU is the default public tool for cross-architecture user-mode execution and full-system virtual machines.

## Choose mode

| Need | Mode |
|---|---|
| Run one Linux/BSD ELF with syscalls forwarded to host | `qemu-<arch>` user-mode |
| Run a process inside an extracted rootfs | `qemu-<arch>-static` in chroot/proot/container |
| Boot kernel/initrd/rootfs/disk/firmware | `qemu-system-<arch>` |
| Debug kernel, bootloader, or process before start | `-S -gdb ...` or user-mode `-g` |
| Expose serial/UART | `-serial stdio`, `-serial unix:...`, `-chardev ...` |
| Expose guest services | `-netdev user,hostfwd=tcp:127.0.0.1:<host>-:<guest>` |

## User-mode patterns

```bash
qemu-arm -L ./sysroot ./target arg1
qemu-mipsel -L ./rootfs -strace ./usr/sbin/httpd
QEMU_LD_PREFIX=./rootfs qemu-aarch64 ./bin/app
qemu-riscv64 -g 1234 -L ./rootfs ./bin/app
```

If an existing file reports "No such file or directory", check the ELF interpreter and shared libraries:

```bash
readelf -lW ./target | grep 'Requesting program interpreter'
readelf -dW ./target | grep NEEDED
```

Use `-strace` for syscall evidence. Use `-g <port>` plus `gdb-multiarch` when register/memory proof is needed.

## Full-system patterns

```bash
qemu-system-x86_64 \
  -kernel bzImage \
  -initrd initramfs.cpio.gz \
  -append "console=ttyS0 panic=-1" \
  -serial stdio -display none

qemu-system-mipsel \
  -M malta -kernel vmlinux \
  -drive file=rootfs.ext2,format=raw \
  -append "root=/dev/sda console=ttyS0" \
  -netdev user,id=n0,hostfwd=tcp:127.0.0.1:8080-:80 \
  -device e1000,netdev=n0 \
  -nographic
```

Discover available hardware:

```bash
qemu-system-arm -machine help
qemu-system-arm -device help
qemu-system-aarch64 -cpu help
```

Do not assume the `virt` machine or virtio devices match vendor firmware. Old router kernels often need `e1000`, `rtl8139`, IDE, SD, or board-specific devices.

## Debugging

```bash
qemu-system-x86_64 -S -gdb tcp:127.0.0.1:1234 ...
gdb vmlinux
(gdb) target remote 127.0.0.1:1234
```

Use `nokaslr` or a deterministic load setup when setting breakpoints by symbol address. For boot sectors, set the GDB architecture to `i8086`.

## Storage and images

```bash
qemu-img info disk.img
qemu-img convert -O raw vendor.vmdk rootfs.raw
qemu-img resize scratch.qcow2 +256M
```

Prefer read-only source images and copy-on-write scratch layers for experiments. Record image format explicitly; guessing raw vs qcow2/vmdk causes misleading boot failures.

## Validation signals

- user-mode syscall trace reaches the behavior under study
- serial console prints the expected boot/init line
- GDB can halt at a relevant symbol/address
- guest service responds through a localhost-bound forward
- disk or filesystem mutation is visible in a scratch image

## Failure triage

- No output: wrong console, machine, DTB, storage root, or guest waiting before serial init.
- Kernel panic: capture the full first panic line and root-device hints.
- Network dead: check NIC model, guest IP, service process, firewall, and hostfwd syntax.
- Illegal instruction: wrong CPU model or missing extension.
- User-mode loader error: wrong sysroot/interpreter/libc version.

