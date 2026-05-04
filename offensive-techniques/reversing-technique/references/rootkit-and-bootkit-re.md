# Rootkit and bootkit reverse engineering

## Purpose

Analyze kernel-mode malware, drivers, boot-stage components, and firmware-adjacent persistence with a safety-first workflow.

## When to use

- Unknown Windows driver or Linux kernel module.
- Evidence of hidden processes, files, registry keys, sockets, or callbacks.
- Bootloader, EFI system partition, or MBR/GPT modification.
- Security product tampering, DSE/PatchGuard bypass indicators, or kernel callback abuse.

## Safety model

- Analyze in isolated VMs or sacrificial hardware.
- Disable shared folders and host clipboard.
- Keep kernel debugging network separate.
- Snapshot before loading any driver or boot artifact.
- Prefer static analysis until load prerequisites are understood.

## Windows driver triage

1. Validate PE driver type, signing state, timestamp, imports, and sections.
2. Identify `DriverEntry`, unload routine, dispatch table, and device objects.
3. Map IOCTL handlers and user-mode control surface.
4. Enumerate kernel APIs: process/thread callbacks, registry callbacks, minifilter, WFP, ETW, SSDT-like behavior.
5. Check for DSE bypass, vulnerable-driver loading, or PatchGuard-sensitive modifications.
6. Correlate with service registry keys and driver load events.

High-value imports/patterns:

- `PsSetCreateProcessNotifyRoutine`, `PsSetLoadImageNotifyRoutine`.
- `CmRegisterCallback`, minifilter registration, WFP callouts.
- `ZwQuerySystemInformation`, `MmMapIoSpace`, `MmGetSystemRoutineAddress`.
- IOCTL dispatch with weak access control.
- Direct kernel object manipulation and linked-list unlinking.

## Linux kernel module triage

1. Identify module metadata, vermagic, init/exit functions.
2. Review hooks: syscall table, ftrace, kprobes, eBPF, LSM, netfilter.
3. Inspect procfs/sysfs/debugfs interfaces.
4. Look for hidden task/module/file/network logic.
5. Correlate with persistence: `/etc/modules`, DKMS, initramfs, systemd loaders.

## Bootkit workflow

1. Preserve disk image and firmware/ESP artifacts.
2. Inspect partition table, boot sectors, EFI system partition, and boot manager entries.
3. Compare bootloader hashes against vendor baselines.
4. Check Secure Boot state and suspicious drivers in EFI paths.
5. Trace handoff chain: firmware → boot manager → loader → kernel → early drivers.
6. Correlate with full-disk encryption configuration and recovery-key events.

## Dynamic analysis

Windows:

- Use WinDbg kernel debugging with symbols.
- Break on driver load and IOCTL dispatch.
- Monitor callbacks, object creation, and hidden artifacts.

Linux:

- Use QEMU/KVM snapshots, `dmesg`, ftrace, kprobes, and crash dumps.
- Avoid loading unknown modules on analyst workstations.

## Evidence requirements

- Driver/module hash and signing state.
- Load path and persistence mechanism.
- Hook/callback list with code references.
- User-mode control channel if present.
- Hidden artifact proof with before/after or raw structure evidence.

## Common pitfalls

- Loading a driver before understanding its OS/version requirements.
- Mistaking legitimate EDR kernel components for malicious code without corroboration.
- Ignoring user-mode controller binaries.
- Assuming a boot artifact is malicious without vendor baseline comparison.
- Forgetting that kernel tampering can crash the VM and destroy volatile evidence.
