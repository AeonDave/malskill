# Platform Workflows

## 1) Windows x64 workflow (PIC + syscall-oriented)

1. Define contract
   - entry register assumptions
   - max size + bad-byte set
   - API path: Win32 vs Nt* direct/indirect
2. Build minimal PIC core
   - resolve modules/APIs without static IAT dependency where needed
   - preserve non-volatiles and shadow-space compliance
3. Add memory lifecycle
   - allocate -> copy/decode -> set execute permissions -> transfer control
   - verify cleanup path for failed transitions
4. Validate
   - disassemble bytes and inspect prologue/epilogue
   - debug with WinDbg/x64dbg for stack/register correctness
   - verify call stack/source address expectations if using indirect syscall gate

### Windows pitfalls checklist

- Missing shadow space before indirect calls
- Broken `rcx/r10` handoff in syscall stubs
- Hardcoded SSN values across OS builds
- Assuming one ntdll gadget is always clean
- PE export/relocation parser mistakes in reflective path

---

## 2) Linux x64 workflow (syscall + mmap/mprotect)

1. Build bootstrap payload with explicit syscall ABI assumptions
2. Request memory with `mmap` and check failures explicitly
3. Stage/decode payload (if staged), then `mprotect` to RX/RWX as needed
4. Transfer control and keep deterministic return/error behavior
5. Validate with debugger + syscall trace and replay with fixed payload bytes

### Linux pitfalls checklist

- Incorrect `rax/r10` argument placement for syscalls
- Using wrong alignment/page math for `mprotect`
- Assuming vDSO fixed address
- Ignoring short reads in staged receive loops

---

## 3) Linux aarch64 workflow

1. Confirm arm64 ABI and stack alignment constraints
2. Use `x8` syscall numbers and `x0-x5` args consistently
3. Keep decoder/stager branch-safe (no accidental clobber of link register semantics)
4. Emulate first, then runtime-debug on arm64 target

### aarch64 pitfalls checklist

- Stack misalignment at function boundaries
- Carrying x64 register habits into arm64 codegen
- Decoder loops that break due to width/sign mistakes

---

## 4) macOS x64/arm64 workflow

1. Treat syscall behavior as XNU-specific, not Linux-compatible
2. Validate syscall identifiers against current XNU syscall tables
3. For in-memory loaders, handle Mach-O/dyld assumptions explicitly
4. Debug on the exact major/minor target environment when possible

### macOS pitfalls checklist

- Reusing Linux syscall assumptions
- Mach-O loader shortcuts that fail on newer versions
- arm64 alignment/calling errors masked in synthetic tests

---

## 5) Cross-platform release gate

A payload variant is release-ready only if:

- ABI invariants pass on target architecture
- memory transition paths (`alloc -> write/decode -> exec`) are deterministic
- staged path tolerates partial transport behavior
- static + emulation + runtime tests all pass with same byte blob
