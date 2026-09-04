# Loader-Core Qualification (Raw PIC Cores)

Condensed from a live qualification pass of three Windows x64 in-memory
loader cores (SEC_IMAGE overlay, module stomping, ghostly hollowing:
bootstrap-decode → manual PE map → carrier overlay → scrubbed-start
handoff). Every defect below passed static review and only reproduced by
EXECUTING the core. Use this when qualifying, porting, or reviewing any
raw PIC loader extracted from a compiled image (`.text`/`.rdata` objcopy)
or any wrapper that stages one.

Ground rule: a raw core inherits every alignment assumption the compiler
baked into it (function alignment, SSE section alignment, RIP-relative
data). The build/wrapper pipeline must preserve ALL of them or the core
faults with signatures agents routinely misread.

## Defect taxonomy (signature -> cause -> gate)

### 1. Wild jump at first dispatched call (mid-instruction RIP, register soup)
- **Cause:** naked thunk templates with a runtime-patched dispatch slot
  (`.quad` after the jmp) packed byte-tight under `-falign-functions=1`.
  When a thunk starts ≠ 0 (mod 8), `.p2align 3` puts the slot at +0x0E while
  the patch helper writes the hardcoded +0x10 — 6 bytes into the real slot
  poison it; the next `jmp [slot]` lands mid-instruction.
- **Gate:** pin `aligned(16)` on every patched thunk template (slot lands at
  a fixed offset), validate the template byte-for-byte in the patch helper
  (opcode bytes, jmp disp, pristine zeroed slot), and a build gate that
  scans the extracted core for every template and asserts slot offset +
  zero bytes. Assembler-computed jmp displacements self-correct for
  placement; hardcoded patch offsets never do.

### 2. SSE fault at first rip-relative `movdqa/movaps` (AV at garbage/-1)
- **Cause:** compilers emit 16-aligned SSE loads/stores for section data
  assuming PE section alignment. A byte-tight link
  (`--section-alignment=1 --file-alignment=1`) makes the raw
  `.text`+`.rdata` concatenation place `.rdata` at an offset ≡ 8 (mod 16).
- **Gate:** link with section alignment 16 (an entry symbol at `.text`
  byte 0 survives), plus a build gate asserting every rip-relative SSE
  source in the extracted core is 16-aligned.

### 3. Same SSE fault, wrapper variant
- **Cause:** the core executes IN PLACE from the staged blob. The wrapper's
  seed-random junk gap between bootstrap and core puts the core at an
  arbitrary (odd) blob offset — breaking the SAME alignment contract even
  when the core itself is clean.
- **Gate:** the wrapper must place the core at a 16-aligned blob offset
  (constrain the junk length), with a layout test asserting
  `core_offset % 16 == 0`.

### 4. Decode/ABI register conflation in the bootstrap
- **Cause:** one register (e.g. RCX) reused for two lifetimes — the
  rolling-XOR decode cursor AND the loader's first ABI argument (payload
  pointer). The cursor walks past the bootstrap; the ABI arg needs its
  original value. Also: hand-written templates drift — the patch offsets
  in comments can be off by one from the actual encoding (an immediate
  patched onto an opcode byte silently corrupts the key).
- **Gate:** re-load the ABI register from an anchor after the decode loop
  (`lea rcx,[rax+dll]` with `rax = &byte5` from `call $+5; pop rax`), and
  enforce template parity by ASSEMBLING the reference source at test time
  and byte-comparing. Never trust a hand-maintained comment offset.

### 5. Kernel-version-dependent "optimization" treated as a requirement
- **Cause:** a dual-view RW alias of a SEC_IMAGE carrier section
  (`PAGE_READWRITE` second view) returns STATUS_IMAGE_NOT_AT_BASE on
  Win11 24H2 — a relocated image view CoWs its pages and stops sharing
  physical pages with the RX view, so writes through the alias never show
  in the executing view. Code that requires the alias (`rst ==
  STATUS_SUCCESS`) fails on every carrier on modern kernels.
- **Gate:** treat such paths as optimizations with a mandatory fallback
  (scoped `NtProtectVirtualMemory` transitions on the executing view),
  unmap the rejected view (leak-free), and let the runtime harness decide
  which path executed. Informational NTSTATUS values (≥ 0x40000000) are
  success-shaped but not always success-equivalent: branch on the exact
  contract, never on `>= 0`.

## Debugging signatures (Windows, live core in a heap page)

- **Post-syscall register soup** (`RCX = gadget+2` = return RIP, `R11 =
  RFLAGS`, sane stack) — the `syscall;ret` gadget returned normally; the
  fault is AFTER the syscall, not in it. Stop blaming the syscall chain.
- **Mid-instruction RIP with impossible registers** — execution jumped
  wild into the middle of code; hunt the mispatched/indirect jump
  primitive (patched slot, poisoned pointer table), not the fault site.
- **AV at `0xFFFFFFFFFFFFFFFF` on Win11** — frequently a misaligned SSE
  access (`movdqa/movaps` on a non-16-aligned address), reported oddly.
- **Fastest forensics ladder:** (1) VEH probe that dumps fault
  RIP/registers + the blob region at fault time (diff the region against
  the expected decoded image — proves decode correctness); (2) GDB
  (`gdb -x cmdfile --args probe.exe`) catches the exact faulting
  instruction where a VEH can mislead; (3) isolate thread-vs-wrapper by
  calling the decoded core directly with the documented ABI from a shim
  (`rcx/rdx/r8/r9d` set, `jmp`) on a fresh thread.

## Qualification gate recipe (per backend)

1. Static: zero `IMAGE_REL_AMD64_ADDR64` relocs in the object (raw
   extraction cannot rebase); placement gates from the taxonomy above;
   core byte 0 = entry trampoline.
2. Layout: wrapper round-trip decode in Go/C recovers core + payload
   byte-for-byte; every patched field self-consistent.
3. Runtime harness (real execution): benign freestanding payload DLL
   (NO CRT DllMain — manual-mapped CRT init is a separate hazard; the
   loader must skip DllMain or the payload must be `-nostdlib`), executed
   at ≥5 explicit randomized addresses, ≥3 runs each; payload validates
   the handoff args and terminates the thread with a magic exit code.
4. Failure cleanup: corrupted payload must exit the thread nonzero with
   the host process alive (strict no-fallback, quiet death).
5. Real-agent end-to-end: the actual payload, full protocol dance
   observed by a listener, thread exit 0.

Win11 24H2 `ntdll` `Zw*` stub layout (gadget/SSN scans still match):
`4C 8B D1` `B8 SSN32` `F6 04 25 08 03 FE 7F 01 75 03` `0F 05 C3`
`CD 2E C3` — the `test [KUSER_SHARED_DATA],1; jne int2E` filter sits
between the SSN and the `syscall;ret` at +0x12. See
`offensive-coding/asm-offensive-patterns/references/syscall-internals.md`.
