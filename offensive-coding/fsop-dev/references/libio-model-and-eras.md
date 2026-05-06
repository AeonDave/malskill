# libio model and exploitation eras

## Table of Contents
- [Core structures](#core-structures)
- [What actually matters in practice](#what-actually-matters-in-practice)
- [Validation and trust boundaries](#validation-and-trust-boundaries)
- [Era map](#era-map)
- [Working model](#working-model)

## Core structures

### `_IO_FILE_plus`

glibc/libio uses a `FILE` object implemented as `_IO_FILE_plus`:

- `_IO_FILE` body holding flags, buffer pointers, orientation, locks, chains, and optional side structures
- trailing `vtable` pointer to an `_IO_jump_t` jump table

This is the main dispatch object for standard streams and many libc I/O helpers.

### `_IO_FILE`

The fields that matter most for exploit routing are usually:

- `_flags`
- `_IO_read_*`
- `_IO_write_*`
- `_IO_buf_*`
- `_chain`
- `_lock`
- `_codecvt`
- `_wide_data`
- `_mode`
- trailing `vtable`

Do not memorize offsets blindly across versions. Reconfirm them on the target libc.

### `_IO_wide_data`

`_IO_wide_data` is the wide-character side structure attached through `FILE->_wide_data`.

Why it matters:

- it contains its own `_wide_vtable`
- many modern FSOP chains rely on the fact that wide dispatch historically lacked the same validation applied to the main `FILE` vtable
- Apple 2 and several angry-FSROP paths are really `_wide_vtable` exploitation, not generic `FILE` exploitation

### `_IO_codecvt`

`_codecvt` participates in character conversion flows. In practice it matters because:

- some vtable-misaligned routes reach codecvt helper functions
- House of Apple 3 lives here
- codecvt paths can provide indirect call sites with different register/control geometry than `_wide_vtable` routes

### `_IO_cookie_file`

`fopencookie` extends the normal stream layout into `_IO_cookie_file`:

- embedded `_IO_FILE_plus`
- `__cookie` at the extension tail, commonly treated as the first argument for the eventual callback
- `__io_functions` block containing encrypted `read` / `write` / `seek` / `close` callback pointers

Why it matters:

- House of Emma and related cookie-file paths live here
- the interesting control points sit **past** the normal `_IO_FILE_plus` tail
- this is one of the clearest examples that modern FSOP is broader than `stdout` / `stderr` plus `_wide_vtable`

## What actually matters in practice

A corrupted stream can give you four broad outcomes:

1. **disclosure** — redirect read/write pointers to leak memory
2. **arbitrary read/write** — turn stream buffers into a memory primitive
3. **indirect call / PC control** — usually via validated jump-table reuse, `_wide_vtable`, codecvt, or related helper paths
4. **bridge to another primitive** — e.g. leak pointer guard, then forge a later exit/destructor/cookie-file path

Not every FSOP target should aim directly at `system`.

## Validation and trust boundaries

### Main `vtable`

Since glibc 2.24, the main `FILE` vtable is range-checked to ensure it points inside the libc vtable section.

Exploit implication:

- raw heap vtables die on modern builds
- valid libc jump-table addresses still work
- **misaligned** valid addresses are often more important than the nominal table the stream originally used

### `_wide_vtable`

Modern FSOP emphasis exists because `_wide_vtable` has historically been reachable without the same validation. That made `_IO_wdoallocbuf`/`_IO_WDOALLOCATE` and related wide paths powerful post-check/post-hook routes.

Treat this as a version-sensitive trust boundary. Confirm on the real target libc.

### Pointer-guard-adjacent surfaces

Some file-related helpers or adjacent endgames involve encrypted function pointers or mangled callbacks.

Exploit implication:

- FILE corruption may only be stage one
- the real win can be a TLS leak, pointer-guard recovery, or guard overwrite enabling a later callback/destructor hijack

### Cookie-file callbacks and pointer guard

Cookie-file routes matter because their callback slots are typically protected by `PTR_MANGLE` / `PTR_DEMANGLE`.

Practical implications:

- a fake `_IO_cookie_file` may need either the real pointer guard, a guard overwrite, or a target path that reuses a pointer already correctly mangled for that process
- on x86-64 glibc, the guard is typically discussed as TLS data near `fs:[0x30]`
- House of Emma-style exploitation often treats FILE corruption as a bridge into **guarded callback execution**, not as a direct `system(fp)` trick

## Era map

| Era | Rough versions | What changed | What to bias |
|---|---|---|---|
| classic | <= 2.23 | no main vtable validation | fake vtables, `_IO_list_all`, raw `_IO_OVERFLOW` thinking |
| validation era | 2.24-2.33 | main vtable must live in libc vtable section | misalignment, alternate jump tables, leak-oriented FILE abuse |
| post-hook | 2.34+ | malloc hooks removed from mainstream paths | Apple 2/3, stream overlap, `setcontext`, ORW |
| modern path-hunting | 2.35+ | practical FSOP centers on `_wide_vtable`, codecvt, and path-specific constraints | angry-FSROP, stderr/stdout overlap, hint-mode path selection |

## Working model

Think in layers:

1. **Object layer** — which stream or fake FILE do you control?
2. **Trust-boundary layer** — main vtable, `_wide_vtable`, `_codecvt`, or buffer fields?
3. **Dispatch layer** — which libc helper gets called naturally?
4. **Constraint layer** — what must `_flags`, `_mode`, locks, and pointers satisfy?
5. **Endgame layer** — leak, read/write, `system`, `setcontext`, ORW, or later bridge?

This layering prevents most FSOP cargo cult. If you cannot name the dispatch layer and the constraints that guard it, you do not yet have an FSOP plan.
