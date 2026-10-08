# ELF internals for programmatic work

Load when parsing ELF headers/relocations or diagnosing the path from process entry to initializers and `main`.

An ELF object can be relocatable, executable, shared object, or core dump. Runtime execution behavior is primarily controlled by the ELF header and **program header table**.

- `e_ident` defines class, endianness, ABI, and magic
- `e_phoff`, `e_phnum` locate load-relevant segments
- `e_shoff`, `e_shnum` describe sections for tooling and link-time metadata

Practical rule: loaders use program headers to map memory. Many runtime-relevant binaries can run with stripped section headers.

## Program headers: runtime truth

Important `p_type` values:

- `PT_LOAD`: maps file bytes into memory with `p_flags` permissions
- `PT_INTERP`: names dynamic linker path for dynamically linked executables
- `PT_DYNAMIC`: points to dynamic linking table
- `PT_PHDR`: optional self-description of program headers
- `PT_NOTE`: notes used for metadata such as build IDs and core information

Invariants:

- `PT_LOAD` entries are expected in ascending virtual address order
- `p_filesz <= p_memsz`; memory tail is zero initialized
- `p_vaddr` and `p_offset` must be congruent under alignment constraints

## Sections: analysis and relocation metadata

Sections provide symbol, relocation, and metadata organization.

Common section types:

- `SHT_SYMTAB`, `SHT_DYNSYM` for symbol tables
- `SHT_RELA` and `SHT_REL` for relocations
- `SHT_DYNAMIC` for dynamic entries mirrored by `PT_DYNAMIC`
- `SHT_STRTAB` for strings
- `SHT_NOTE` for notes
- `SHT_NOBITS` for zero-init regions like `.bss`

Common section flags:

- `SHF_ALLOC` memory-present at runtime
- `SHF_EXECINSTR` executable content
- `SHF_WRITE` writable content

## Dynamic linking mechanics

`PT_DYNAMIC` exposes `DT_*` tags used by the runtime linker.

Frequent tags:

- `DT_NEEDED` direct shared library dependencies
- `DT_STRTAB`, `DT_SYMTAB` dynamic symbol infrastructure
- `DT_RELA`, `DT_RELASZ`, `DT_REL`, `DT_RELSZ` relocation tables
- `DT_PLTGOT`, `DT_JMPREL` PLT and GOT relocation surfaces
- `DT_INIT`, `DT_FINI` lifecycle hooks
- `DT_RPATH` and `DT_RUNPATH` library search directives

Search-order reality on modern Linux loaders:

1. `DT_RPATH` only if `DT_RUNPATH` absent
2. `LD_LIBRARY_PATH` unless secure-exec mode
3. `DT_RUNPATH` for direct dependencies
4. `/etc/ld.so.cache`
5. default library directories

`DT_RUNPATH` differs from legacy `DT_RPATH` by not applying recursively to transitive children.

## Relocations and symbol binding

Relocations patch references once final load addresses are known.

- `REL`: addend stored at relocation target
- `RELA`: explicit addend in relocation entry

Runtime-sensitive areas:

- GOT and PLT entries for external function and data references
- non-writable segment relocations can trigger stronger scrutiny and may require text relocation allowances

## Notes and build identity

`SHT_NOTE` and `PT_NOTE` can hold values used by debuggers, core analyzers, and distribution tooling.

Notable note payloads:

- build ID identifiers
- ABI tagging
- core dump thread and mapping metadata

## Trace program startup against the target runtime

For a normal dynamically linked glibc executable with `PT_INTERP`, distinguish these boundaries:

```text
execve -> kernel maps executable and interpreter, prepares initial stack/auxv
-> interpreter entry -> loader relocation and early initialization
-> executable e_entry (usually _start) -> __libc_start_main
-> executable initializers -> main -> normal exit processing
```

The kernel initially transfers control to the interpreter, not directly to the executable's `_start`. `AT_ENTRY` identifies the relocated executable entry; `AT_BASE` identifies the interpreter base. Neither is a file offset. Check the mapped object containing the current PC, not just a symbol named `_start`. See the kernel's [ELF execution implementation](https://github.com/torvalds/linux/blob/v6.18/fs/binfmt_elf.c); match its version and vendor patches when investigating kernel-specific behavior.

Startup is runtime-specific. Without `PT_INTERP`, there is no external interpreter handoff; static glibc startup performs its own runtime initialization, and static PIE also needs self-relocation. musl, custom entrypoints, and language runtimes require their own source/trace. `ET_DYN` alone does not distinguish a shared library from a PIE executable.

### Replace old diagrams with measured boundaries

- The [DBP tutorial](http://dbp-consulting.com/tutorials/debugging/linuxProgramStartup.html) demonstrates a useful minimal-program/disassembly/debugger/source method, using 32-bit x86 and older glibc/GCC startup. Its addresses, stack arguments, PC thunks, `.ctors` helpers, and `__libc_csu_init` chain are not a current cross-platform ABI.
- Current glibc startup objects, changed in 2.34, pass null `init`/`fini` arguments. In the dynamic path, libc locates the executable's `DT_INIT`/`DT_INIT_ARRAY` directly. An older binary can still pass its legacy initializer to a newer libc: inspect the binary, not only the installed libc version. [glibc startup change](https://sourceware.org/pipermail/libc-alpha/2021-February/122794.html), [glibc 2.39 implementation](https://github.com/bminor/glibc/blob/glibc-2.39/csu/libc-start.c).
- On ordinary x86-64 glibc startup, `_start` passes `main`, `argc`, and `argv` in registers; do not transpose the tutorial's i386 pushes onto x86-64. Check the target architecture's [startup assembly](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/x86_64/start.S).
- In dynamic glibc startup, the loader handles executable `DT_PREINIT_ARRAY` and dependency initialization before transferring to executable startup; libc then handles executable initializers. Relocation-time IFUNC resolvers can run earlier. Do not prescribe a total ordering of independent DSOs from one sample. [Loader initializer source](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-init.c).
- Returning from `main` enters normal `exit` processing. `_exit`, `_Exit`, a fatal signal, or an initialization failure can bypass normal cleanup; one trace's handler/destructor order is not a universal termination rule. [glibc main invocation](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/nptl/libc_start_call_main.h).

### Recover the evidence

Record the target compiler/linker, libc package revision, architecture, loader, and binary build ID/hash. For matching source/debug-file selection and the evidence record, use `reversing-technique` → `references/re-workflow.md`, section **Verify OS/runtime behavior**.

Static inspection does not execute the target:

```bash
uname -srmo
gcc --version
ld --version
getconf GNU_LIBC_VERSION
readelf -W -h -l -d -n ./probe
readelf -W -s -V ./probe
objdump -d --disassemble=_start ./probe
gcc -### -g -O0 -fPIE -pie probe.c -o probe
gcc -print-file-name=Scrt1.o
```

The driver commands show link inputs without building/executing the program; use their startup-object paths to correlate disassembly with libc/toolchain sources. `Scrt1.o` is a glibc PIE convention, not a universal filename. Match distro source packages and patches to the loaded libc/loader; an upstream tag alone does not prove the installed implementation matches.

Use a locally built, harmless probe with a constructor marker, a `main` marker, and an `atexit` callback; build with `gcc -g -O0 -fPIE -pie probe.c -o probe`. Compare its normal run with this GDB session:

```text
set pagination off
set disable-randomization off
set backtrace past-main on
set backtrace past-entry on
set breakpoint pending on
starti
info symbol $pc
info auxv
info files
```

At the first stop, read `AT_ENTRY` from `info auxv`; set `tbreak *ADDRESS`, replacing `ADDRESS` with that runtime value, then `continue`. Confirm the stop is in the executable before disassembling its startup and breaking on `__libc_start_main`, the probe constructor, and `main`. Record `bt`, argument/register values, and actual mapping addresses at the relevant stops. Breakpoints named `_start` can resolve in both interpreter and executable; an address breakpoint avoids that ambiguity.

`start` stops around `main` and can miss constructors; `starti` exposes the earlier boundary. Leave ASLR enabled when verifying relocation/address assumptions. `LD_DEBUG=libs,reloc` can supplement a trusted probe's trace, but loader diagnostics, `strace`, and output markers do not individually prove every internal call. [GDB startup commands](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Starting.html).

## Practical offensive and defensive implications

- Hooking and evasion workflows that depend on symbol resolution should reason about dynamic tags and loader path controls, not just static imports
- Loader anomalies often come from search-path state, secure-exec stripping, or missing expected `DT_NEEDED` chains
- Forwarded or versioned symbol behavior can change function resolution outcomes between systems with different linker and libc stacks

## Version-sensitive cautions

- Dynamic linker behavior varies with glibc version and distro patches
- hwcaps path preference can alter selected shared object even when soname is unchanged
- hardened environments may suppress preload and path variables in secure execution contexts

## Fast troubleshooting checklist

- Validate ELF class and endianness early
- Confirm `PT_INTERP` path exists and matches target arch
- Inspect `DT_NEEDED` plus runpath and rpath interplay
- Compare effective loader environment with secure-exec assumptions
- Verify relocation table presence and expected type mix
