# ELF internals for programmatic work

## Core model

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
