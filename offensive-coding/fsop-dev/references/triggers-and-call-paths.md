# Triggers and call paths for FSOP

Load when choosing how to trigger a counterfeit `FILE` stream (e.g., `puts`, `exit`, assert).

## Table of Contents
- [Why trigger selection matters](#why-trigger-selection-matters)
- [Classic cleanup paths](#classic-cleanup-paths)
- [Output-driven paths](#output-driven-paths)
- [Wide-data paths](#wide-data-paths)
- [Codecvt paths](#codecvt-paths)
- [Obstack and adjacent paths](#obstack-and-adjacent-paths)
- [Practical trigger rules](#practical-trigger-rules)

## Why trigger selection matters

Many FSOP exploits fail because the stream corruption succeeded but the chosen libc path never reached the intended function pointer.

Always separate:

1. **corruption phase** — overlap, poison, partial overwrite, fake FILE placement
2. **dispatch phase** — the specific libc helper that consumes the corrupted stream
3. **endgame phase** — leak, write, `system`, `setcontext`, ORW, or a later bridge

## Trigger-availability triage (do this FIRST)

Before forging anything, confirm the trigger you plan to use is actually reachable. Cheap to check, saves long dead-end forges:

- **Scan the imports/PLT.** No `exit`/`atexit`/`__cxa_atexit` and only `_exit`? → `_IO_list_all` is **never flushed** → exit-time and `_IO_list_all`-based FSOP are dead. (`__cxa_finalize` runs dtors, not `_IO_flush_all`.)
- **Which standard streams are touched by *reachable* code?** A forged `stderr` is useless if `stderr` is only used in startup error paths; a forged `stdout`/`stdin` only helps if the menu actually `puts`/`printf`s or `fgets`/`scanf`s each loop. Map "stream → the libc call that consumes it" before forging.
- **Buffering changes the dispatch.** `setbuf`/`setvbuf` to unbuffered makes every `puts`/`printf` hit `_IO_OVERFLOW` immediately (instant trigger, but also instant crash if the stream is half-forged); fully-buffered streams may need >4 KB of output (or a `\n` if line-buffered) to flush.
- **Is the stream's pointer-of-record writable?** Some builds load the `FILE*` for `puts`/`printf` from a libc slot in a **read-only RELRO page** — you cannot redirect the pointer, only corrupt the struct it points to (or use buffer redirection, below).
- **If only `_exit`/no clean trigger exists**, prefer a trigger driven by the program's *own* per-loop I/O: a print (`puts`/`printf`) for output streams, or `fgets`/`fread`/`scanf` for input streams (the latter pairs with buffer redirection).

## Classic cleanup paths

### `exit` / return from `main`

Classic FSOP cleanup paths revolve around process-exit stream cleanup.

Typical implications:

- good when `_IO_list_all` traversal or cleanup-time stream inspection is the trigger
- stable when you can wait until termination
- risky when normal execution mutates the stream too much before exit

### abort / assert / `__malloc_assert`

Failure-driven dispatch is often underrated.

Good fit when:

- the heap route naturally reaches allocator assertions
- `stderr` is easier to overlap than `stdout`
- regular output is too noisy or clobbers your crafted state

This is where Apple-adjacent assert recipes like Cat/Kiwi-style reasoning often make more sense than a clean `puts` path.

Also remember the two common failure-path surfaces:

- `__malloc_assert -> __fxprintf -> __vfxprintf_internal -> _IO_file_xsputn`
- `__malloc_assert -> fflush(stderr)`

That split matters because one target build may favor a write-side path while another favors sync/flush.

## Output-driven paths

### `puts`

Strong when:

- you overlap `stdout`
- you can satisfy byte-oriented checks
- you want a small reproducible dispatch surface

Common modern use:

- redirect `__xsputn`-like flow into `_IO_wfile_overflow` or a related misaligned target

### `fputs`

Strong when:

- the application keeps a custom or heap-backed `FILE *`
- you have a dangling `fopen` / `fdopen` stream rather than a standard-stream overlap
- the code path naturally does `fputs(data, fp)` or `fwrite(..., fp)` after your corruption

Why it matters:

- `fputs` often reaches `_IO_new_file_xsputn`, then `_IO_OVERFLOW`
- after a validated swap or misalignment into `_IO_wfile_jumps`, that can become the same Apple-2-style `_IO_wfile_overflow -> _IO_wdoallocbuf -> _IO_WDOALLOCATE` chain people usually discuss only in `stdout` / `stderr` terms
- this is a strong reminder that FSOP is not just “overwrite `stderr` and call `exit`"

### `printf` / `fprintf` / `fwrite`

Strong when:

- the program already prints through standard or custom streams
- you need repeated triggers
- you are exploiting write-side buffer logic or output helpers

Caveat: these functions can mutate write pointers or buffering state before the final indirect call.

### `fflush`

Often cleaner than raw printing because it can reach sync/finish-style code with less visible application noise.

Bias toward it when:

- you want `_IO_file_sync`, `_IO_wfile_sync`, or similar internal paths
- the target naturally calls `fflush` or flushes on menu boundaries
- you are attacking `stderr` and want to avoid `stdout` interference from normal application output

In practice, this is one of the cleanest modern dispatch surfaces because many tested layouts are easier to keep stable when the trigger is a quiet `fflush(stderr)` rather than repeated menu `puts()` traffic.

## Buffer redirection as arbitrary write (read-side, no vtable change)

When you cannot forge a stream in place (the in-place wall: the corrupting op zeroes the struct and the program uses it immediately) and you cannot redirect the stream's pointer-of-record (read-only RELRO), turn the program's **own input read into your write primitive**:

- Corrupt **only** an input stream's buffer/read fields — `_IO_buf_base`, `_IO_buf_end`, `_IO_read_base/ptr/end` — and **leave `vtable` and `_lock` intact** so the stream still functions and `_IO_acquire_lock` does not fault.
- Set `_IO_read_ptr == _IO_read_end` (force underflow) and `_IO_buf_base = TARGET`, `_IO_buf_end = TARGET + n`. The next `fgets`/`fread`/`scanf` → `_IO_file_underflow` → `read(fileno, TARGET, n)` writes the **next attacker-typed bytes into `TARGET`**.
- Point `TARGET` at another stream (e.g. `&_IO_2_1_stdout_`) and *type* a full forged House-of-Apple-2 FILE into it; then the following print dispatches through it → `system`. (`_flags` clear of `_IO_NO_READS`; the value that forces underflow may need tuning per build — verify in a debugger.)

This sidesteps the in-place wall (the corrupting allocation that gives you `slot.data == &stream` zeroes only the buffer fields if you align its window to exclude `_lock@0x88` and `vtable@0xd8`, e.g. allocate at `&stream - 0x80`), and works even when the output stream's pointer-of-record is read-only. It is the practical form of "angelboy-style FILE-buffer arbitrary read/write" turned into RCE.

## Wide-data paths

### `_IO_wfile_overflow -> _IO_wdoallocbuf -> _IO_WDOALLOCATE`

This is the canonical Apple 2 / angry-FSROP path.

Typical constraint shape:

- `_flags` must not indicate no-writes or incompatible buffering
- `_wide_data->_IO_write_base == 0`
- `_wide_data->_IO_buf_base == 0`
- main `vtable` must misalign into a compatible `_IO_wfile_*` function

Why it matters: it is the clearest modern route from validated main vtable to unvalidated `_wide_vtable` dispatch.

### `_IO_switch_to_wget_mode`

A less famous but real path family.

Why it matters:

- can reach `_IO_WOVERFLOW`
- can be excellent when seekoff/orientation changes are in play
- good example that not all modern FSOP is “just call puts on stdout”

## Codecvt paths

### `__libio_codecvt_in`

Apple 3 family member. Commonly needs awkward register shaping or a tiny gadget bridge because the raw `rdi` geometry may be inconvenient.

### `__libio_codecvt_out`

Another Apple 3 family member. Can fit finish/overflow/sync style routes depending on stream orientation and write-side state.

### `__libio_codecvt_length`

Useful when the available read/write relationships satisfy its stricter constraints better than the in/out helpers.

Guiding rule: if your misaligned validated vtable route lands naturally in codecvt helpers and `_codecvt` is writable, do not force Apple 2.

## Obstack and adjacent paths

Obstack-backed libio helpers are real FSOP surfaces.

Why they matter:

- they can use adjacent stream or pointer state beyond the nominal `FILE` body
- they expand the target set beyond the famous Apple families
- they often work best with `stderr`/`stdout` adjacency or neighboring libc data

Treat them as advanced but practical, especially when symbolic-path work or prior writeups identify a low-constraint route.

Operational nuance:

- some obstack paths effectively consume state in the **next** libc FILE object or an adjacent pointer right after the nominal `_IO_FILE_plus` body
- on stock libc layouts, this often means `stderr` corruption can rely on values placed in neighboring `stdout`
- some of these layouts behave well with `fwrite` / output helpers but not with `fflush`, because the flush path may rewrite fields you were using as payload carriers

## Practical trigger rules

- Use **`stderr`** when normal `stdout` activity corrupts your layout too aggressively.
- Use **`puts`** when you want the smallest recognizable output-driven dispatch.
- Use **`fputs` / `fwrite` on custom `FILE *`** when the bug is a stream UAF and standard streams are irrelevant.
- Use **`fflush`** when sync/finish paths look cleaner than print helpers.
- Use **exit/assert** when your heap route already produces cleanup or allocator-failure control.
- Prefer the trigger that requires the fewest mutable fields to remain stable after corruption.
- **Verify the trigger is reachable before forging** (see "Trigger-availability triage"): no clean `exit`/flush → no `_IO_list_all`; unused `stderr` → no assert/error trigger.
- If your only write primitive **zeroes the chunk and the program immediately does a FILE op on that stream** (the in-place wall), do not forge that stream in place — use cross-stream **buffer redirection** (read-side) or a non-zeroing/print-free/second-thread write.
- If the path depends on orientation, document whether `_mode` must be negative, zero, or positive.

Field-stability rules that save real debugging time:

- avoid using `_lock` as payload storage unless you proved the trigger will not touch locking first
- keep `_mode` negative for byte-oriented streams unless the selected codecvt / wide path explicitly needs it positive
- remember that read/write helpers may rewrite `_IO_read_*` and `_IO_write_*` before your final indirect call, so a path that works under `fflush` may fail under `fprintf`
