# Firmware Rehosting

Use this reference for router, camera, appliance, NAS, printer, and IoT Linux-style firmware.

## Extraction and inventory

```bash
file firmware.bin
binwalk firmware.bin
binwalk -Me firmware.bin
find _firmware.bin.extracted -type f -exec file {} + | grep -E 'ELF|script|Squashfs|UBI'
```

Map:

- kernel, initramfs, rootfs, DTB, bootloader, upgrade container
- CPU arch/endian and libc family
- `/etc/inittab`, `/etc/init.d`, `rcS`, `procd`, systemd units, vendor launchers
- web roots, CGI/Lua/PHP handlers, service binaries, config paths
- NVRAM defaults, certificates, keys, passwords, model/board identifiers

Use `unsquashfs`, `sasquatch`, `jefferson`, `ubi_reader`, `cpio`, `tar`, `7z`, `dtc`, and `qemu-img` according to the container type.

## Rehosting order

1. Extract enough rootfs to run one service binary.
2. Try QEMU user-mode with the extracted sysroot.
3. Add missing config/NVRAM files only when traces prove the expected paths.
4. Run the service with localhost-only networking and external clients (`curl`, browser, `ssh`, `ftp`, `telnet`, `nc`, protocol-specific Python).
5. If init, kernel, netdev, or device behavior matters, escalate to QEMU full-system or a firmware framework.
6. If board peripherals dominate, switch to board simulation or document the missing model.

## User-mode service pattern

```bash
qemu-mipsel -L ./squashfs-root -strace ./squashfs-root/usr/sbin/httpd -f /etc/httpd.conf
qemu-arm -L ./squashfs-root ./squashfs-root/bin/busybox sh
```

When paths are absolute, use an isolated chroot/proot/container rootfs. Populate only observed necessities:

- `/proc`, `/dev/null`, `/dev/urandom`, `/tmp`
- expected config files
- NVRAM/key-value stores or simple wrapper binaries if the service only checks configuration
- writable log/cache dirs

## Full-system pattern

Use QEMU system when the target needs kernel init, real init scripts, netdevs, block devices, or kernel modules.

```bash
qemu-system-mipsel \
  -M malta -kernel vmlinux \
  -drive file=rootfs.ext2,format=raw \
  -append "root=/dev/sda console=ttyS0" \
  -netdev user,id=n0,hostfwd=tcp:127.0.0.1:8080-:80 \
  -device e1000,netdev=n0 \
  -nographic
```

Use `qemu-system-<arch> -machine help` and `-device help`; do not assume `virtio` works for old vendor kernels.

## Frameworks

- FirmAE/Firmadyne: useful for automated router rehosting and network inference; inspect generated commands instead of treating success/failure as magic.
- EMUX: useful when the goal is web-service rehosting from firmware.
- Avatar2: useful for hybrid emulation/hardware research and peripheral forwarding.
- QEMU + manual rootfs patches remains the baseline when frameworks fail.

## Validation signals

- service listens on the intended port and responds to an external request
- UART/serial console reaches init or shell prompt
- init script launches the target daemon
- expected config path is opened and parsed
- packet capture shows expected protocol exchange
- filesystem diff shows expected runtime state

## Failure pivots

- Wrong NIC: try `e1000`, `rtl8139`, platform-specific NIC, or explicit kernel config clues.
- Reboot/watchdog loop: patch init scripts or disable watchdog only if that is not the behavior under study.
- Missing NVRAM: trace key names and create minimal defaults; avoid huge fake environments.
- SquashFS extraction fails: try the right endian/compression variant or `sasquatch`.
- Kernel/rootfs mismatch: pair artifacts from the same firmware version when possible.

