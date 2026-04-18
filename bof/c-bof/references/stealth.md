# BOF stealth and OPSEC guidance

## Scope

This page focuses on reducing *behavioral* and *memory* detection signals while keeping BOFs portable across loaders.

## 1) Syscall strategy

### Beacon syscall wrappers (preferred)

Prefer Beacon syscall wrappers (`BeaconVirtualAllocEx`, `BeaconOpenProcess`, etc.) where available.

Why:
- follows framework-configured syscall strategy
- can leverage indirect syscalls without embedding `syscall` instructions in BOF code
- reduces direct userland-hook interaction in common paths

### InlineWhispers3 (fallback)

When Beacon syscall wrappers are unavailable (non-CS loaders, older CS versions),
use [InlineWhispers3](https://github.com/klezVirus/InlineWhispers3) to generate
indirect syscall stubs compatible with BOF constraints.

Workflow:
1. Run InlineWhispers3 against the target Windows build to generate `syscalls.asm`
2. Assemble with `nasm -f win64 syscalls.asm -o syscalls.o`
3. Link `syscalls.o` alongside your BOF object
4. Call generated stubs (e.g., `NtAllocateVirtualMemory`) instead of `ntdll.dll` exports

BOF-specific considerations:
- Generated stubs use `jmp [ntdll_base + offset]` pattern → indirect call through ntdll
- No embedded `syscall` instruction in BOF code → avoids direct syscall detection
- Stubs are position-independent and COFF-compatible
- SSN resolution happens at generation time → no runtime `syscall; ret` hunting needed
- Combine with DFR for ntdll base: `HMODULE hNtdll = KERNEL32$GetModuleHandleA("ntdll.dll");`

Limitations:
- SSNs are OS-version dependent → regenerate for target build
- Adds ~2-4 KB per syscall stub to `.text`
- Some EDRs hook the indirect call target in ntdll → test against target environment

## 2) Memory hygiene

- Avoid long-lived RWX mappings.
- Use RW → RX transitions.
- Release transient buffers quickly.
- Keep decrypted payload lifetime short.

## 3) Image-backed execution options

When feasible, prefer techniques that execute from image-backed regions (e.g., module stomping) over private RX pages.

## 4) Thread-start OPSEC

High-signal indicators include thread start addresses in private/unbacked regions.
Mitigations:
- image-backed staging
- call path indirection
- conservative use of thread creation APIs

## 5) Sleep-mask and BeaconGate awareness

For environments using Sleep Mask / BeaconGate:
- validate call-origin behavior after enabling gates
- test memory layout before/after masking cycles
- ensure BOF helper memory is not left as obvious unbacked RX artifacts

## 6) Output discipline

- avoid verbose noisy logging in production mode
- provide operator-selectable verbosity (`mode` flag)
- emit compact error codes + context, not large dumps by default

## 7) Build-time hardening

Minimum flags baseline:
- `-fno-asynchronous-unwind-tables`
- `-ffunction-sections -fdata-sections`
- `-falign-functions=1`
- `-fno-merge-constants`
- `-s`

## 8) Validation checklist

- no obvious high-signal IOCs from memory permissions
- no unnecessary imports
- no hardcoded operator or workstation artifacts
- deterministic cleanup on every error path
