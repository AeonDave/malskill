# Clang SafeStack + CFI + software shadow stack + canary (the "CFI++" mitigation stack)

Load when a binary combines several of: `-fsanitize=safe-stack`, Clang cross-DSO CFI (forward-edge
icall checks), a **hand-rolled software shadow stack** (BSS array of return addresses checked in every
instrumented epilogue), and normal stack canaries — and the only bug is a linear overflow of an
address-taken buffer. Every one of these can be defeated *leak-free* by turning one primitive into
another; the whole point is that no single mitigation is the wall — the composition is, and it comes
apart when you attack the runtime data that all of them share (the TLS block, the saved-register
window, the jump-table base register).

Treat the offsets below as *shapes to look for*, not constants.

## 0. Recognise the layout — and DON'T trust WSL

The bug is usually an unbounded `gets()`/`read()` into a buffer on the **unsafe stack** (the mmap'd
region pointed to by `__safestack_unsafe_stack_ptr` in TLS; `%rsp` still points at the *safe* stack).
Overflowing it does NOT reach the return address (that's on the safe stack) — that's SafeStack's whole
pitch. What it CAN reach depends entirely on what is mapped *above* the unsafe stack:

- **RLIMIT_STACK is the knob.** With the default (e.g. 8 MB) stack, Linux uses top-down mmap and libc
  (`r--p`) usually abuts the unsafe-stack top → the overflow faults a few bytes in. **With
  `ulimit -s unlimited` (standard for `socat` CTF deploys) Linux switches to the LEGACY bottom-up mmap
  layout, which places the TLS/TCB block DIRECTLY ABOVE the unsafe stack.** Now the same overflow
  reaches, measured from the buffer:
  `__safestack_unsafe_stack_ptr` (`fs-0x20`), the locale-TLS ptr (`fs-0xb0`), the master canary
  (`fs+0x28`), the TCB self-pointer (`fs+0x00`), the pointer guard (`fs+0x30`).
- **WSL lies.** WSL's kernel gives the top-down (default-stack) layout, so a WSL `/proc/pid/maps` shows
  libc abutting the unsafe stack and the overflow "faulting at +0x70". That is a **WSL artifact**, not
  the remote. Reproduce the remote faithfully: `patchelf` a copy onto the target glibc and run it under
  `ulimit -s unlimited` (glibc *version* is irrelevant; RLIMIT_STACK is the only knob). Or just
  length-sweep the live remote (§ "verify boundaries live" in the main skill). Never conclude "bounded/
  impossible" from a WSL map.

## 1. Canary bypass — leak-free (two ways)

The stack-protector canary sits on the *unsafe* stack (it guards the buffer), so the overflow crosses
it — but you rarely need to know it:

- **Self-reference.** The check is `cmp r15, [r14]` where `r14` is the address it compares against and
  `r15` is the loaded canary. If you can make the checking function's restored `r14` point at its own
  restored `r15` slot, then `[r14] == r15` trivially for *any* value — no canary knowledge. You get
  this control from a SafeStack relocation (§3): you own the callee's saved-register window on the
  (relocated) stack, and those saved regs become the caller's `r14`/`r15` after the epilogue `pop`s.
- **Overwrite, don't leak.** If the overflow reaches `fs:0x28`, SET it to a known `K`. From then on
  every frame's canary check passes by writing `K` at the checked slot (match), and any prologue that
  copies `fs:0x28` (e.g. a callee's `[usp-8]=canary`) propagates `K` wherever you steer that write —
  which is how you feed `K` into a register you need (§2).

## 2. Clang forward-edge CFI bypass — rewrite the jump-table base register

The icall check is `sub target, base; ror ...,3; cmp count-1; ja fail; call target`, where **`base` is
a register** (e.g. `lea r15,[rip+x]`). For a 2-entry table this locks `target ∈ {base, base+8}` — but
only *while `base` is immutable*. If you can rewrite the caller's `base` register (via the relocation
register-control of §3, or by having a callee's canary-copy write land on the caller's saved-`r15`
slot), set `base == target` so `target-base = 0` passes for an **arbitrary** target. The bijective lock
is an illusion the moment `base` is attacker-controlled. This is usually the cleanest way to get
`call <arbitrary>` from a corruptible-but-CFI-checked function pointer.

## 3. SafeStack unsafe-pointer relocation — the master primitive

`__safestack_unsafe_stack_ptr` (TLS, `fs-0x20`) is the base for the *next* instrumented function's
unsafe frame. Overwrite it (reachable per §0) to point anywhere writable — typically **onto the safe
stack** or into `.bss`. Then that function's compiler-emitted unsafe writes become an
**arbitrary write**:
- its prologue `[usp-8] = canary`, and
- any `read(0, usp-0x30, N)` / buffer store into its unsafe frame.

Crucially you also control that function's *saved callee registers* on the relocated stack, which the
epilogue `pop`s into the CALLER's registers — that's the lever for §1 (caller `r14`/`r15`) and §2
(caller `r15` = CFI base). One relocation = one contiguous write region, so a *single* relocation can
paint EITHER a safe-stack slot OR a far `.bss` slot, never both — remember this when fighting the
shadow stack (§4).

## 4. Software shadow stack — defeat by loop, or by bare-gadget pivot

A hand-rolled shadow stack (BSS array `shstk[]` + index `shstk_ptr`; every instrumented fn: push
retaddr on entry, `cmp shstk[p-1], retaddr; jne abort` on exit) is *correct* and *balanced* — auditing
it for an off-by-one usually finds nothing. Two real defeats:

- **Bare-gadget pivot (skip every instrumented epilogue).** The shadow check only guards
  *compiler-instrumented* returns. A ROP chain of *bare* gadgets (`pop rdi;ret`, `add rsp,8;ret`,
  `pop rsp;...;ret`, and `syscall@plt` — a PLT stub, NOT an instrumented epilogue, so it returns
  cleanly) never touches the shadow stack. Once you have `call <arbitrary>` (§2), dispatch it to a
  pivot (`add rsp,8;ret` lands `rsp` on attacker qwords → `pop rsp` → a `.bss` chain) and run ORW with
  no shadow check ever consulted.
- **Hijack a real return** requires TWO coordinated far-apart writes (the safe-stack return slot AND
  its `shstk[]` copy, or `shstk_ptr` aliased to a self-referential slot). One relocation gives one
  write — so you need a **sustained loop** (§5) to get unlimited writes.

## 5. The sustained relocation LOOP → unlimited arbitrary write

Turn the single `call K` into a repeatable primitive by dispatching **K = the program's `main` entry**
(re-run the menu). Two traps that masquerade as "TCB/shadow walls":

- **16-byte stack alignment.** Re-entering at an inner site (e.g. `call vuln`) that descends 8
  bytes/cycle misaligns `%rsp` → glibc `printf`'s `movaps` `#GP`s (looks exactly like TCB corruption).
  Re-enter at `main` entry so the per-cycle descent is a multiple of 0x10 (call-push 8 + N prologue
  pushes) → always 16-aligned → `printf` never faults. Re-running `main` also re-derives `r14`/`r13`
  from `fs:[usp]` and resets the CFI base `r15`, repairing state each cycle.
- **Zeroed locale TLS.** The overflow zeroed the locale pointer (`fs-0xb0`) → `strtol` SIGSEGVs.
  **Forge it with one ASLR-invariant qword**: point it at a PIE data address whose `[+0x68]`
  (`__locale_struct.__ctype_b`) targets a libc function such that `isspace(digit)==0`. No leak, no
  placement — just a constant offset.

With the loop alive: once `fs:0x28=K` is set (§1), every later cycle's canary passes by match, so the
relocated read's qwords are FREE — a **repeatable arbitrary write** to any address. Stage a full
syscall-ORW chain + `"flag.txt"` into an already-mapped BSS page (the `shstk` page, NOT a separate
segment that may be unmapped on the remote), then trigger the pivot.

## 6. Leak-free syscall-ORW endgame (no libc)

`syscall@plt` = libc `syscall(nr,a1,a2,a3)` (args in `rdi,rsi,rdx,rcx`) and RETURNS cleanly. Building a
chain with only PIE gadgets:
- **No `pop rdx`?** The `syscall` instruction preserves `rdx`, so `rdx` carries over as the previous
  `syscall`'s C-`rcx` — prime it with `pop rcx` one call earlier; no rdx gadget needed.
- **fd is deterministic** — but `socat` may hold fd 3, so `read(3,...)` hangs. `close(0)` first → `open`
  returns fd 0 → `read(0,...)` is fd-agnostic.
- Chain: `close(0); open("flag.txt",0); read(0,buf,0x100); write(1,buf,0x100)`.

## Checklist / discriminating tests
- Length-sweep the LIVE remote for the real fault boundary before ruling the overflow bounded.
- Confirm `__safestack_unsafe_stack_ptr` is reachable (relocation survives → the next fn's banner still
  prints; a wild ptr faults its prologue write).
- If a loop dies at cycle 2 with a `printf` `movaps` crash → alignment; re-enter at `main`.
- If it dies in `strtol`/`__ctype` → forge the locale ptr.
- Never accept a sub-agent/sim "primitive works/doesn't" verdict without an INPUT-ONLY repro (a local
  PTY in cooked mode mangles `0x7f` bytes in pointer payloads → false "loop never cycles"; a `gdb set`
  is not a delivered primitive).
