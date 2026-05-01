# ELF Reverse Engineering Supplement

Load this after `triage.md` and `re-workflow.md` when the sample is an ELF. It focuses on ELF-only pivots: program headers, PLT/GOT behavior, constructors, dynamic linking, and Linux-specific runtime clues.

## ELF-only fast checks

```bash
readelf -h sample.elf
readelf -l sample.elf
readelf -d sample.elf
readelf -S sample.elf
```

Answer these first:

1. **PIE or fixed-base?** Changes how you reason about addresses.
2. **glibc, musl, or static?** Determines libc signatures and loader behavior.
3. **Dynamic or syscall-heavy?** Malware often mixes libc wrappers with raw syscalls.
4. **Constructor abuse?** `init_array`/constructors may run real logic before `main`.

## Linux loader-aware workflow

### 1. Read program headers, not just sections

- `PT_INTERP` reveals the runtime loader
- `PT_DYNAMIC` exposes `NEEDED`, `RPATH/RUNPATH`, and relocation mode
- `PT_GNU_STACK` and `GNU_RELRO` hint at exploit surface and hardening

```bash
readelf -l sample.elf | grep -E "INTERP|DYNAMIC|GNU_STACK|GNU_RELRO"
```

### 2. Inspect dynamic linking behavior

Prioritize these symbols and tables:

- **PLT/GOT**: imported call sites and lazy binding pivots
- **`dlopen` / `dlsym`**: runtime plugin loading or late API resolution
- **`__libc_start_main`**: useful anchor when symbols are stripped
- **`init_array` / `fini_array`**: constructor/destructor logic

If imports look clean but behavior is suspicious, look for direct syscalls or `dlsym`-resolved function pointers.

### 3. Treat constructors as pre-main code paths

```bash
readelf -W -a sample.elf | grep -iE "init_array|fini_array"
```

Common constructor duties:

- anti-debug or anti-VM checks
- config decryption
- environment probing
- fork/daemon setup

### 4. Separate stripped-binary problems from language-runtime problems

- **Stripped C/C++**: recover anchors from imports, strings, and calling patterns
- **Go / Rust**: pivot to `languages.md`
- **Embedded ELF inside firmware**: pivot to `firmware-rev.md`

Do not spend time rebuilding generic language metadata by hand if runtime fingerprints already give it away.

### 5. Check Linux-specific execution surfaces

- file/network/process syscalls
- persistence via service/unit files, cron, shell init files
- credential access via `/proc`, `/etc`, SSH keys, browser stores
- privilege boundaries: setuid, capabilities, namespace usage

```bash
strings -a sample.elf | grep -iE "/proc/|/etc/|systemd|cron|ssh|iptables|bashrc"
```

## Format-specific checklists

### Malware / implant checklist

- `ptrace`, `prctl`, `seccomp`, raw `syscall`
- `dlopen`, `dlsym`, plugin or stage loaders
- daemonization (`fork`, `setsid`) and environment gating
- config paths under `/etc`, `/var`, `/tmp`, hidden dotfiles

### Vulnerability-hunting checklist

- parser entrypoints from `read`, `recv`, `fread`, file format handlers
- allocator usage and integer-size calculations
- RELRO / PIE / CANARY context before exploit assumptions

### Patch-diff checklist

- changed dynamic dependencies
- added bounds checks or parser state validation
- constructor changes that move validation before `main`

## Common pitfalls

- **Staring only at sections**: ELF runtime behavior lives in program headers and dynamic entries.
- **Ignoring `init_array`**: Linux samples often hide meaningful logic before `main`.
- **Misreading stripped Go/Rust as generic C**: use `languages.md` early.
- **Trusting libc imports too much**: raw syscalls and `dlsym` can hide the real API surface.
- **Forgetting loader context**: `RPATH/RUNPATH` and unusual interpreters can explain weird behavior fast.

---

## GNU_IFUNC / STT_GNU_IFUNC (Indirect Functions)

`IFUNC` entries in `.dynsym` are resolver functions: the dynamic linker calls them at load time to select the actual implementation (e.g., the best AVX2/SSE2/generic path for `memcpy`). If Ghidra shows an unresolved indirect call through `.got.plt`, it may be an IFUNC target that was never concretized.

### Detection

```bash
readelf -s binary | grep -E "IFUNC|STT_GNU_IFUNC"
# Output example:
# 23: 0000000000401890  94 IFUNC  GLOBAL DEFAULT 13 memcpy
```

### Resolving in GDB

```bash
gdb ./binary
(gdb) break _start
(gdb) run
# After dynamic linker finishes (ld.so resolved IFUNCs before main):
(gdb) info symbol 0x<got_plt_entry_address>
# Output: memcpy@plt + N in section .plt of binary (resolved)
(gdb) x/i 0x<resolved_address>   # Disassemble the selected impl
```

### Analysis in Ghidra

1. Locate the IFUNC entry in the `.got.plt` table — Ghidra may label it as an `ExternalFunction` with no body
2. Set a breakpoint in GDB at the IFUNC resolver function address (from `readelf -s`)
3. Step through the resolver to identify which implementation it selects for the current CPU
4. In Ghidra: mark the selected implementation address as the real callee; re-annotate call sites

### Relevance for RE

- Custom IFUNCs are a steganography opportunity: the resolver function can contain logic (not just CPU feature checks)
- Security patches sometimes change which IFUNC variant is default — patch diff analysis must account for resolver logic changes

---

## In-Memory ELF Loading (memfd_create / dlopen)

When `strace` shows `memfd_create` or `/proc/self/fd/N` paths passed to `dlopen`, the binary is doing fileless loading of an inner shared object.

See `references/in-memory-loading.md` for the full workflow: detection, runtime dump, layer separation, and outer binary analysis.
