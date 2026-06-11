# Linux syscall dispatch internals (x86-64 focus)

Load when designing low-level tool dispatcher strategies (vDSO, libc, direct syscalls) and handling telemetry impacts.

For low-level tooling, where the `syscall` instruction executes from is operationally important. Kernel-side telemetry can attribute origin differently depending on whether dispatch comes from vDSO, libc, or your own text section.

## x86-64 syscall ABI invariants

Register contract:

- `rax` = syscall number
- `rdi`, `rsi`, `rdx` = args 1-3
- `r10`, `r8`, `r9` = args 4-6
- return value in `rax` (`< 0` means `-errno`)

Critical detail: `syscall` clobbers `rcx` and `r11`. This is why arg4 is passed in `r10` and not `rcx`.

## Dispatch source patterns

Common practical modes:

- **vDSO gadget dispatch**: call into a `SYSCALL;RET` sequence (`0F 05 C3`) found in `linux-vdso.so.1`
- **libc gadget fallback**: same gadget pattern from mapped libc text
- **direct asm syscall**: issue `syscall` from your own trampoline code
- **runtime raw syscall fallback**: language runtime wrapper path

Each mode can differ in observed origin/fingerprint profile while still reaching the same kernel syscall path.

## Robust fallback chain design

A resilient resolution strategy:

1. Parse `AT_SYSINFO_EHDR` from `/proc/self/auxv` to locate vDSO base
2. Validate ELF and scan executable segment for `0F 05 C3`
3. If unavailable, parse `/proc/self/maps` for libc text mapping and rescan
4. Final fallback: direct asm syscall path

This avoids hard failure when vDSO layout differs across kernel/distro builds.

## Wrapper correctness patterns

Useful defensive wrapper habits:

- Return fast on zero-length buffers in `read` and `write`
- For string syscalls like `openat`, ensure explicit NUL termination
- For syscalls writing kernel-side structs (for example `pipe2`), use correctly sized raw buffers and convert explicitly
- Normalize negative returns into `errno` at wrapper boundaries

## Telemetry and troubleshooting implications

When behavior differs between hosts:

- Verify which dispatch source is active (vDSO/libc/direct)
- Verify ABI register placement for 4-6 arg syscalls (`r10` especially)
- Confirm that fallback did not silently switch execution mode
- Compare kernel version, vDSO mapping, and libc build

## Frequent mistakes

- Treating all “direct syscall” implementations as observably identical
- Assuming `rcx` carries arg4 on x86-64 syscall entry
- Skipping fallback design and breaking on hosts with unusual vDSO layout
- Handling negative syscall returns as valid payload instead of `errno`
