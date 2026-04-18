# ELF and Mach-O Analysis Procedure

Detailed workflow for analyzing Linux ELF and macOS Mach-O binaries. Load this reference when the sample is identified as ELF or Mach-O.

## ELF Triage

1. Confirm format: `\x7fELF` magic at offset 0
2. Record: class (32/64), endianness, type (EXEC/DYN/REL), machine (x86_64/ARM/MIPS), entry point
3. Check for static vs dynamic linking: presence of `.dynamic` section and `PT_INTERP` segment
4. Identify compiler: check `.comment` section for GCC/Clang version strings

```bash
readelf -h sample.elf          # Header
readelf -S sample.elf          # Sections
readelf -l sample.elf          # Program headers / segments
readelf -d sample.elf          # Dynamic section (linked libraries)
nm -D sample.elf               # Dynamic symbols
objdump -d -M intel sample.elf # Disassemble (Intel syntax)
```

If `readelf`/`objdump` are unavailable, use `scripts/triage.py` for basic ELF header parsing, or Python `lief`:
```python
import lief
binary = lief.parse("sample.elf")
for section in binary.sections:
    print(f"{section.name}: size={section.size}, entropy={section.entropy}")
```

## ELF section analysis

**Key sections:**
- `.text` — executable code
- `.rodata` — read-only data (strings, constants)
- `.data` / `.bss` — initialized/uninitialized writable data
- `.init` / `.fini` — constructor/destructor code (check for anti-analysis here)
- `.plt` / `.got` — dynamic linking tables
- `.symtab` / `.strtab` — symbol and string tables (stripped binaries lack these)
- `.note.gnu.build-id` — build ID for identification

**Red flags:**
- Missing `.symtab` — binary is stripped (common for malware)
- High-entropy `.data` or `.rodata` — encrypted payloads
- Non-standard section names — possible packing
- `.init`/`.fini` with complex logic — anti-debug or payload initialization

## ELF import/symbol analysis

```bash
nm -D sample.elf | grep -i "connect\|send\|recv\|exec\|system\|fork\|ptrace\|mmap\|mprotect"
objdump -T sample.elf | grep -i "FUNC"
```

**Suspicious imports/symbols:**
- *Network:* `connect`, `send`, `recv`, `socket`, `getaddrinfo`, `gethostbyname`, `curl_*`
- *Execution:* `execve`, `system`, `popen`, `fork`, `clone`, `dlopen`, `dlsym`
- *Memory:* `mmap`, `mprotect`, `munmap` (with PROT_EXEC — self-modifying code)
- *Anti-debug:* `ptrace(PTRACE_TRACEME)`, `prctl(PR_SET_DUMPABLE)`, reading `/proc/self/status`
- *Persistence:* writing to `~/.bashrc`, `/etc/cron.d/`, systemd service files, `/etc/init.d/`

## Go binary analysis

Go binaries are large and have distinctive characteristics:
1. Check for `go.buildid` section or `Go build ID:` string
2. Parse `pclntab` (program counter line table) for function names — survives stripping
3. Use `r2` with `aaa` — radare2 can parse Go function metadata
4. garble-obfuscated Go binaries: function names are random-looking dotted identifiers (e.g., `a1b2c3.d4e5f6`)
5. Runtime strings to look for: `runtime.goexit`, `runtime.mstart`, `runtime.newproc`

## Mach-O Triage

1. Confirm format: `\xCF\xFA\xED\xFE` (64-bit LE), `\xCE\xFA\xED\xFE` (32-bit LE), `\xCA\xFE\xBA\xBE` (fat/universal)
2. Record: CPU type, subtype, file type, number of load commands
3. For universal binaries, extract the target architecture with `lipo`

```bash
otool -h sample.macho           # Header
otool -l sample.macho           # Load commands
otool -L sample.macho           # Linked libraries
otool -tV sample.macho          # Disassemble __TEXT,__text
```

## Mach-O specific concerns

- **Code signing:** check `LC_CODE_SIGNATURE` load command; unsigned or ad-hoc signed binaries are suspicious
- **Entitlements:** check for dangerous entitlements (`com.apple.security.cs.disable-library-validation`)
- **Launch agents/daemons:** look for strings referencing `~/Library/LaunchAgents/`, `/Library/LaunchDaemons/`
- **dylib injection:** check for `DYLD_INSERT_LIBRARIES` environment variable references
- **Persistence via login items:** `LSSharedFileList`, `SMJobBless`, `osascript`

## ELF/Mach-O packing

Less common than PE packing but exists:
- UPX works on ELF — try `upx -d sample.elf`
- Custom packers: look for `mmap`+`mprotect` with `PROT_EXEC` in `.init` or entry point
- Encrypted segments: high entropy in unexpected sections

## Reverse engineering approach

1. Start at entry point (`_start` or `main`)
2. For dynamically linked: focus on PLT/GOT entries for network and exec functions
3. For statically linked: use `capa` to identify capabilities without symbol info
4. Use `r2` or Ghidra headless for decompilation — see the respective tool skills for command details
5. For Go: focus on `main.main`, then trace through goroutine spawns

## Dynamic analysis (Linux lab)

```bash
# Trace syscalls
strace -f -o trace.log ./sample.elf

# Trace library calls
ltrace -f -o ltrace.log ./sample.elf

# GDB — break on network/exec
gdb -q ./sample.elf
> break connect
> break execve
> break ptrace
> run
> bt          # backtrace when breakpoint hits
> info registers
```

GDB workflow details are in `references/dynamic-analysis.md`.
