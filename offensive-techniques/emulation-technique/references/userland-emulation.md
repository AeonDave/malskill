# Userland Emulation

Use this reference for process-level execution where the target is an application or service binary rather than a whole board.

## QEMU user-mode first

Best for Linux/BSD userland executables when you have a compatible sysroot.

```bash
file ./bin/target
readelf -hW ./bin/target
readelf -lW ./bin/target | grep 'Requesting program interpreter'

qemu-mipsel -L ./rootfs ./bin/target
qemu-arm -L ./rootfs -strace ./bin/target arg1
qemu-aarch64 -L ./rootfs -g 1234 ./bin/target
```

Use `-L` or `QEMU_LD_PREFIX` for dynamic ELF dependencies. If the target expects absolute paths, use a chroot/proot/container copy of the rootfs, then run the matching `qemu-*-static` inside it.

Good signals:

- target reaches `main` or expected init
- syscall trace shows expected file/network operations
- service binds a localhost-forwarded port
- GDB can break on the function under study

Failure pivots:

- `No such file or directory` on an existing binary usually means missing interpreter.
- glibc symbol-version errors mean wrong sysroot, not wrong executable.
- `SIGILL` suggests CPU extension mismatch or wrong ARM/Thumb state.
- Missing `/proc`, `/dev`, `/tmp`, config, or NVRAM paths may need bind mounts or scratch files.

## Qiling when OS behavior must be shaped

Use Qiling when the useful move is to intercept syscalls/APIs, fake files/registry, hook addresses, hotpatch checks, or run a PE/Mach-O/ELF with a controlled OS model.

```bash
qltool run -f ./rootfs/bin/target --rootfs ./rootfs
qltool run -f ./sample.exe --rootfs ./rootfs/x8664_windows --json
qltool code --os linux --arch arm --format hex -f shellcode.hex
```

Prefer task-local harnesses only when `qltool` is not enough. Keep hooks minimal and label every fake result.

Use Qiling for:

- Windows/Linux/macOS/UEFI-style API and syscall interception
- rootfs-backed execution with mapped files
- registry/config fakes
- unpacking/decryption routines that need OS calls
- dynamic patching without debugger artifacts

Do not use Qiling as proof of complete OS or hardware parity. Missing syscall/API errors are normal boundaries; hook them only when they are not the behavior being tested.

## Native sandbox as last resort

Use a disposable VM when the target needs exact kernel, GUI, driver, EDR, browser, or proprietary runtime behavior that emulators cannot model. Keep network isolated and capture process/file/registry/network telemetry.

## Instrumentation stack

- `strace -f -o trace.log`: Linux syscall path, files, processes, sockets.
- `ltrace -f -o ltrace.log`: libc/library calls where dynamic linking works.
- GDB/lldb: breakpoints, registers, memory dumps, remote QEMU gdbstub.
- Frida: API hooks, argument logging, bypassing runtime checks, TLS pinning in lab apps.
- `tcpdump`/Wireshark: packets from emulated or sandboxed services.
- `socat`/`nc`/`curl`: external endpoint proof without embedding protocol clients in the analysis logic.

