---
name: linux-internals
description: |
  Linux internals knowledge base for offensive and defensive programming: ELF loading and relocation behavior, procfs and process metadata semantics, namespace lifecycle and capability boundaries, eBPF verifier and map and attachment mechanics, and LSM hook and policy surfaces. Use when writing implants, loaders, syscall-level tooling, container escape research, eBPF probes, or hardening and telemetry logic that needs kernel-level mechanics beyond userland APIs.
license: MIT
compatibility: Linux kernels 5.4 through 6.x on x86-64 and ARM64. Interfaces and struct layouts can vary by kernel version and distro patches, so verify against running kernel docs and headers before production use.
metadata:
  author: AeonDave
  version: "1.0"
---

# linux-internals

Deep Linux internals for practitioners who need to reason below libc and framework abstractions.

This skill is for structural mechanics: what the kernel and loader actually do, what invariants hold, what breaks across versions, and where detection surfaces appear.

---

## When to activate

- You are writing or reviewing custom ELF loaders, in-memory execution, or reflective mapping logic
- You are parsing `/proc` for process, memory, mount, or namespace intelligence and need race-safe interpretation
- You are building namespace or container boundary logic with `clone`, `unshare`, `setns`, or pidfd flows
- You are loading eBPF programs and debugging verifier failures, helper constraints, map lifetime, or attach semantics
- You are reasoning about LSM policy behavior, hook order, and process security attribute surfaces
- You need to explain detection and hardening implications of low-level Linux behavior

If the task is ordinary userland API usage, this skill is overkill. If the task is ABI and kernel boundary mechanics, use this skill first.

---

## Territory map

| Domain | File | Covers |
|---|---|---|
| ELF and dynamic linking | `references/elf-format.md` | ELF headers, program headers vs sections, dynamic tags, relocation flow, loader order, practical invariants |
| procfs semantics | `references/procfs.md` | `/proc` layout, ptrace-gated visibility, `maps` and `smaps` races, `hidepid`, mountinfo and pidns interactions |
| Namespaces and isolation | `references/namespaces.md` | namespace APIs, ownership and capability checks, pid and user namespace rules, lifetime pinning |
| Syscall dispatch internals | `references/syscall-dispatch-linux.md` | x86-64 syscall ABI details, vDSO-sourced syscall gadgets, fallback chains, errno handling, and telemetry implications |
| eBPF architecture | `references/ebpf.md` | `bpf()` command families, map and program lifecycle, verifier model, helper constraints, attach and pin patterns |
| LSM model | `references/lsm.md` | LSM stacking and ordering, active module discovery, process attr interfaces, hook surfaces and development implications |

---

## Quick invariants

| Area | Invariant |
|---|---|
| ELF | Runtime loading is driven by **program headers**, not section headers |
| ELF | `PT_LOAD`: `p_filesz <= p_memsz`; trailing bytes are zero-filled in memory |
| procfs | Access to many `/proc/pid/*` files for other processes is ptrace capability gated |
| procfs | Reading `maps` and `smaps` is inherently racy except single-read snapshots |
| namespaces | Joining namespaces requires capability checks in both current and owning user namespaces |
| pid namespaces | A process cannot move to an ancestor PID namespace |
| syscalls (x86-64) | Arg4 is in `r10`, not `rcx`; `syscall` clobbers `rcx` and `r11` |
| eBPF | Verifier must prove termination, type safety, bounds safety, and reference release on all paths |
| eBPF | Helper calls can invalidate packet pointer proofs; bounds checks often must be redone |
| LSM | Active LSM order matters; checks run in configured order, capability module first |
| LSM | `/sys/kernel/security/lsm` reflects the active stack and check order |

---

## Decision flow: choose the right subsystem lens

1. Issue is binary load or symbol resolution behavior
   - Start in `elf-format.md`
   - Validate `PT_INTERP`, `DT_NEEDED`, `DT_RPATH` and `DT_RUNPATH`, then relocation type flow

2. Issue is process or memory inspection mismatch
   - Start in `procfs.md`
   - Validate ptrace permission model, `hidepid` mode, and map-read race conditions

3. Issue is container boundary or namespace transition
   - Start in `namespaces.md`
   - Validate ownership user namespace, capability context, and one-way PID namespace movement

4. Issue is syscall origin, anti-hooking, or low-level ABI behavior
  - Start in `syscall-dispatch-linux.md`
  - Validate calling convention (`r10`/`rcx`), dispatch source (vDSO vs libc vs direct), and fallback implications

5. Issue is eBPF load rejection or runtime attach surprises
   - Start in `ebpf.md`
   - Read verifier error class first, then map/program refs and attach target constraints

6. Issue is policy enforcement or security hook behavior
   - Start in `lsm.md`
   - Confirm active stack and hook order before attributing allow or deny outcomes

---

## Detection and hardening surface checklist

Use this whenever implementing a low-level technique.

- ELF path
  - Does behavior depend on dynamic linker search path state such as RUNPATH, cache, preload, or secure-exec stripping?
- procfs path
  - Are you assuming stable snapshots from files documented as racy?
  - Are you accidentally leaking sensitive args or env due to permissive proc mount options?
- namespace path
  - Are capability checks evaluated in the expected owning user namespace?
  - Could namespace lifetime be pinned by open descriptors or bind mounts?
- syscall path
  - Is the syscall instruction sourced from the location you think it is (vDSO/libc/direct asm), and does that match your telemetry assumptions?
  - Are x86-64 register conventions respected for 4-6 argument syscalls?
- eBPF path
  - Are helper or map choices constrained by program type and privilege model?
  - Are verifier assumptions broken by helper-induced packet buffer changes?
- LSM path
  - Is behavior due to stacked module ordering rather than a single policy engine?
  - Are process attrs read from module-specific paths versus legacy aggregate paths?

---

## Pitfalls

- Treating section headers as mandatory at runtime for execution behavior
- Assuming `DT_RPATH` and `DT_RUNPATH` are equivalent in dependency traversal
- Assuming `/proc/pid/maps` partial reads are stable under concurrent VMA changes
- Forgetting `hidepid` and ptrace gating when process inventory appears incomplete
- Expecting `setns` to move the caller itself into a new PID namespace instead of affecting future children
- Trying to reenter same user namespace to regain dropped capabilities
- Passing syscall arg4 in `rcx` instead of `r10` on x86-64 and then debugging phantom failures
- Assuming all direct-syscall approaches have the same observable syscall origin in kernel telemetry
- Ignoring eBPF reference-release paths after socket lookup helpers
- Debugging eBPF without verifier logs, then guessing blindly
- Attributing policy outcomes to one LSM without checking active stack order

---

## Resources

- `references/elf-format.md` for loader and relocation mechanics
- `references/procfs.md` for process and memory introspection semantics
- `references/namespaces.md` for isolation model and transition constraints
- `references/syscall-dispatch-linux.md` for syscall ABI, dispatch-source tradeoffs, and fallback design
- `references/ebpf.md` for verifier and syscall-level eBPF operations
- `references/lsm.md` for LSM architecture and policy interaction model
