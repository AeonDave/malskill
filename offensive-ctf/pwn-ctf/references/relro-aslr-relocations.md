# RELRO, ASLR, and ELF Relocations

Use this when a pwn task depends on GOT/PLT behavior, ELF relocation targets, leakless ASLR reasoning, partial pointer overwrites, or confusion between `RELRO`, `REL`, and `RELA`.

## Table of Contents

- [Activation cues](#activation-cues)
- [Mental model](#mental-model)
- [Fast inspection](#fast-inspection)
- [RELRO is per object](#relro-is-per-object)
- [Relocation math that matters for exploits](#relocation-math-that-matters-for-exploits)
- [ASLR-invariant partial overwrite gate](#aslr-invariant-partial-overwrite-gate)
- [Reliability hazards](#reliability-hazards)
- [FSOP and libc-data targets](#fsop-and-libc-data-targets)
- [Evidence block](#evidence-block)
- [Research trail](#research-trail)

## Activation cues

Load this reference when any of these are true:

- `checksec` shows Partial or Full RELRO and the exploit plan mentions GOT, PLT, `ret2dlresolve`, `.fini_array`, libc data, or loader state.
- A write primitive can only change 1-3 low bytes of a pointer and the target runs with ASLR.
- Local testing works only with ASLR disabled, but remote spawns a fresh process for every attempt.
- A shared object such as `libc.so.6` is being treated as if it had the same RELRO state as the main executable.
- A relocation table entry, `Elf64_Rela`, `R_X86_64_RELATIVE`, `R_X86_64_JUMP_SLOT`, or `R_X86_64_GLOB_DAT` is part of the exploit path.
- A trigger depends on `exit`, `_exit`, `abort`, assert, `malloc_printerr`, or stdio cleanup.

## Mental model

Keep four terms separate:

| Term | Meaning | Exploit relevance |
| --- | --- | --- |
| `RELRO` | Loader/linker hardening that places relocation-resolved regions in `PT_GNU_RELRO`, then `mprotect`s them read-only. | Decides whether a target slot remains writable at runtime. |
| `REL` / `RELA` | Relocation record formats. `RELA` stores an explicit `r_addend`; `REL` stores the addend in the target location. | Explains why runtime pointers are initialized as `base + addend` and which bytes are stable under ASLR. |
| GOT / PLT | Tables/stubs used for dynamic symbol addresses and lazy/eager binding. | Provides leak targets, call targets, and sometimes writable function-pointer slots. |
| ASLR / PIE | Runtime base randomization for the executable, shared libraries, heap, stack, and mappings. | Forces a leak, an oracle, a non-randomized target, or an ASLR-invariant overwrite. |

Practical rule: **RELRO answers “is this page writable?”; relocations answer “what value did the loader write there?”; ASLR answers “which high bytes can I know or preserve?”**

## Fast inspection

Run the checks on every relevant ELF object, not just the main executable.

```bash
checksec --file ./chall
checksec --file ./libc.so.6
readelf -Wl ./chall | grep -E "GNU_RELRO|LOAD"
readelf -Wd ./chall | grep -E "BIND_NOW|FLAGS_1.*NOW|JMPREL|PLTGOT|RELA|REL"
readelf -Wr ./chall | grep -E "JUMP_SLOT|GLOB_DAT|RELATIVE|COPY"
objdump -R ./chall
```

For shared libraries and runtime permission checks:

```bash
checksec --file ./libc.so.6
readelf -Wl ./libc.so.6 | grep -E "GNU_RELRO|LOAD"
readelf -Wd ./libc.so.6 | grep -E "BIND_NOW|FLAGS_1.*NOW|JMPREL|PLTGOT|RELA|REL"
readelf -Wr ./libc.so.6 | grep -E "JUMP_SLOT|GLOB_DAT|RELATIVE|_IO_|system|malloc|free"
cat /proc/$pid/maps | grep -E "chall|libc|ld-linux"
```

Debugger reminders:

- In GDB, enable ASLR when reproducing remote behavior: `set disable-randomization off`.
- Prefer `vmmap`/`info proc mappings` and direct memory permissions over section names; section headers can be absent or misleading at runtime.
- Inspect `r_offset` as an object-relative virtual address. The runtime address is usually `object_base + r_offset` for ET_DYN objects.

## RELRO is per object

Do not infer process-wide writability from one `checksec` line.

| State | Loader behavior | What stays useful |
| --- | --- | --- |
| No RELRO | GOT-like relocation storage stays writable. | Direct GOT overwrite is usually viable if addresses are known. |
| Partial RELRO | Non-PLT `.got` goes into `PT_GNU_RELRO`; lazy-binding `.got.plt` remains writable. | `R_*_JUMP_SLOT` slots may be writable; `.fini_array`/`.dynamic` often are not. |
| Full RELRO | `-z now` / eager binding resolves PLT slots before `main`, then `.got` and `.got.plt` are protected. | Look for non-GOT writable control data, leaks, ROP/SROP, FSOP, or data-only impact. |

Important nuance: every ET_DYN object has its own program headers, dynamic tags, relocation tables, and `PT_GNU_RELRO` range. A Full RELRO main binary does **not** prove that `libc.so.6`, `ld-linux`, or another DSO has Full RELRO. Check each file and confirm runtime page permissions.

When a plan says “overwrite libc GOT,” require all of this evidence:

1. The target slot's runtime address is in a writable mapping in `/proc/$pid/maps`.
2. The target object is loaded and its base is known, leaked, or preserved by an existing pointer.
3. The slot value will not be rewritten by a future lazy resolver call before the trigger.
4. The trigger actually dereferences that slot after your write.

## Relocation math that matters for exploits

On x86-64, dynamic relocations are commonly `Elf64_Rela` records:

```text
Elf64_Rela {
  r_offset  # where the relocation is applied, object-relative for ET_DYN
  r_info    # symbol index + relocation type
  r_addend  # explicit addend
}
```

For practical pwn work, the common cases are:

| Relocation | Runtime effect | Pwn use |
| --- | --- | --- |
| `R_X86_64_RELATIVE` | write `object_base + r_addend` at `object_base + r_offset`; no symbol lookup. | Explains many initialized libc/global pointers and why low-byte pointer rewrites can preserve ASLR high bytes. |
| `R_X86_64_GLOB_DAT` | symbol lookup result is written to a GOT entry during relocation. | Eagerly resolved data/function pointer; often protected by RELRO if in `.got`. |
| `R_X86_64_JUMP_SLOT` | PLT/lazy binding slot for imported function calls. | Classic GOT overwrite target under no/partial RELRO; under Full RELRO it is eagerly resolved and protected. |
| `R_X86_64_COPY` | runtime linker copies shared-object data into writable executable storage. | Can create surprising writable aliases in the main executable. |

Exploit implication: if a pointer slot originally contains `B + old_addend` and your target is `B + new_addend` in the **same object**, a low-byte overwrite may be ASLR-invariant because the unknown base `B` is preserved in the high bytes already stored in memory.

If the two pointers are in different mappings, a partial overwrite is usually not invariant unless those mappings share the preserved high bytes by accident. Treat that as brute force, not proof.

## ASLR-invariant partial overwrite gate

For an `n`-byte overwrite of an existing 64-bit pointer:

```python
mask = (1 << (8 * n)) - 1
patched = (old_runtime & ~mask) | (target_runtime & mask)
works = patched == target_runtime
```

You do not know `old_runtime` or `target_runtime` fully without a leak, but for same-object pointers:

```python
old_runtime = base + old_off
target_runtime = base + target_off
```

The overwrite is invariant only if `(base + old_off) & ~mask == (base + target_off) & ~mask` for every base value the service can use. Linux mappings are page-aligned, so low 12 base bits are zero, but higher low bytes can still vary between runs.

Checklist before calling a partial overwrite “ASLR-safe”:

1. **Same object**: old pointer and target pointer must share the same randomized base.
2. **Same preserved-byte window**: high bytes above the overwrite width must match after adding offsets to the base.
3. **No carry surprise**: adding `old_off` vs `target_off` must not carry differently into byte `n` for possible bases.
4. **Endian order**: low-byte writes patch least-significant bytes on little-endian x86-64.
5. **Canonical address remains valid**: do not create non-canonical or unmapped addresses while partially writing.
6. **Pointer is read after all writes**: no allocator, stdio, resolver, or application code clobbers the slot before dispatch.

Use a local stress loop with ASLR enabled. For leakless remote services that spawn independent processes, one lucky run is noise. If the service requires `N` independent successes and the per-run success probability is `p`, the overall success is:

$$
P_\text{overall} = p^N
$$

Examples for `N = 32`:

| Per-run success | Overall success |
| --- | --- |
| 99.0% | ~72.5% |
| 99.5% | ~85.2% |
| 99.9% | ~96.8% |

So a “rare carry failure” is still a real bug when the challenge requires many fresh ASLR instances.

## Reliability hazards

- **Local ASLR off**: Docker, GDB, `setarch -R`, or `/proc/sys/kernel/randomize_va_space` can hide a bad invariant.
- **Wrong object**: `exe` Full RELRO does not describe `libc`, `ld-linux`, plugins, or mmaped helper DSOs.
- **Lazy binding race**: an unresolved `JUMP_SLOT` may be overwritten by `_dl_fixup`; call once to resolve or choose a slot that will not be rebound.
- **Section-name trap**: exploit runtime memory permissions, not `.got`/`.got.plt` names alone. Full RELRO can merge or rename sections.
- **Allocator clobber**: `free()` writes tcache `next`/key metadata into freed chunks; fastbin/tcache paths can overwrite the byte you planned to preserve.
- **Cleanup mismatch**: `_exit()` bypasses normal `exit()` handlers and stdio cleanup. Validate the actual trigger path instead of assuming `return from main` behavior.
- **Signal/error path mismatch**: `abort`, assert, and `malloc_printerr` behavior varies by glibc path and target state. Break on the intended internal call before relying on it.
- **Bad-byte truncation**: partial writes sent through text protocols may stop at whitespace, newline, NUL, or signed-integer parsing boundaries.

## FSOP and libc-data targets

When FSOP depends on libc data or relocation slots:

1. Identify the exact libc build and libio offsets.
2. Check whether the target pointer was loader-initialized by `R_X86_64_RELATIVE`, `GLOB_DAT`, or `JUMP_SLOT`.
3. Confirm the target page is writable in the live process.
4. If using a partial overwrite, prove same-object offset invariance with ASLR enabled.
5. Validate the full dispatch chain with breakpoints: e.g. stream operation -> libio helper -> indirect call target.
6. Treat trigger corruption as a separate hypothesis from FILE layout corruption. A perfect FILE object still fails if the trigger path clobbers or skips it.

Common high-value questions:

- Does the application call `exit()` or `_exit()`?
- Is there an error path that reaches a validated flush or libio dispatch path?
- Will `free()` or `malloc()` rewrite the fake chunk fields before the error path?
- Are `_wide_data`, `_wide_vtable`, `_lock`, `_mode`, and relevant write/read pointers still coherent at dispatch?

## Evidence block

Record this before finalizing a RELRO/ASLR relocation exploit path:

```text
Objects checked:
- chall: RELRO=<none|partial|full>, PIE=<yes|no>, base source=<fixed|leak|preserved>
- libc: RELRO=<none|partial|full>, build-id=<id>, base source=<leak|preserved|bruteforce>

Target slot:
- object=<chall|libc|ld|plugin>
- relocation=<type or none>
- file offset/VA=<...>
- runtime address formula=<base + offset>
- runtime page permission=<rw-p/r--p>

ASLR proof:
- overwrite width=<1|2|3|... bytes>
- old offset=<...>
- target offset=<...>
- invariant check=<pass/fail and why>
- stress result=<successes>/<runs> with ASLR on

Trigger proof:
- trigger path=<function chain>
- breakpoints hit=<yes/no>
- clobber checks=<allocator/stdio/resolver/application>
```

## Research trail

- Red Hat, “Hardening ELF binaries using Relocation Read-Only (RELRO)” — clear partial vs full RELRO behavior and GOT writability.
- MaskRay, “All about Global Offset Table” — GOT entries, `PT_GNU_RELRO`, `.got`/`.got.plt`, and linker-loader protocol details.
- MaskRay, “All about Procedure Linkage Table” — lazy vs eager binding and `R_*_JUMP_SLOT` resolver behavior.
- MaskRay, “Relative relocations and RELR” — `REL` vs `RELA`, relative relocation representation, and loader-side base/addend reasoning.
- Oracle Linker and Libraries Guide, “Relocation Sections” — ABI notation: `B` base, `A` addend, `S` symbol, and x64 relocation calculations.
- System Overlord, “GOT and PLT for pwning” — pwn-oriented walkthrough of GOT/PLT and RELRO implications.
- CTF101, “ASLR” and “RELRO” — compact challenge-level refresher for mitigation triage.
