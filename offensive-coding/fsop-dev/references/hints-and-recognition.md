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
- you can corrupt an **input** stream's buffer pointers (`_IO_buf_base`/`_IO_read_*`) — the program's own `fgets`/`fread`/`scanf` then becomes an **arbitrary write of attacker-typed bytes** (use it to forge a FILE into *another* stream). See `triggers-and-call-paths.md` → "Buffer redirection as arbitrary write".

### The in-place wall: allocator zeroes + immediately uses the target stream

A very common reason an otherwise-correct in-place FSOP "just crashes": the **only write primitive zeroes the buffer it returns (calloc / explicit `memset`/`rep stosq`) and the program performs a FILE op on that same stream before you can re-forge it** (e.g. `create` zeroes a chunk over `stdout` then immediately `printf`s the success line; or corrupting `stdin` breaks the *next* `fgets` you need to drive the forging write). The half-zeroed stream (NULL vtable / NULL `_lock`) faults before your forge completes.

Recognise it, then escape via one of:

- **Cross-stream redirect (no in-place forge):** corrupt an *input* stream's buffer only — keep its `vtable` and `_lock` intact — so the program's own read lands your forged FILE bytes into a *different* target stream; trigger on the next print. This sidesteps the wall entirely and is single-shot.
- **Pick a stream the corrupting op never touches:** forge a stream whose only consumer is a *later* trigger you control, so no FILE op runs on the half-built state in between.
- **A write primitive that does not zero / does not print** (a true arbitrary write, a `free()`-deposited pointer, or a second thread performing the write outside the corrupting op).

When choosing the chunk offset for the corrupting allocation, **align the zeroed/edited window to exclude the fields that must stay live for the intervening op** (`_lock`, `vtable`, and the read/`_lock` fields any in-between I/O needs).

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
- **`stdin`**: strongest when you want arbitrary read/write or structure self-overwrite, not immediate RIP control. Its biggest modern use: **redirect `_IO_buf_base` to a target address** (keeping `vtable`+`_lock`) so the next `fgets`/`fread` `read(0, target, n)` writes attacker-typed bytes there — type a forged FILE straight into `stdout`/`stderr`, then trigger on the next print. Lets you weaponise even when the stdout/stderr pointer-of-record is in a read-only RELRO page.
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
- Do not keep retrying an **in-place** vtable/struct forge when the same write op zeroes the stream and the program uses it immediately after (the in-place wall) — switch to cross-stream buffer redirect or a non-zeroing/print-free write instead.
- Do not assume an exit/`_IO_list_all` or `stderr`/assert trigger exists — **verify it in the imports/PLT first** (see trigger-availability triage). Burning time forging a FILE for a trigger the binary never reaches is a classic dead path.
