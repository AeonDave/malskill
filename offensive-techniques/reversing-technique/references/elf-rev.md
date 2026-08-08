# ELF Reverse Engineering Supplement

Load this after `triage.md` and `re-workflow.md` when the sample is an ELF. This supplement focuses on ELF-only pivots: program headers, the Linux dynamic loader, PLT/GOT behavior, relocations, RELRO/ASLR evidence, constructors, IFUNC, symbol versioning, packers, and Linux runtime surfaces.

## Table of contents

- [ELF-only fast checks](#elf-only-fast-checks)
- [Linux loader-aware workflow](#linux-loader-aware-workflow)
- [Dynamic linker evidence](#dynamic-linker-evidence)
- [PLT, GOT, relocations, and RELRO](#plt-got-relocations-and-relro)
- [Symbol versioning and interposition](#symbol-versioning-and-interposition)
- [Pre-main execution paths](#pre-main-execution-paths)
- [Runtime instrumentation](#runtime-instrumentation)
- [Packing, header abuse, and in-memory loading](#packing-header-abuse-and-in-memory-loading)
- [Format-specific checklists](#format-specific-checklists)
- [Exploitability handoff](#exploitability-handoff)
- [Common pitfalls](#common-pitfalls)
- [Research trail](#research-trail)

## ELF-only fast checks

```bash
file sample.elf
readelf -Wh sample.elf
readelf -Wl sample.elf
readelf -Wd sample.elf
readelf -Wr sample.elf
readelf -Ws sample.elf | head
readelf -V sample.elf
checksec --file ./sample.elf
```

Answer these first:

1. **PIE or fixed-base?** PIE changes whether the main executable base is randomized.
2. **glibc, musl, static, or custom loader?** The interpreter and libc family determine loader behavior and symbol signatures.
3. **Dynamic or syscall-heavy?** Malware often mixes libc wrappers with raw syscalls.
4. **Which runtime objects matter?** Check the main executable and every DSO involved in the behavior or exploit path.
5. **Constructor or IFUNC abuse?** `.preinit_array`, `.init_array`, legacy constructors, and IFUNC resolvers can run before `main`.
6. **Packed or fileless?** Corrupted headers, high entropy, `memfd_create`, or `/proc/self/fd/*` loading mean split outer loader from inner payload.

## Linux loader-aware workflow

### 1. Read program headers before sections

ELF runtime behavior is driven by program headers and dynamic entries. Section headers help tools, but a stripped or hostile ELF can run without useful section metadata.

Prioritize:

- `PT_INTERP`: runtime dynamic loader path, such as `/lib64/ld-linux-x86-64.so.2`.
- `PT_LOAD`: mapped segments, runtime permissions, and base-address math.
- `PT_DYNAMIC`: dynamic linker metadata (`DT_*`).
- `PT_TLS`: static thread-local storage.
- `PT_GNU_STACK`: executable-stack signal.
- `PT_GNU_RELRO`: memory range the loader should make read-only after relocations.

```bash
readelf -Wl sample.elf | grep -E "INTERP|LOAD|DYNAMIC|TLS|GNU_STACK|GNU_RELRO"
```

Evidence rule: if sections and segments disagree, the loader follows segments.

### 2. Inspect dynamic entries as the loader's script

High-value entries:

| Dynamic entry | Why it matters |
|---|---|
| `DT_NEEDED` | Direct shared-library dependencies |
| `DT_RPATH` / `DT_RUNPATH` | Search-path hijack and environment-sensitive loading clues |
| `DT_SONAME` | DSO identity used by dependents |
| `DT_JMPREL` | PLT relocation table used for imported calls |
| `DT_PLTGOT` | GOT/PLT anchor for lazy binding |
| `DT_RELA` / `DT_REL` / `DT_RELASZ` / `DT_RELSZ` | Non-PLT relocation tables |
| `DT_BIND_NOW`, `DF_1_NOW` | Eager binding; relevant to full RELRO and resolver breakpoints |
| `DT_INIT`, `DT_INIT_ARRAY`, `DT_PREINIT_ARRAY`, `DT_FINI_ARRAY` | Pre/post-main execution |
| `DT_SYMTAB`, `DT_STRTAB`, `DT_GNU_HASH`, `DT_HASH` | Dynamic symbol discovery and hash-table behavior |
| `DT_VERNEED`, `DT_VERDEF`, `DT_VERSYM` | Symbol versioning and binding compatibility |

```bash
readelf -Wd sample.elf
readelf -Wr sample.elf | grep -E "JUMP_SLOT|GLOB_DAT|RELATIVE|COPY|IRELATIVE|TLSDESC"
```

### 3. Separate stripped-binary problems from language-runtime problems

- **Stripped C/C++**: recover anchors from imports, strings, relocation targets, and calling patterns.
- **Go / Rust / Nim / Python-packed ELF**: pivot to `languages.md` or the dedicated language supplement.
- **Embedded ELF inside firmware**: pivot to `firmware-rev.md`.
- **Second-stage ELF loaded from memory**: pivot to `in-memory-loading.md`.

Do not rebuild generic language metadata by hand if runtime fingerprints already identify the compiler ecosystem.

### 4. Check Linux-specific execution surfaces

- file/network/process syscalls
- persistence via service/unit files, cron, shell init files
- credential access via `/proc`, `/etc`, SSH keys, browser stores
- privilege boundaries: setuid, file capabilities, namespaces, seccomp, containers
- loader environment: `LD_PRELOAD`, `LD_AUDIT`, `LD_LIBRARY_PATH`, `LD_BIND_NOW`, `LD_DEBUG`

```bash
strings -a sample.elf | grep -iE "/proc/|/etc/|systemd|cron|ssh|iptables|bashrc|ld_preload|ld_audit|seccomp|cap_"
```

## Dynamic linker evidence

Use loader instrumentation when imports, dependencies, or call targets do not match static expectations.

```bash
LD_TRACE_LOADED_OBJECTS=1 ./sample.elf
LD_DEBUG=libs,bindings,reloc ./sample.elf 2> ld-debug.log
LD_BIND_NOW=1 ./sample.elf
```

Controlled loader pivots:

- **`LD_BIND_NOW=1`** forces eager symbol resolution. It helps expose broken imports and lets you compare lazy vs eager resolver behavior.
- **`LD_DEBUG=libs,bindings,reloc`** records library search, binding, and relocation activity without building a custom tracer.
- **`LD_AUDIT=./audit.so`** subscribes to dynamic-loader events (`la_objopen`, `la_objsearch`, `la_symbind*`) and can reveal late `dlopen`/symbol-binding behavior.
- **`LD_PRELOAD=./shim.so`** can interpose symbols for observation in a lab, but fails or is sanitized in secure-execution contexts.
- **`dlopen` / `dlsym` / `dlvsym` / `dlmopen`** indicate late loading, version-specific lookup, or namespace isolation.

Caveats:

- Setuid/setgid or otherwise secure-execution paths sanitize many `LD_*` variables.
- Statically linked binaries bypass most dynamic-loader tricks.
- Malware may call syscalls directly, resolve symbols from its own loader, or validate loaded library paths.

## PLT, GOT, relocations, and RELRO

### 1. Distinguish `.got`, `.got.plt`, and PLT stubs

- `.got` holds loader-initialized addresses and constants used by PIC code.
- `.got.plt` is tied to PLT call indirection and lazy binding.
- The first x86/x86-64 GOTPLT entries are special loader metadata/resolver slots; do not treat them as normal imports.
- `.plt` stubs route imported function calls through GOTPLT entries.
- `.plt.sec` may appear in CET/IBT-aware x86 builds.
- `-fno-plt` codegen may use GOT-indirect calls without classic PLT stubs.

Static inspection:

```bash
objdump -d -j .plt -j .plt.got -j .plt.sec sample.elf
readelf -Wr sample.elf | grep -E "JUMP_SLOT|GLOB_DAT|RELATIVE|IRELATIVE|COPY"
readelf -Wd sample.elf | grep -E "JMPREL|PLTGOT|BIND_NOW|FLAGS_1"
```

### 2. Lazy vs eager binding

Lazy binding path:

```text
call puts@plt -> jump via puts@got.plt -> resolver trampoline -> _dl_runtime_resolve/_dl_fixup -> GOTPLT patched -> future calls jump directly
```

Eager binding path:

```text
LD_BIND_NOW or DF_1_NOW -> loader resolves JUMP_SLOT relocations before user code -> GOTPLT already points to final callees
```

RE implications:

- A GOTPLT value before first call may point back into PLT resolver machinery, not the final libc function.
- Breakpoints on `_dl_fixup` or the imported function can answer whether a binding is lazy, eager, or already resolved.
- Full RELRO usually pairs `PT_GNU_RELRO` with eager binding so `.got.plt` can become read-only after relocations.

### 3. Separate RELRO, relocations, and ASLR

When the objective is memory-corruption exploitation, do not collapse these into one mitigation label:

- `RELRO` is a per-object runtime permission story (`PT_GNU_RELRO` plus loader `mprotect`). Check the main executable and every relevant DSO separately.
- `REL` / `RELA` records explain how loader-initialized pointers were computed. On x86-64, `Elf64_Rela.r_addend` is explicit; `R_X86_64_RELATIVE` commonly materializes pointers as object base plus addend.
- `ASLR` changes object bases per process. A partial pointer overwrite is only stable when the preserved high bytes remain valid under every possible base the service can use.

Fast gate:

```bash
checksec --file ./sample
checksec --file ./libc.so.6
readelf -Wl ./sample | grep -E "GNU_RELRO|LOAD"
readelf -Wd ./sample | grep -E "BIND_NOW|FLAGS_1.*NOW|JMPREL|PLTGOT|RELA|REL"
readelf -Wr ./sample | grep -E "JUMP_SLOT|GLOB_DAT|RELATIVE|COPY|IRELATIVE"
```

For payload decisions, load `../../../offensive-ctf/pwn-ctf/references/relro-aslr-relocations.md` and document the target object, relocation type, runtime page permissions, and ASLR invariant before building payloads.

### 4. Relocation types that change RE conclusions

- `R_*_JUMP_SLOT`: PLT/GOTPLT imported function binding.
- `R_*_GLOB_DAT`: imported object/function address stored in GOT.
- `R_*_RELATIVE`: base-plus-addend pointer materialization; common in PIE/shared objects.
- `R_*_IRELATIVE`: calls a resolver function during relocation; associated with IFUNC-like behavior.
- `R_*_COPY`: copy relocation in executable; can confuse data ownership and interposition assumptions.
- TLS relocations / TLSDESC: thread-local storage access; do not misread as ordinary globals.

## Symbol versioning and interposition

Versioned symbols explain why a symbol name alone is sometimes insufficient.

```bash
readelf -V sample.elf
objdump -T sample.elf | grep '@'
```

What to check:

- `.gnu.version`, `.gnu.version_r`, and `.gnu.version_d` entries.
- Default (`@@`) vs non-default (`@`) symbol versions.
- `dlvsym` call sites that explicitly request a version.
- Weak symbols, protected visibility, and `-Bsymbolic` behavior in DSOs.
- `LD_PRELOAD` interposition failures caused by version or visibility mismatch.

RE implications:

- `dlsym(RTLD_DEFAULT, "foo")` and `dlvsym(..., "foo", "VER")` can resolve different implementations.
- Patching or shimming the wrong symbol version produces misleading runtime evidence.
- Patch diffing should include changed version definitions/requirements, not just changed functions.

## Pre-main execution paths

### Constructors and destructors

Check these before assuming `main` is first meaningful code:

```bash
readelf -W -a sample.elf | grep -iE "preinit_array|init_array|fini_array|\.init|\.ctors|\.dtors"
```

Execution order highlights:

- `DT_PREINIT_ARRAY` applies to executables and runs before normal DSO initializers.
- DSO initializers can run before executable constructors.
- `.init_array` is the modern constructor mechanism; `.ctors` is legacy but still appears.
- `.fini_array` and destructors may perform cleanup, persistence, or anti-forensic actions.

Common constructor duties:

- anti-debug or anti-VM checks
- config decryption
- environment probing
- signal handler or seccomp setup
- fork/daemon setup

### GNU IFUNC / `STT_GNU_IFUNC`

`IFUNC` symbols are resolver functions. The dynamic linker calls the resolver and writes the selected implementation address into the relevant relocation target.

Detection:

```bash
readelf -Ws sample.elf | grep -E "IFUNC|STT_GNU_IFUNC"
readelf -Wr sample.elf | grep -E "IRELATIVE|JUMP_SLOT"
```

RE implications:

- IFUNC resolvers may execute during relocation before constructors.
- A resolver can select CPU-specific code paths or hide custom logic.
- Ghidra may show unresolved indirect calls until runtime concretizes the target.
- Resolver code should normally avoid unsafe global/TLS/external dependencies; malware can abuse that unusual execution phase.

Practical resolution:

1. Break at `_start`, the IFUNC resolver, or `_dl_debug_state`.
2. Run until relocations complete.
3. Inspect the GOT/relocation target for the selected implementation.
4. Annotate decompiler call sites with the concrete target and CPU/environment condition.

## Runtime instrumentation

Use static analysis to form hypotheses, then collect runtime evidence with the smallest tool that answers the question.

| Question | Fast evidence |
|---|---|
| What files, sockets, and processes are touched? | `strace -f -e trace=file,network,process ./sample` |
| Which libc/library calls happen? | `ltrace -f ./sample` |
| Which DSOs load late? | `LD_DEBUG=libs`, GDB `catch load`, `/proc/$pid/maps` |
| Which symbols bind at runtime? | `LD_DEBUG=bindings`, `LD_AUDIT`, break `_dl_fixup` |
| Where is unpacked code mapped? | `/proc/$pid/maps`, `pmap`, GDB `info proc mappings` |
| Does behavior differ under debugger? | compare clean run, `strace`, GDB, and Frida hook runs |

Useful GDB pivots:

```text
set environment LD_BIND_NOW 1
break _start
break __libc_start_main
break _dl_debug_state
catch syscall execve
catch syscall memfd_create
catch load
info proc mappings
```

Do not use heavyweight instrumentation first if `readelf`, `LD_DEBUG`, or one syscall trace answers the current hypothesis.

## Packing, header abuse, and in-memory loading

### Packed or hostile ELF indicators

- high entropy in executable segments
- entrypoint inside a tiny unpacking stub
- strange or missing section headers while program headers remain runnable
- UPX markers, modified UPX headers, or a UPX-looking binary that standard `upx -d` cannot unpack
- large anonymous executable mappings after startup
- self-modifying writes followed by `mprotect(PROT_EXEC)`

Unpacking workflow:

1. Preserve original hashes and headers.
2. Identify the outer stub's mapping and entrypoint.
3. Trace memory allocation, writes, decompression/decryption, and permission changes.
4. Dump the executable mapping after the OEP or stable payload entry is reached.
5. Rebuild enough ELF metadata for tooling, but keep the dump and original separate.
6. Rerun triage and validate behavior against runtime traces.

### In-memory ELF loading

When `strace` shows `memfd_create` or `/proc/self/fd/N` paths passed to `dlopen`, the binary is doing fileless loading of an inner shared object.

See `in-memory-loading.md` for the full workflow: detection, runtime dump, layer separation, and outer binary analysis.

## Format-specific checklists

### Malware / implant checklist

- `ptrace`, `prctl`, `seccomp`, raw `syscall`, signal handlers
- `dlopen`, `dlsym`, `dlvsym`, plugin or stage loaders
- constructor/IFUNC logic before `main`
- daemonization (`fork`, `setsid`) and environment gating
- config paths under `/etc`, `/var`, `/tmp`, hidden dotfiles
- `/proc` scraping, SSH key access, credential-store paths

### Vulnerability-hunting checklist

- parser entrypoints from `read`, `recv`, `fread`, mmap-backed parsers, and file format handlers
- allocator usage and integer-size calculations
- RELRO / PIE / CANARY / NX / seccomp context before exploit assumptions
- relocation-backed function pointers, vtables, callback arrays, and destructor lists
- DSO version and loader search path if reproducing a crash depends on exact libraries

### Patch-diff checklist

- changed dynamic dependencies, symbol versions, or linker flags
- added bounds checks or parser state validation
- constructor changes that move validation before `main`
- changed IFUNC resolver or CPU-feature dispatch logic
- changed RPATH/RUNPATH or bundled library versions

## Exploitability handoff

Keep this supplement focused on reversing evidence. When a memory-corruption primitive is confirmed, pivot to `../../binary-exploitation-technique/SKILL.md` and, for ELF RELRO/ASLR/pointer-stability decisions, `../../../offensive-ctf/pwn-ctf/references/relro-aslr-relocations.md`.

Minimum handoff evidence:

```text
Object(s): main executable and relevant DSOs
PIE / base addresses / ASLR observations:
RELRO state per object:
Relevant relocations and GOT/PLT entries:
Runtime page permissions:
Leak/control primitive:
Constructor/IFUNC/pre-main side effects:
Reproduction environment and libc/loader version:
```

Conceptual pwn pivots to recognize during RE:

- ret2plt-style calls can leak GOT-resolved addresses when an output primitive exists.
- GOT overwrite assumptions fail under full RELRO or when targeting the wrong object.
- Partial pointer overwrites need ASLR-invariant high bytes, not only a convenient local run.
- `LD_PRELOAD`/symbol interposition can be a lab observation tool, but it is not an exploitability proof.

## Common pitfalls

- **Staring only at sections**: ELF runtime behavior lives in program headers and dynamic entries.
- **Ignoring `init_array` / IFUNC**: meaningful logic can run before `main` and before your usual breakpoints.
- **Misreading stripped Go/Rust/Nim as generic C**: use `languages.md` early.
- **Trusting libc imports too much**: raw syscalls and `dlsym` can hide the real API surface.
- **Forgetting loader context**: `RPATH/RUNPATH`, unusual interpreters, and `LD_*` behavior explain many surprises.
- **Assuming one RELRO result covers all objects**: RELRO is per executable/DSO mapping.
- **Treating GOT values as final too early**: lazy binding means pre-call GOTPLT state can point to resolver machinery.
- **Using `LD_PRELOAD` evidence in secure-exec contexts**: setuid/capability paths can sanitize environment variables.

## Research trail

- [Linux Foundation ELF dynamic linking reference](https://refspecs.linuxfoundation.org/ELF/zSeries/lzsabi0_zSeries/x2251.html) — GOT/PLT, `DT_PLTGOT`, `DT_JMPREL`, lazy binding, and `LD_BIND_NOW` fundamentals.
- [MaskRay, All about Global Offset Table](https://maskray.me/blog/2021-08-29-all-about-global-offset-table) — `.got` vs `.got.plt`, relocation families, RELRO interaction, and GOT entry semantics.
- [MaskRay, All about Procedure Linkage Table](https://maskray.me/blog/2021-09-19-all-about-procedure-linkage-table) — PLT stubs, lazy/eager binding, `_dl_fixup`, `-fno-plt`, and `.plt.sec`.
- [MaskRay, All about symbol versioning](https://maskray.me/blog/2020-11-26-all-about-symbol-versioning) — `.gnu.version*`, `readelf -V`, default versions, and `dlsym`/versioning behavior.
- [MaskRay, GNU indirect function](https://maskray.me/blog/2021-01-18-gnu-indirect-function) — `STT_GNU_IFUNC`, resolver timing, `R_*_IRELATIVE`, and analysis caveats.
- [MaskRay, `.init`, `.ctors`, and `.init_array`](https://maskray.me/blog/2021-11-07-init-ctors-init-array) — constructor/destructor mechanisms and execution order.
- [System Overlord, GOT and PLT for pwning](https://systemoverlord.com/2017/03/19/got-and-plt-for-pwning.html) — practical offensive framing for GOT/PLT and RELRO.
- [CTF101 GOT, ASLR, and RELRO pages](https://ctf101.org/binary-exploitation/what-is-the-got/) — concise CTF-oriented mental models for exploitation handoff.
- [ir0nstone PLT/GOT notes](https://ir0nstone.gitbook.io/notes/binexp/stack/aslr/plt_and_got) — ret2plt/GOT leak framing for ASLR bypass recognition.
- [US-RSE LD_AUDIT walkthrough](https://us-rse.org/blog/2021/vsoch/ldaudit) — loader audit callbacks for library search and symbol-binding evidence.
- [MalwareMustDie R2CON ELF packer talk](https://blog.malwaremustdie.org/p/new-video-of-this-talk-has-just-been.html) — practical custom ELF packer/header-repair lessons.
