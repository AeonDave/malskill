# COFF Loader Hardening

Load when writing or auditing a **custom COFF loader** (engine-side), not when authoring a BOF. Patterns reported from a Go engine (`bof_engine coff/`); no revision-bound qualification record is linked here.

## Symbol resolution

- **GOT dedup**: cache resolved addresses per symbol (`gotMap`). A BOF importing the same `KERNEL32$` symbol 10 times must not consume 10 callback slots — engines with finite trampoline pools exhaust silently.
- **Reverse symbol matching**: encrypt the incoming symbol name at compare time and match against pre-encrypted constants; no plaintext `BeaconPrintf`-class names anywhere in the loader.
- **Thunk pages for runtime functions**: BOFs legitimately reference `memset`/`memcpy` without DFR. Resolve against a fixed runtime-DLL list (msvcrt/ntdll/kernel32/kernelbase/ucrtbase) and bind through a `mov rax, imm64; jmp rax` thunk on a dedicated page, then `PAGE_EXECUTE_READ` it.
- **API-set fallback**: resolve `api-ms-win-*` forwards through the PEB ApiSetMap hash table before falling back to kernelbase; try `W` suffix then `A`.

## Section and relocation handling

- Detect `.bss` by `IMAGE_SCN_CNT_UNINITIALIZED_DATA` (0x80), **never** by section name — obfuscated BOFs randomize names.
- Allocate sections `PAGE_READWRITE`, apply relocations, **then** flip executable sections to `PAGE_EXECUTE_READ`. Never RWX.
- Supported relocation types for x64: `ADDR64`, `ADDR32NB`, `REL32`/`REL32_1..5`. Anything else: reject the object, don't guess.
- **Argless entry**: pad `argData` to a minimal valid buffer (`[len=4][0]`) when the operator passes nothing — reading a length prefix from an 8-byte stack slot is the classic argless-BOF crash.

## Compile-time instead of loader-side emulation

Push what you can into flags, so the loader never needs to emulate runtime features:

```bash
x86_64-w64-mingw32-gcc -c bof.c -o bof.o -Os \
  -mno-stack-arg-probe \                # removes __chkstk dependency entirely
  -fno-asynchronous-unwind-tables       # no SEH unwind data to honor
```

Without `-mno-stack-arg-probe`, a BOF with a large stack frame emits `__chkstk` imports that naive loaders must special-case (or crash on).

## Crash isolation (VEH)

A crashing BOF must not kill the host agent:

1. Register the VEH **first** (`AddVectoredExceptionHandler(1, ...)`) — priority over the host runtime's own handler (matters for Go hosts).
2. In the handler: capture context with `RtlCaptureContext`, run the entry on a guard flag, restore with `RtlRestoreContext` (not `longjmp` — it corrupts the frame chain).
3. Return the exception code as the BOF's exit status; remove the handler after the call.
4. Guard-page status (`STATUS_GUARD_PAGE_VIOLATION`) belongs to the paging layer — intercept in the same handler chain and hand off to the demand pager.

## Demand paging for large BOF .text

For `.text` > ~8 KiB, minimize the inspectable executable footprint (reported pattern, `bof_engine memory_protection_windows.go`):

1. Snapshot the section, encrypt offline, keep a sliding window of ~4 RX pages.
2. Back the rest with `PAGE_GUARD`.
3. On `STATUS_GUARD_PAGE_VIOLATION`: decrypt that page into the window, evict the oldest (zero it, re-guard), `EXCEPTION_CONTINUE_EXECUTION`.
4. The VEH from the crash-isolation layer handles the faults — same handler chain, paging is just another guarded state.

## Idle-time sleep masking

When the engine idles between BOFs, XOR-encrypt executed sections with a CSPRNG key and restore on next dispatch (tracker keyed by section base). Loop must be driven by the output channel's idle window, not by a hook on `Sleep` — hooking the host's sleep surface breaks hosted-thread contracts (see `edr-evasion-dev` BOF-safe sleep policy).

## COFF obfuscation (at-rest)

An obfuscator that emits **still-valid COFF** buys at-rest anti-signature without loader changes: zero timestamps/characteristics, rename sections and non-critical symbols conservatively (preserve `go`, `__imp_*`, `__C_specific_handler` contracts), junk string-table entries, padding. Optional second stage: XOR with machine-type-derived key plus a self-describing obfuscation version header, loader auto-detects and deobfuscates (reported pattern: `bof_engine script/coff_obfuscator.go`).

## Anti-patterns

- Loader allocates one page per import slot without dedup → callback-pool exhaustion on large BOFs.
- Trusting section names for BSS/init detection → breaks on obfuscated objects.
- Emulating `__chkstk` in the loader instead of compiling it out.
- Leaving the VEH registered across unrelated engine work → the handler starts catching host faults.
- Demand-paging BOFs that run in a hosted thread you don't control → guard faults in a thread whose VEH chain you don't own are unfixable from outside.
