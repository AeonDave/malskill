# Hints and recognition for FSOP

Load to quickly map a binary's behavior or crash constraints to viable FSOP paths.

## Table of Contents
- [Fast recognition cues](#fast-recognition-cues)
- [Field-level hint map](#field-level-hint-map)
- [Target selection hints](#target-selection-hints)
- [Trigger-selection hints](#trigger-selection-hints)
- [Endgame hints](#endgame-hints)
- [Anti-hints](#anti-hints)

## Fast recognition cues

### You probably have an FSOP candidate when

- a heap exploit can place data over `stdout`, `stderr`, or `stdin`
- a UAF or overlap reaches a heap `FILE *` returned by `fopen` / `fdopen`, especially if `fputs` or `fwrite` uses it later
- you can write one or two libc pointers into a stream but a full ROP overwrite is awkward
- glibc is post-2.34 and old hook endings are gone
- the program naturally prints, flushes, exits, aborts, or asserts after corruption
- a fake `FILE` is easier to allocate than a fake stack or full object graph

### You probably do **not** need FSOP when

- you already own a simpler application callback/function pointer with the same or lower write cost
- the target never touches streams again after corruption
- the stream fields you need are constantly rewritten before your trigger
- your only idea is “overwrite vtable to heap pointer” on validated modern glibc

## Field-level hint map

- **`_flags`**: often doubles as a constraint gate and, in `system(fp)`-style endings, part of the argument string.
- **`_IO_read_*` / `_IO_write_*`**: usually tell you whether the path is leak/read/write-oriented or whether a flush/overflow check can be satisfied.
- **`_IO_buf_*`**: strong clue for redirection, disclosure, and some obstack/overflow routes.
- **`_lock`**: if invalid, many otherwise-correct layouts crash before the interesting dispatch.
- **`_mode`**: one of the fastest ways to distinguish byte-oriented from wide-oriented or codecvt-sensitive paths.
- **`_wide_data`**: the biggest single hint that Apple 2 / wide dispatch might be the shortest modern route.
- **`_codecvt`**: hint that Apple 3 / codecvt helpers may be easier than forcing `_wide_vtable`.
- **`__cookie` / `__io_functions` on a cookie-file layout**: House of Emma territory; expect pointer-guard and callback-mangling problems, not a trivial `system(fp)`.
- **main `vtable`**: think validated misalignment, not arbitrary replacement.

## Target selection hints

- **`stdout`**: easiest to trigger, hardest to keep pristine.
- **`stderr`**: often the best practical default on modern targets because it is used less, yet still reachable on errors and asserts.
- **`stdin`**: strongest when you want arbitrary read/write or structure self-overwrite, not immediate RIP control.
- **custom `FILE *`**: great when the program keeps a heap-allocated or attacker-influenced stream object alive across operations.

## Trigger-selection hints

- If the menu calls `puts` after almost every action, `stdout`-driven FSOP may be easier than exit-time cleanup.
- If allocator corruption naturally reaches `malloc_printerr` / `__malloc_assert`, think `stderr` and failure-path FSOP.
- If the program flushes regularly, `fflush` and sync paths may be cleaner than output helpers.
- If only termination is guaranteed, document the exact exit-time path and which checks you must survive before dispatch.

## Endgame hints

- **Need shell quickly on permissive target** → Apple 2 with `system`-style ending.
- **Need SUID-safe chain** → `setcontext`, ORW, or credential-fixing ROP.
- **Need more primitives, not immediate RIP** → leak-oriented FSOP first.
- **Need pointer-guard / TLS material** → redirect output and recover the secret before touching guarded callbacks.
- **Need the fewest writes** → choose the path whose suggested layout clusters values in already-controlled regions.

## Anti-hints

- Do not call every post-hook FILE exploit “House of Apple”.
- Do not assume `_wide_vtable` automatically means easy RCE; confirm the reachable wide function and the constraints guarding it.
- Do not burn time on Apple 3 if `_codecvt` is not realistically writable.
- Do not ignore obstack and sync/finish paths just because public writeups talk mostly about `puts` and `exit`.
- Do not choose `system("/bin/sh")` when the target needs ORW, `setuid(0)`, or a less noisy post-exploitation path.
